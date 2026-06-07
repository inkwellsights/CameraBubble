# CameraBubble

Turn an Android phone into a **wireless, fully open-source webcam** for Windows — plus an
always-on-top **circular webcam bubble** and **hand-gesture control** that drives Claude Code's
`/voice` dictation. Nothing is installed on the phone; everything runs locally on the PC.

Built with [scrcpy](https://github.com/Genymobile/scrcpy), [MediaPipe](https://github.com/google-ai-edge/mediapipe),
OpenCV, and [windows-capture](https://github.com/NiiightmareXD/windows-capture).

## What's in here

| Tool | What it does |
|---|---|
| **`PhoneBubble.bat`** | Phone rear camera as a draggable, always-on-top circular bubble |
| **`PhoneView.bat`** | Phone camera as a floating always-on-top window at full source quality (no bubble re-render = less CPU; rectangle, not circle) |
| **`GestureControl.bat`** | Hand gestures → keystrokes (drives Claude Code `/voice`) |
| **`PhoneSuite.bat`** | Phone view **+** gesture control together (asks rectangle or bubble; rectangle default) |
| **`PhoneWebcam.bat`** | Phone as a virtual webcam (Meet, Zoom, WhatsApp, Telegram, Discord…) |
| **`PhoneFeed.bat`** | Just the hidden feed, for streaming/recording in OBS |
| `Pair-Phone.bat` | One-time pairing for the wireless connection (Wi-Fi or Tailscale) |
| `SetRotation.bat` | Set camera rotation (also asked at every launch) |
| `Stop-PhoneSuite.bat` | Stop everything |
| `mode_badge.py` | Always-on-top mode pill (auto-launched by the gesture engine) |
| `mirror.py` | Standalone webcam-bubble (any DirectShow camera) |

## How it works

```
Android rear camera ──(scrcpy, Wi-Fi)──► hidden PhoneCam window
                                              │  (Windows Graphics Capture)
                          ┌───────────────────┴───────────────────┐
                          ▼                                        ▼
                 circular webcam bubble                  MediaPipe gesture engine
                 (phone_bubble.py)                       (gesture_control.py) → keystrokes
```

The phone connects over **Wi-Fi via scrcpy's wireless debugging** (no USB needed, no app on the
phone). scrcpy renders the camera to a hidden, off-screen window; both the bubble and the gesture
engine read that window's pixels via Windows Graphics Capture, so they coexist with no conflict.

## Requirements

- Windows 10/11
- [scrcpy](https://github.com/Genymobile/scrcpy) **2.0+** (camera mirroring): `winget install Genymobile.scrcpy`
- Python 3.10+ (tested on 3.13)
- An Android phone with **Developer Options → Wireless debugging** enabled, on the same Wi-Fi

## Setup

```powershell
# 1. scrcpy (bundles adb)
winget install Genymobile.scrcpy

# 2. Python deps
pip install -r requirements.txt

# 3. Download the MediaPipe gesture model (~8 MB) into this folder
curl -L -o gesture_recognizer.task https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
```

### Pair the phone (one time, over Wi-Fi)
1. Phone: **Settings → Developer options → Wireless debugging → On**.
2. Tap **Pair device with pairing code** — note the `IP:port` and 6-digit code.
3. On the PC: `adb pair <IP:port> <code>`. After pairing, the phone auto-connects via mDNS.

The launchers handle the connection automatically (with an `IP:port` prompt as a fallback).

## Usage

**Webcam bubble:**
```
PhoneBubble.bat          # asks rear/front, then shows the bubble
```

**Gesture-driven dictation** (with Claude Code `/voice`):
```
/voice hold              # run this inside Claude Code
GestureControl.bat       # then start the gesture engine (matches /voice mode)
GestureControl.bat --dry # test mode: logs detections, presses no keys
```

**Both at once:**
```
PhoneSuite.bat
```

### Gesture map (hold mode)

| Gesture | Action |
|---|---|
| ✋ Open palm | Talk — opens a 30s recording window; re-show palm to extend |
| ✊ Fist | Stop recording; **when stopped**, insert a newline |
| 👍 Thumbs up | Stop recording; **when stopped**, send (Enter) |
| ✌️ Victory | Snipping tool (Win+Shift+S) |
| 👎 Thumbs down | Freeze / unfreeze all gesture scanning (move your hands freely) |
| 🤟 Rock sign (enter) | Enter scroll mode (thumb + index + pinky). Then point one finger and tilt up/down to scroll. |
| ✊ Fist (in scroll) | Exit scroll mode. |
| ☝️ Point up | Enter **command mode** (one finger straight up). Then: Victory = copy, palm = paste, thumbs up = app switcher. |
| 👍 Thumbs up (in command) | Hold the Alt+Tab switcher open; move your **whole hand** right/left to step through windows. |
| ✊ Fist (in command) | Pick the highlighted window (when switching) and exit command mode. |

**Scroll** is a joystick, not a drag: show the rock sign (🤟, thumb + index + pinky) to enter scroll
mode, then drop to one pointing finger and tilt it up to scroll up, down to scroll down, hold level to
stop. Make a fist to exit. Entering and exiting use different gestures on purpose, so you always know
which one you're doing. The rock sign is one of MediaPipe's built-in trained gestures, so it detects
reliably; the landmark-based alternatives (`"shaka"`, `"three"`) tend to be jittery. Change it in one
line: `SCROLL_ENTER = "iloveyou"`. It scrolls whatever's under the mouse, so hover there first. Tune
`SCROLL_SPEED`, `SCROLL_DEADZONE`, and `SCROLL_INVERT` at the top of `gesture_control.py`.

**Command mode** is a second sub-mode for keyboard shortcuts. Point one finger straight up to enter,
then fire system actions with single gestures: **Victory = copy** (Ctrl+C) and **open palm = paste**
(Ctrl+V). **Thumbs up opens the app switcher**: it presses Alt and keeps it held so the Windows
Alt+Tab list stays on screen, then you move your **whole hand** right to step forward through the open
windows or left to step back, and make a **fist** to land on the one you want (Alt releases on the
highlighted window). That lets you jump to a specific window, not just the previous one. Make a fist
any time to exit command mode (or drop your hand for a few seconds, which also commits the switcher).
While in command mode, dictation and the normal gesture actions are paused so nothing fires by
accident. Pointing up is the only built-in trained gesture not already in use, so it detects as
reliably as palm or fist. If moving your hand right steps the wrong way, flip `CMD_TAB_INVERT`. Add
your own shortcuts in the `CMD_BINDINGS` table at the top of `gesture_control.py`.

**Mode badge.** A small always-on-top pill shows the current mode so you never have to watch the
console: **READY** (blue, palm to talk), **TALK** (green, recording), **SCROLL** (orange), **CMD**
(purple, command mode), **FROZEN** (gray, paused). Drag it onto your phone-cam view and it stays there. It launches with the gesture
engine and closes with it. Turn it off with `SHOW_BADGE = False`.

Sending is always a deliberate thumbs-up on a paused prompt — nothing auto-sends mid-dictation.
Everything is configurable at the top of `gesture_control.py` (`DICTATION_MODE`, `HOLD_WINDOW`,
`BINDINGS`, `NEWLINE_KEYS`, `PAUSE_GESTURE`, …).

## Use it as a webcam (video calls)

```
PhoneWebcam.bat          # asks rotation + rear/front, then exposes "OBS Virtual Camera"
```
In Meet / Zoom / WhatsApp / Telegram / Discord, pick **"OBS Virtual Camera"** as the camera.
Feeds the phone into a virtual camera via `pyvirtualcam` (OBS Virtual Camera backend — OBS must be
installed but does **not** need to be running).

## Stream / record in OBS

Don't use `PhoneWebcam.bat` here (it and OBS both want the virtual camera). Instead:
```
PhoneFeed.bat            # starts just the hidden phone feed
```
Then in OBS: **Sources → + → Window Capture → `[scrcpy.exe]: PhoneCam`**, and set
**Capture Method = "Windows 10 (1903 and up)"** (BitBlt shows black). Now stream/record normally —
and hit **Start Virtual Camera** in OBS if you also want your whole scene on a call.

## Camera rotation

Every launcher asks at startup (`[1] 0  [2] 90  [3] 180  [4] 270  [5] mirror`) and remembers your
choice in `rotation.txt` (one keypress after the first time). It's applied at the source via
scrcpy `--capture-orientation`, so it corrects the bubble, gestures, webcam, and OBS feed together.
Set it directly anytime with `SetRotation.bat 180`.

## Notes

- **CPU only.** MediaPipe's Windows wheel ships with the GPU delegate disabled; it runs fine on
  the optimized CPU (XNNPACK) path at ~30 fps.
- **Mode must match.** The gesture engine's `DICTATION_MODE` (`hold`/`tap`) must match Claude
  Code's `/voice` mode.
- **Keystrokes follow focus.** Gesture keystrokes go to whatever window is focused — keep Claude
  Code focused while dictating.
- Nothing is installed on the phone; the connection is wireless debugging only.

## License

MIT
