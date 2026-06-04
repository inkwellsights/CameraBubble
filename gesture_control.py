"""
Gesture Control — turn phone-camera hand gestures into PC actions.

Captures the scrcpy "PhoneCam" window via Windows Graphics Capture, runs Google
MediaPipe's prebuilt Gesture Recognizer (7 gestures, no training), and fires a
mapped keyboard/hotkey action on a debounced gesture transition.

Run:  python gesture_control.py          (live - actually presses keys)
      python gesture_control.py --dry     (logs what it WOULD do, no keypresses)

Needs the scrcpy PhoneCam window running (PhoneBubble.bat or GestureControl.bat
starts it). Requires: mediapipe pyautogui opencv-python numpy windows-capture
and gesture_recognizer.task next to this file.
"""

import sys, time, threading, os, atexit, ctypes
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mptasks
from mediapipe.tasks.python import vision
import pyautogui
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

# ---------------- config ----------------
WINDOW_NAME   = "PhoneCam"
MODEL_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_recognizer.task")
MIN_SCORE     = 0.45     # min confidence to accept a gesture (lower = catches marginal palms faster)
STABLE_FRAMES = 3        # gesture must persist this many frames before it fires
INFER_FPS     = 15       # cap gesture recognition to this many frames/sec (big CPU saver; 30 not needed)
INFER_WIDTH   = 640      # downscale frames to this width before recognition (CPU saver)
PAUSE_GESTURE = "Thumb_Down"  # toggles ALL scanning on/off (freeze, so you can move your hands freely).
                              # Same gesture freezes AND resumes - the engine keeps watching for THIS
                              # one even while frozen. Options: Thumb_Down, ILoveYou, Pointing_Up.
COOLDOWN      = 1.2      # seconds before the same tap action can fire again
MAX_HOLD      = 120      # safety: hard cap - auto-release any latched key after N seconds
NOHAND_RELEASE = 45      # safety: release latched keys after N seconds with NO gesture seen
                         #         (so a missed fist / walking away can't leave space stuck;
                         #          45s = comfortable hands-free dictation window, then auto-stops)
HOLD_WINDOW   = 30       # hold-mode: a palm opens a recording window this many seconds long.
                         #            Re-show palm to extend; fist/thumbs pause it. No fist
                         #            dependency, so it can't get stuck if the fist isn't read.
NEWLINE_KEYS  = ["shift", "enter"]  # fist while PAUSED inserts a newline (multi-line prompt).
NEWLINE_COUNT = 2                   # how many newlines per idle-fist. If shift+enter SENDS instead
                                    # of making a newline in your terminal, try ["ctrl","enter"].

# Gesture -> action. Built-in gesture names:
#   Open_Palm, Closed_Fist, Thumb_Up, Thumb_Down, Victory, Pointing_Up, ILoveYou
# modes:
#   tap        -> press a single key once          {"mode":"tap","key":"enter"}
#   hotkey     -> press a combo once               {"mode":"hotkey","keys":["win","shift","s"]}
#   latch_on   -> hold a key DOWN until latch_off   {"mode":"latch_on","key":"space"}
#   latch_off  -> release a latched key             {"mode":"latch_off","key":"space"}
# ============================ DICTATION MODE ============================
# "tap"  = HANDS-FREE (recommended). Run `/voice tap` ONCE in Claude Code first.
#          Palm = start recording (keeps going on its own), Fist = stop + auto-submit.
#          One synthetic keypress, no warmup, no key-repeat needed = reliable.
# "hold" = Default /voice. You must HOLD your palm up the WHOLE time you talk
#          (engine streams the key ~20x/sec to emulate a physically held key).
#          This is the version you already proved works.
DICTATION_MODE = "hold"
VOICE_KEY = "space"     # Claude Code /voice push-to-talk key
# NOTE: this MUST match Claude Code's /voice mode.
#   engine "hold" <-> run `/voice hold` in Claude Code  (hold palm up while talking)
#   engine "tap"  <-> run `/voice tap`  in Claude Code  (palm = start, fist = stop)
# =======================================================================

if DICTATION_MODE == "hold":
    # LATCHED hands-free: palm once = start (space streams on its own), fist/thumbs = stop.
    STREAM_GESTURE  = "Open_Palm"      # show once to START recording
    STREAM_KEY      = VOICE_KEY
    STREAM_INTERVAL = 0.05             # ~20 taps/sec, emulates OS auto-repeat
    BINDINGS = {                       # palm/fist/thumbs handled specially below; extras here:
        "Victory": {"mode": "hotkey", "keys": ["win", "shift", "s"], "desc": "Snipping tool"},
    }
else:  # "tap"
    STREAM_GESTURE  = None
    STREAM_KEY      = VOICE_KEY
    STREAM_INTERVAL = 0.05
    BINDINGS = {
        "Open_Palm":   {"mode": "tap", "key": VOICE_KEY, "desc": "/voice START (tap mode)"},
        "Closed_Fist": {"mode": "tap", "key": VOICE_KEY, "desc": "/voice STOP + submit"},
        "Thumb_Up":    {"mode": "tap", "key": "enter",   "desc": "Submit / Enter"},
        # add your own:
        # "Victory":     {"mode": "hotkey", "keys": ["win","shift","s"], "desc": "Screenshot snip"},
        # "Pointing_Up": {"mode": "hotkey", "keys": ["ctrl","c"],        "desc": "Copy"},
    }
# ----------------------------------------

DRY = "--dry" in sys.argv
DEBUG = "--debug" in sys.argv
try:
    sys.stdout.reconfigure(line_buffering=True)   # show prints immediately when redirected
except Exception:
    pass
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

held = {}          # key -> time it was pressed (latched)
last_fire = {}     # gesture -> last tap fire time


def log(msg):
    print(time.strftime("%H:%M:%S "), msg, flush=True)


def dispatch(gesture):
    spec = BINDINGS.get(gesture)
    if not spec:
        return
    mode = spec["mode"]
    now = time.time()
    tag = "[DRY] " if DRY else ""

    if mode in ("tap", "hotkey"):
        if now - last_fire.get(gesture, 0) < COOLDOWN:
            return
        last_fire[gesture] = now
        if mode == "tap":
            if not DRY: pyautogui.press(spec["key"])
            log(f"{tag}{gesture}: {spec['desc']}  (press {spec['key']})")
        else:
            if not DRY: pyautogui.hotkey(*spec["keys"])
            log(f"{tag}{gesture}: {spec['desc']}  ({'+'.join(spec['keys'])})")

    elif mode == "latch_on":
        key = spec["key"]
        if key not in held:
            if not DRY: pyautogui.keyDown(key)
            held[key] = now
            log(f"{tag}{gesture}: {spec['desc']}  (holding {key})")

    elif mode == "latch_off":
        key = spec["key"]
        if key in held:
            if not DRY: pyautogui.keyUp(key)
            del held[key]
            log(f"{tag}{gesture}: {spec['desc']}  (released {key})")


def release_all():
    for key in list(held):
        if not DRY: pyautogui.keyUp(key)
        log(f"safety: released held key '{key}'")
        del held[key]


atexit.register(release_all)   # never leave a latched key stuck down

# Also release on console-close / logoff (atexit alone misses a hard window close).
def _console_ctrl_handler(ctrl_type):
    release_all()
    return False  # allow default handling to continue
try:
    _HANDLER = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)(_console_ctrl_handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_HANDLER, True)
except Exception:
    pass


class FrameGrabber:
    def __init__(self, window_name):
        self.window_name = window_name
        self.latest = None
        self.lock = threading.Lock()
        self.control = None
        self.count = 0          # frames received from WGC
        self.closed = False
        self.error = None

    def start(self):
        cap = WindowsCapture(cursor_capture=False, draw_border=False, window_name=self.window_name)

        @cap.event
        def on_frame_arrived(frame: Frame, ctl: InternalCaptureControl):
            with self.lock:
                self.latest = np.ascontiguousarray(frame.frame_buffer[:, :, :3])
                self.count += 1

        @cap.event
        def on_closed():
            self.closed = True

        try:
            self.control = cap.start_free_threaded()
        except AttributeError:
            threading.Thread(target=cap.start, daemon=True).start()

    def get(self):
        with self.lock:
            return None if self.latest is None else self.latest.copy()


def main():
    if not os.path.exists(MODEL_PATH):
        print("Missing gesture_recognizer.task next to this script."); return

    opts = vision.GestureRecognizerOptions(
        base_options=mptasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,                          # catch either hand (we scan all slots below)
        min_hand_detection_confidence=0.5,    # default - lower invited phantom hands
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    recognizer = vision.GestureRecognizer.create_from_options(opts)

    grab = FrameGrabber(WINDOW_NAME)
    grab.start()

    print("=" * 56)
    print(f"  GESTURE CONTROL{'  [DRY-RUN: no keys pressed]' if DRY else ''}")
    print(f"  Dictation mode: {DICTATION_MODE.upper()}")
    print("  Show these to the phone camera:")
    if DICTATION_MODE == "hold":
        print(f"    Open_Palm    -> talk for {int(HOLD_WINDOW)}s (re-show palm to extend)")
        print("    Closed_Fist  -> stop recording; (when stopped) newline")
        print("    Thumb_Up     -> stop recording; (when stopped) SEND")
        print("    Victory      -> Snipping tool")
    else:
        for g, s in BINDINGS.items():
            print(f"    {g:<12} -> {s['desc']}")
    print(f"    {PAUSE_GESTURE:<12} -> FREEZE / UNFREEZE all scanning")
    print("  Ctrl+C to quit.")
    print("=" * 56)

    # wait for first frame
    for _ in range(40):
        if grab.get() is not None: break
        time.sleep(0.25)
    if grab.get() is None:
        print("No PhoneCam frames. Is scrcpy 'PhoneCam' running? (run GestureControl.bat)")
        return

    prev, stable, fired = "None", 0, False
    ts = 0
    loops = 0
    last_hb = time.time()
    last_count = 0
    last_active = time.time()   # last time ANY gesture was seen (for no-hand release)
    streaming = False           # hold-mode: dictation window currently open
    last_stream = 0.0
    last_palm = 0.0             # time the palm was last seen (opens the HOLD_WINDOW)
    last_dbg = 0.0
    last_infer = 0.0
    infer_period = 1.0 / INFER_FPS
    paused = False              # when True, all gesture actions are frozen (toggle with PAUSE_GESTURE)
    try:
        while True:
            now = time.time()

            # --- SPACE stream runs EVERY loop (decoupled from inference) so it stays ~20/sec
            #     even though we only recognize gestures at INFER_FPS to save CPU ---
            if DICTATION_MODE == "hold":
                window_open = (not paused) and (now - last_palm) < HOLD_WINDOW
                if window_open:
                    if now - last_stream >= STREAM_INTERVAL:
                        if not DRY: pyautogui.press(STREAM_KEY)
                        last_stream = now
                    if not streaming:
                        streaming = True
                        log(f"dictation ON - {int(HOLD_WINDOW)}s window; re-show palm to extend")
                elif streaming:
                    streaming = False
                    log("dictation OFF (window closed - words transcribed; thumbs-up to send)")

            # --- gesture recognition: throttled to INFER_FPS + downscaled (the CPU saver) ---
            if now - last_infer >= infer_period:
                last_infer = now
                frame = grab.get()
                if frame is None:
                    if now - last_hb >= 3:
                        log(f"[hb] waiting for frames... frames_in={grab.count} closed={grab.closed}")
                        last_hb = now
                else:
                    h, w = frame.shape[:2]
                    if INFER_WIDTH and w > INFER_WIDTH:                  # downscale -> cheaper inference
                        frame = cv2.resize(frame, (INFER_WIDTH, int(h * INFER_WIDTH / w)), interpolation=cv2.INTER_AREA)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    ts += int(infer_period * 1000) + 1
                    try:
                        res = recognizer.recognize_for_video(mp_img, ts)
                    except Exception as e:
                        log(f"recognize error: {e}")
                        res = None

                    if res is not None:
                        loops += 1
                        # Scan ALL detected hands; take the best NAMED gesture (multi-hand slot fix).
                        g = "None"; score = 0.0
                        for hand_gestures in (res.gestures or []):
                            if not hand_gestures:
                                continue
                            cat = hand_gestures[0]
                            if cat.category_name not in ("None", "") and cat.score >= MIN_SCORE and cat.score > score:
                                g, score = cat.category_name, cat.score

                        if DEBUG and now - last_dbg > 0.3:
                            raws = [f"{hg[0].category_name}:{hg[0].score:.2f}" for hg in (res.gestures or []) if hg]
                            log(f"[dbg] hands={len(res.gestures or [])} raw=[{', '.join(raws)}] accepted={g}")
                            last_dbg = now

                        if g == prev:
                            stable += 1
                        else:
                            prev, stable, fired = g, 1, False
                        if g != "None":
                            last_active = now
                        if DICTATION_MODE == "hold" and not paused and g == "Open_Palm":
                            last_palm = now                             # (re)open the window

                        # --- gesture transitions (fire once per gesture streak) ---
                        if stable >= STABLE_FRAMES and not fired and g != "None":
                            fired = True
                            if g == PAUSE_GESTURE:                      # freeze/unfreeze everything
                                paused = not paused
                                if paused:
                                    last_palm = 0.0                     # close any open dictation window
                                    log(f"*** SCANNING PAUSED *** (show {PAUSE_GESTURE} again to resume)")
                                else:
                                    log("*** SCANNING RESUMED ***")
                            elif paused:
                                pass                                    # ignore every other gesture while paused
                            elif DICTATION_MODE == "hold":
                                if g == "Closed_Fist":
                                    if streaming:
                                        last_palm = 0.0                 # pause recording (does NOT send)
                                        log("PAUSE (fist) - not sent; palm to keep talking")
                                    else:
                                        for _ in range(NEWLINE_COUNT):  # paused fist = newline(s)
                                            if not DRY: pyautogui.hotkey(*NEWLINE_KEYS)
                                        log(f"newline x{NEWLINE_COUNT} (fist while paused)")
                                elif g == "Thumb_Up":
                                    if streaming:
                                        last_palm = 0.0                 # pause first; never sends mid-recording
                                        log("PAUSE (thumbs) - thumbs-up again to SEND")
                                    else:
                                        if not DRY: pyautogui.press("enter")
                                        log("SEND (Enter)")
                                elif g != "Open_Palm":
                                    dispatch(g)   # Victory -> snipping tool, etc.
                            else:
                                log(f"detected: {g} ({score:.2f})" + (f" -> {BINDINGS[g]['desc']}" if g in BINDINGS else "  (unbound)"))
                                dispatch(g)

            # safety auto-release of latched keys
            if held and now - last_active > NOHAND_RELEASE:
                log(f"safety: no gesture for {NOHAND_RELEASE}s -> releasing latched keys")
                release_all()
            for key, t in list(held.items()):
                if now - t > MAX_HOLD:
                    if not DRY: pyautogui.keyUp(key)
                    del held[key]
                    log(f"safety: auto-released '{key}' after {MAX_HOLD}s")

            # heartbeat every 3s
            if now - last_hb >= 3:
                fps = (grab.count - last_count) / (now - last_hb)
                state = " [FROZEN]" if paused else ""
                log(f"[hb] alive  frames_in={grab.count} ({fps:.0f}/s)  infer={loops}  current={prev}{state}")
                last_hb, last_count = now, grab.count

            time.sleep(0.008)
    except KeyboardInterrupt:
        pass
    finally:
        release_all()
        print("\nGesture control stopped.")


if __name__ == "__main__":
    main()
