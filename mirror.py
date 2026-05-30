"""
Webcam Mirror — always-on-top draggable circle
Requires: pip install opencv-python pillow pygrabber
Zero GPU usage. ~40MB RAM. Pure CPU.

Right-click the circle for options (resize, switch camera, quit).
Drag the circle to move it.
"""

import tkinter as tk
from tkinter import Menu, messagebox
import cv2
from PIL import Image, ImageDraw, ImageTk
import os
import sys

# Suppress OpenCV's noisy probe warnings during auto-detection
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

# Config
DEFAULT_SIZE = 200        # Starting diameter in pixels
FPS = 24                  # Frame rate (lower = less CPU)
CAMERA_INDEX = None       # None = auto-detect; set to int to force
BORDER_WIDTH = 2
BORDER_COLOR = (80, 80, 80)
SIZES = [120, 160, 200, 260, 320]

# Cameras to skip in auto-detect (still listed in menu, just not auto-picked)
AUTO_SKIP_KEYWORDS = ("obs", "virtual", "snap", "manycam", "xsplit")


def list_dshow_devices():
    """Return [(index, name), ...] for DirectShow cameras. Falls back to numeric labels."""
    try:
        from pygrabber.dshow_graph import FilterGraph
        names = FilterGraph().get_input_devices()
        return [(i, n) for i, n in enumerate(names)]
    except Exception:
        # Fallback: probe indexes 0-4 and label generically
        out = []
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                out.append((i, f"Camera {i}"))
            cap.release()
        return out


def open_camera(idx):
    """Open camera by DSHOW index. Returns cv2.VideoCapture or None."""
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    return cap


def auto_pick(devices):
    """Pick first device that returns frames AND isn't a known virtual camera. Falls back to any working device."""
    skipped = []
    for idx, name in devices:
        if any(kw in name.lower() for kw in AUTO_SKIP_KEYWORDS):
            skipped.append((idx, name))
            continue
        cap = open_camera(idx)
        if cap is None:
            continue
        ret, _ = cap.read()
        if ret:
            return cap, idx
        cap.release()
    # Nothing preferred worked. Try the skipped ones (OBS etc.) as last resort.
    for idx, name in skipped:
        cap = open_camera(idx)
        if cap is None:
            continue
        ret, _ = cap.read()
        if ret:
            return cap, idx
        cap.release()
    return None, -1


class MirrorApp:
    def __init__(self):
        self.size = DEFAULT_SIZE
        self.running = True
        self.drag_x = 0
        self.drag_y = 0

        # Enumerate cameras
        self.devices = list_dshow_devices()
        if not self.devices:
            self._fatal(
                "No cameras detected.\n\n"
                "Check Windows Settings -> Privacy -> Camera and make sure "
                "desktop apps are allowed to access the camera."
            )
            return

        # Open first usable camera (skipping OBS/virtual cams when possible)
        if CAMERA_INDEX is None:
            self.cap, self.current_idx = auto_pick(self.devices)
        else:
            self.cap = open_camera(CAMERA_INDEX)
            self.current_idx = CAMERA_INDEX if self.cap else -1

        if self.cap is None:
            # Still build the window so the user can pick from the menu
            self.current_idx = -1

        # Window
        self.root = tk.Tk()
        self.root.title("Mirror")
        self.root.overrideredirect(True)        # No title bar
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-transparentcolor', '#010101')  # Chroma key
        self.root.configure(bg='#010101')

        # Position bottom-right
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{self.size}x{self.size}+{sw - self.size - 50}+{sh - self.size - 80}')

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg='#010101',
            highlightthickness=0,
            cursor='fleur',
        )
        self.canvas.pack()

        # Drag
        self.canvas.bind('<Button-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_move)

        # Right-click menu
        self.menu = Menu(self.root, tearoff=0, bg='#1e1e1e', fg='#cccccc',
                         activebackground='#333', activeforeground='#fff',
                         font=('Segoe UI', 9))
        self.canvas.bind('<Button-3>', self._show_menu)

        # Circular mask (pre-compute)
        self._build_mask()

        # Start frame loop
        self._update_frame()
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.mainloop()

    def _build_mask(self):
        """Pre-build a circular alpha mask at current size."""
        self.mask = Image.new('L', (self.size, self.size), 0)
        draw = ImageDraw.Draw(self.mask)
        b = BORDER_WIDTH
        # Outer circle (border)
        draw.ellipse([0, 0, self.size - 1, self.size - 1], fill=255)
        self.mask_inner = Image.new('L', (self.size, self.size), 0)
        draw2 = ImageDraw.Draw(self.mask_inner)
        draw2.ellipse([b, b, self.size - 1 - b, self.size - 1 - b], fill=255)

    def _update_frame(self):
        if not self.running:
            return

        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                self._render_frame(frame)

        self.root.after(1000 // FPS, self._update_frame)

    def _render_frame(self, frame):
        # Mirror horizontally
        frame = cv2.flip(frame, 1)

        # Crop to square from center
        h, w = frame.shape[:2]
        side = min(h, w)
        y0 = (h - side) // 2
        x0 = (w - side) // 2
        frame = frame[y0:y0+side, x0:x0+side]

        # Resize
        frame = cv2.resize(frame, (self.size, self.size), interpolation=cv2.INTER_AREA)

        # BGR -> RGB -> PIL
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        # Add border + circular mask
        border_layer = Image.new('RGB', (self.size, self.size), BORDER_COLOR)
        result = Image.new('RGBA', (self.size, self.size), (1, 1, 1, 0))
        border_rgba = border_layer.copy()
        border_rgba.putalpha(self.mask)
        img_rgba = img.copy()
        img_rgba.putalpha(self.mask_inner)
        result.paste(border_rgba, (0, 0))
        result.paste(img_rgba, (0, 0), img_rgba)

        self.photo = ImageTk.PhotoImage(result)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)

    def _drag_start(self, e):
        self.drag_x = e.x
        self.drag_y = e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + (e.x - self.drag_x)
        y = self.root.winfo_y() + (e.y - self.drag_y)
        self.root.geometry(f'+{x}+{y}')

    def _show_menu(self, e):
        self.menu.delete(0, 'end')

        # Camera submenu
        cam_menu = Menu(self.menu, tearoff=0, bg='#1e1e1e', fg='#cccccc',
                        activebackground='#333', activeforeground='#fff',
                        font=('Segoe UI', 9))
        for idx, name in self.devices:
            marker = '* ' if idx == self.current_idx else '   '
            cam_menu.add_command(label=f"{marker}{name}",
                                 command=lambda i=idx: self._switch_camera(i))
        cam_menu.add_separator()
        cam_menu.add_command(label='   Refresh device list', command=self._refresh_devices)
        self.menu.add_cascade(label='  Camera', menu=cam_menu)

        # Size submenu
        size_menu = Menu(self.menu, tearoff=0, bg='#1e1e1e', fg='#cccccc',
                         activebackground='#333', activeforeground='#fff',
                         font=('Segoe UI', 9))
        for s in SIZES:
            marker = '* ' if s == self.size else '   '
            size_menu.add_command(label=f"{marker}{s}px",
                                  command=lambda sz=s: self._set_size(sz))
        self.menu.add_cascade(label='  Size', menu=size_menu)

        self.menu.add_separator()
        self.menu.add_command(label='   Quit', command=self._quit)
        self.menu.post(e.x_root, e.y_root)

    def _switch_camera(self, idx):
        if idx == self.current_idx and self.cap is not None:
            return
        old_cap = self.cap
        new_cap = open_camera(idx)
        if new_cap is None:
            messagebox.showerror("Camera Bubble",
                                 f"Could not open camera index {idx}.\n"
                                 "It may be in use by another app, or not currently active "
                                 "(e.g. phone webcam app not running).")
            return
        self.cap = new_cap
        self.current_idx = idx
        if old_cap is not None:
            old_cap.release()

    def _refresh_devices(self):
        self.devices = list_dshow_devices()

    def _set_size(self, s):
        self.size = s
        self.canvas.config(width=s, height=s)
        self.root.geometry(f'{s}x{s}')
        self._build_mask()

    def _quit(self):
        self.running = False
        if getattr(self, "cap", None) is not None:
            self.cap.release()
        self.root.destroy()

    def _fatal(self, msg):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Camera Bubble", msg)
        root.destroy()
        sys.exit(1)


if __name__ == '__main__':
    MirrorApp()
