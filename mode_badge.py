"""
mode_badge.py - tiny always-on-top badge showing the gesture engine's current MODE.

Launched automatically by gesture_control.py (when SHOW_BADGE is True). It reads
_mode_status.txt (written atomically by the engine), shows a colored pill -
FROZEN / SCROLL / TALK / READY - and, when ATTACH is on, follows the phone-cam window
so the two move together. By default it sits just ABOVE the cam (so the cam can't cover
it) and re-asserts topmost every tick. Drag it to reposition; the spot (relative to the
cam) is remembered. It closes itself when the engine stops.

Robust by design: a bad/partial read is ignored (keeps the last state); it only closes
when the engine's timestamp goes genuinely stale. Any error is logged to _badge_error.log.

No extra dependencies - tkinter ships with Python.
"""
import tkinter as tk
import os, time, traceback
import ctypes
from ctypes import wintypes

_HERE     = os.path.dirname(os.path.abspath(__file__))
MODE_FILE = os.path.join(_HERE, "_mode_status.txt")
POS_FILE  = os.path.join(_HERE, "_badge_pos.txt")
ERR_FILE  = os.path.join(_HERE, "_badge_error.log")

ATTACH     = True                          # follow the phone-cam window so the badge moves with it
CAM_TITLES = ["PhoneCam", "PhoneBubble"]   # scrcpy rectangle, or the circular bubble

# mode -> (background, foreground, label)
STYLE = {
    "FROZEN": ("#6b7280", "#ffffff", "FROZEN"),   # gray
    "SCROLL": ("#f97316", "#ffffff", "SCROLL"),   # orange
    "TALK":   ("#22c55e", "#08160c", "TALK"),     # green
    "READY":  ("#2563eb", "#ffffff", "READY"),    # blue
}
DEFAULT = STYLE["READY"]


def log_err(msg):
    try:
        with open(ERR_FILE, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


# --- Win32 plumbing to find, follow, and stay above the cam window (64-bit safe) ---
_u = ctypes.windll.user32
_u.FindWindowW.restype = wintypes.HWND
_u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
_u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_u.IsWindowVisible.argtypes = [wintypes.HWND]
_u.GetWindowLongW.restype = ctypes.c_long
_u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_u.SetWindowLongW.restype = ctypes.c_long
_u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
_u.SetWindowPos.restype = wintypes.BOOL
_u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, wintypes.UINT]
HWND_TOPMOST   = wintypes.HWND(-1)
SWP_NOSIZE     = 0x0001
SWP_NOACTIVATE = 0x0010


def cam_origin():
    """Top-left (x, y) of the visible phone-cam window, or None."""
    try:
        for title in CAM_TITLES:
            hwnd = _u.FindWindowW(None, title)
            if hwnd and _u.IsWindowVisible(hwnd):
                r = wintypes.RECT()
                if _u.GetWindowRect(hwnd, ctypes.byref(r)) and r.left < 4000 and r.top < 4000:
                    return r.left, r.top     # (skip scrcpy's off-screen feed in bubble mode)
    except Exception:
        pass
    return None


root = tk.Tk()
root.report_callback_exception = lambda *a: log_err(traceback.format_exc())
root.title("GestureMode")
root.overrideredirect(True)
root.attributes("-topmost", True)
try:
    root.attributes("-alpha", 0.93)
except Exception:
    pass

wrap = tk.Frame(root, bg=DEFAULT[0], bd=0, highlightthickness=2, highlightbackground="#0b1220")
wrap.pack()
dot = tk.Label(wrap, text="●", font=("Segoe UI", 13, "bold"), bg=DEFAULT[0], fg=DEFAULT[1])
dot.pack(side="left", padx=(10, 5), pady=5)
text = tk.Label(wrap, text=DEFAULT[2], font=("Segoe UI Semibold", 12, "bold"), bg=DEFAULT[0], fg=DEFAULT[1])
text.pack(side="left", padx=(0, 12), pady=5)
root.update_idletasks()
_badge_hwnd = root.winfo_id()
_bh = root.winfo_height() or 34

# off_x/off_y = where the badge sits relative to the cam's top-left.
# default: just ABOVE the cam's top edge, left-aligned, so the cam can't cover it.
off_x, off_y = 0, -(_bh + 4)
try:
    off_x, off_y = (int(v) for v in open(POS_FILE).read().split(","))
except Exception:
    pass
root.geometry(f"+{max(off_x, 0)}+{max(off_y, 0)}")   # placeholder until the first follow tick


def place(x, y):
    """Move the badge AND re-assert topmost (so the always-on-top cam can't cover it)."""
    try:
        _u.SetWindowPos(_badge_hwnd, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception:
        root.geometry(f"+{x}+{y}")


# --- drag to move; remember the offset relative to the cam window ---
_d = {"x": 0, "y": 0, "drag": False}
def _down(e):
    _d["x"], _d["y"], _d["drag"] = e.x, e.y, True
def _move(e):
    root.geometry(f"+{root.winfo_x() + e.x - _d['x']}+{root.winfo_y() + e.y - _d['y']}")
def _up(e):
    global off_x, off_y
    _d["drag"] = False
    org = cam_origin() if ATTACH else None
    if org:
        off_x, off_y = root.winfo_x() - org[0], root.winfo_y() - org[1]
    elif not ATTACH:
        off_x, off_y = root.winfo_x(), root.winfo_y()
    else:
        return   # cam not found right now; keep the existing offset
    try:
        with open(POS_FILE, "w") as f:
            f.write(f"{off_x},{off_y}")
    except Exception:
        pass
for w in (wrap, dot, text):
    w.bind("<Button-1>", _down)
    w.bind("<B1-Motion>", _move)
    w.bind("<ButtonRelease-1>", _up)


# --- never steal keyboard focus from whatever you're dictating into ---
def _no_activate():
    try:
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        ex = _u.GetWindowLongW(_badge_hwnd, GWL_EXSTYLE)
        _u.SetWindowLongW(_badge_hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    except Exception:
        pass


START = time.time()
cur = [None]
last_good = [time.time()]


def read_status():
    try:
        with open(MODE_FILE) as f:
            raw = f.read().strip().split("\n")
        mode = raw[0].strip()
        ts = float(raw[1]) if len(raw) > 1 else None
        if mode and ts is not None:
            return mode, ts
    except Exception:
        pass
    return None, None


def tick():
    now = time.time()
    mode, ts = read_status()
    if mode and ts:
        last_good[0] = ts
        if mode == "OFF":
            root.destroy(); return
        if mode != cur[0]:
            cur[0] = mode
            bg, fg, label = STYLE.get(mode, DEFAULT)
            wrap.configure(bg=bg)
            dot.configure(bg=bg, fg=fg)
            text.configure(bg=bg, fg=fg, text=label)
    # close only when the engine has genuinely stopped updating (stale ts), past startup grace
    if now - last_good[0] > 5 and now - START > 5:
        root.destroy(); return
    # follow the cam window + stay above it (unless you're mid-drag)
    if ATTACH and not _d["drag"]:
        org = cam_origin()
        if org:
            place(org[0] + off_x, org[1] + off_y)
    root.after(80, tick)


_no_activate()
tick()
try:
    root.mainloop()
except Exception:
    log_err(traceback.format_exc())
