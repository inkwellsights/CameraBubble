"""
Phone Camera Bubble (OBS-free).

Captures the scrcpy "PhoneCam" window directly via Windows Graphics Capture
and shows it as an always-on-top draggable circle. No OBS, no virtual camera.

Requires: pip install opencv-python pillow numpy windows-capture
The scrcpy PhoneCam window must be running (launch PhoneCam.bat first), but it
can be off-screen/behind other windows - WGC still captures it.

Drag the circle to move it. Right-click for size / quit.
"""

import tkinter as tk
from tkinter import Menu, messagebox
import threading
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageTk
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

WINDOW_NAME = "PhoneCam"   # scrcpy window title to capture
DEFAULT_SIZE = 200
FPS = 24
BORDER_WIDTH = 2
BORDER_COLOR = (80, 80, 80)
SIZES = [120, 160, 200, 260, 320]


class FrameGrabber:
    """Background WGC capture of the PhoneCam window. Keeps the latest frame (BGR)."""
    def __init__(self, window_name):
        self.window_name = window_name
        self.latest = None
        self.lock = threading.Lock()
        self.control = None
        self.error = None
        self.closed = False

    def start(self):
        cap = WindowsCapture(cursor_capture=False, draw_border=False,
                             window_name=self.window_name)

        @cap.event
        def on_frame_arrived(frame: Frame, ctl: InternalCaptureControl):
            buf = frame.frame_buffer            # H x W x 4, BGRA
            bgr = np.ascontiguousarray(buf[:, :, :3])
            with self.lock:
                self.latest = bgr

        @cap.event
        def on_closed():
            self.closed = True

        try:
            # Non-blocking: runs capture on its own thread, returns a control handle.
            self.control = cap.start_free_threaded()
        except AttributeError:
            threading.Thread(target=cap.start, daemon=True).start()
        except Exception as e:
            self.error = e

    def get(self):
        with self.lock:
            return None if self.latest is None else self.latest.copy()

    def stop(self):
        try:
            if self.control is not None:
                self.control.stop()
        except Exception:
            pass


class BubbleApp:
    def __init__(self):
        self.size = DEFAULT_SIZE
        self.running = True

        self.grab = FrameGrabber(WINDOW_NAME)
        self.grab.start()

        self.root = tk.Tk()
        self.root.title("PhoneBubble")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{self.size}x{self.size}+{sw - self.size - 50}+{sh - self.size - 80}')

        self.canvas = tk.Canvas(self.root, width=self.size, height=self.size,
                                bg='#010101', highlightthickness=0, cursor='fleur')
        self.canvas.pack()
        self.canvas.bind('<Button-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_move)
        self.canvas.bind('<Button-3>', self._show_menu)

        self.menu = Menu(self.root, tearoff=0, bg='#1e1e1e', fg='#cccccc',
                         activebackground='#333', activeforeground='#fff',
                         font=('Segoe UI', 9))

        self._build_mask()
        self._waiting_logged = False
        self._update_frame()
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.mainloop()

    def _build_mask(self):
        b = BORDER_WIDTH
        self.mask = Image.new('L', (self.size, self.size), 0)
        ImageDraw.Draw(self.mask).ellipse([0, 0, self.size - 1, self.size - 1], fill=255)
        self.mask_inner = Image.new('L', (self.size, self.size), 0)
        ImageDraw.Draw(self.mask_inner).ellipse([b, b, self.size - 1 - b, self.size - 1 - b], fill=255)

    def _update_frame(self):
        if not self.running:
            return
        frame = self.grab.get()
        if frame is not None:
            self._render(frame)
        self.root.after(1000 // FPS, self._update_frame)

    def _render(self, frame):
        frame = cv2.flip(frame, 1)                       # mirror
        h, w = frame.shape[:2]
        side = min(h, w)
        y0, x0 = (h - side) // 2, (w - side) // 2
        frame = frame[y0:y0 + side, x0:x0 + side]        # center square
        frame = cv2.resize(frame, (self.size, self.size), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        result = Image.new('RGBA', (self.size, self.size), (1, 1, 1, 0))
        border = Image.new('RGB', (self.size, self.size), BORDER_COLOR)
        border.putalpha(self.mask)
        img_rgba = img.copy()
        img_rgba.putalpha(self.mask_inner)
        result.paste(border, (0, 0))
        result.paste(img_rgba, (0, 0), img_rgba)

        self.photo = ImageTk.PhotoImage(result)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)

    def _drag_start(self, e):
        self.drag_x, self.drag_y = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + (e.x - self.drag_x)
        y = self.root.winfo_y() + (e.y - self.drag_y)
        self.root.geometry(f'+{x}+{y}')

    def _show_menu(self, e):
        self.menu.delete(0, 'end')
        size_menu = Menu(self.menu, tearoff=0, bg='#1e1e1e', fg='#cccccc',
                         activebackground='#333', activeforeground='#fff', font=('Segoe UI', 9))
        for s in SIZES:
            marker = '* ' if s == self.size else '   '
            size_menu.add_command(label=f"{marker}{s}px", command=lambda sz=s: self._set_size(sz))
        self.menu.add_cascade(label='  Size', menu=size_menu)
        self.menu.add_separator()
        self.menu.add_command(label='   Quit', command=self._quit)
        self.menu.post(e.x_root, e.y_root)

    def _set_size(self, s):
        self.size = s
        self.canvas.config(width=s, height=s)
        self.root.geometry(f'{s}x{s}')
        self._build_mask()

    def _quit(self):
        self.running = False
        self.grab.stop()
        self.root.destroy()


if __name__ == '__main__':
    try:
        BubbleApp()
    except Exception as e:
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("Phone Bubble",
                             f"Could not start.\n\n{e}\n\n"
                             "Make sure the scrcpy 'PhoneCam' window is running (launch PhoneCam.bat first).")
        r.destroy()
