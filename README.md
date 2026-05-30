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
| **`GestureControl.bat`** | Hand gestures → keystrokes (drives Claude Code `/voice`) |
| **`PhoneSuite.bat`** | Bubble **+** gesture control together, one launch |
| `PhoneCam.bat` | Just the raw scrcpy camera window (for OBS, etc.) |
| `Stop-PhoneSuite.bat` | Stop everything |
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
| ✊ Fist | Pause recording; **when paused**, insert a newline |
| 👍 Thumbs up | Pause recording; **when paused**, send (Enter) |
| ✌️ Victory | Snipping tool (Win+Shift+S) |

Sending is always a deliberate thumbs-up on a paused prompt — nothing auto-sends mid-dictation.
Everything is configurable at the top of `gesture_control.py` (`DICTATION_MODE`, `HOLD_WINDOW`,
`BINDINGS`, `NEWLINE_KEYS`, …).

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
