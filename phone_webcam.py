"""
Phone as a virtual WEBCAM.

Captures the scrcpy "PhoneCam" window and feeds it into a virtual camera (the OBS
Virtual Camera backend - no OBS needs to be running), so any app can select the phone
as a webcam: Google Meet, Zoom, WhatsApp, Telegram, Discord, Messenger, OBS, streaming
software, etc.

Run via PhoneWebcam.bat (starts the hidden phone feed first), or directly:
    python phone_webcam.py
Then in your video app pick "OBS Virtual Camera" as the camera.

Requires: pip install pyvirtualcam opencv-python numpy windows-capture
(plus OBS installed, which registers the OBS Virtual Camera device).
"""
import time, threading
import numpy as np
import cv2
import pyvirtualcam
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

WINDOW_NAME = "PhoneCam"
FPS = 30
MIRROR = False   # set True if you look left-right flipped in the call
# Rotation is handled at the source by scrcpy's --capture-orientation (set via the
# launcher's -Rotate flag), so the bubble, gestures, and webcam all stay consistent.


class FrameGrabber:
    def __init__(self, name):
        self.name = name
        self.latest = None
        self.lock = threading.Lock()
        self.control = None

    def start(self):
        cap = WindowsCapture(cursor_capture=False, draw_border=False, window_name=self.name)

        @cap.event
        def on_frame_arrived(frame: Frame, ctl: InternalCaptureControl):
            with self.lock:
                self.latest = np.ascontiguousarray(frame.frame_buffer[:, :, :3])

        @cap.event
        def on_closed():
            pass

        try:
            self.control = cap.start_free_threaded()
        except AttributeError:
            threading.Thread(target=cap.start, daemon=True).start()

    def get(self):
        with self.lock:
            return None if self.latest is None else self.latest.copy()


def main():
    grab = FrameGrabber(WINDOW_NAME)
    grab.start()

    first = None
    for _ in range(40):
        first = grab.get()
        if first is not None:
            break
        time.sleep(0.25)
    if first is None:
        print("No PhoneCam frames. Is scrcpy 'PhoneCam' running? (use PhoneWebcam.bat)")
        return

    h, w = first.shape[:2]
    try:
        cam = pyvirtualcam.Camera(width=w, height=h, fps=FPS)
    except Exception as e:
        print("Could not open a virtual camera:", e)
        print("Make sure OBS (with its Virtual Camera) is installed.")
        return

    with cam:
        print("=" * 60)
        print(f"  PHONE WEBCAM LIVE  ->  {cam.device}  ({w}x{h}@{FPS})")
        print("  In your video app, choose this camera:")
        print(f"      {cam.device}")
        print("  Works in Meet, Zoom, WhatsApp, Telegram, Discord, OBS, streaming...")
        print("  Ctrl+C to stop.")
        print("=" * 60)
        try:
            while True:
                frame = grab.get()
                if frame is not None:
                    if MIRROR:
                        frame = cv2.flip(frame, 1)
                    if frame.shape[1] != w or frame.shape[0] != h:
                        frame = cv2.resize(frame, (w, h))
                    cam.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                cam.sleep_until_next_frame()
        except KeyboardInterrupt:
            pass
    print("\nPhone webcam stopped.")


if __name__ == "__main__":
    main()
