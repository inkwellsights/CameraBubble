"""
mode_badge.py - tiny always-on-top badge showing the gesture engine's current MODE.

Launched automatically by gesture_control.py (when SHOW_BADGE is True). It reads
_mode_status.txt (written by the engine) several times a second and shows a colored
pill: FROZEN / SCROLL / TALK / READY. Drag it onto your phone-cam view; it remembers
where you put it. It closes itself when the engine stops (status file goes stale).

No extra dependencies - tkinter ships with Python.
"""
import tkinter as tk
import os, time

_HERE     = os.path.dirname(os.path.abspath(__file__))
MODE_FILE = os.path.join(_HERE, "_mode_status.txt")
POS_FILE  = os.path.join(_HERE, "_badge_pos.txt")

# mode -> (background, foreground, label)
STYLE = {
    "FROZEN": ("#6b7280", "#ffffff", "FROZEN"),   # gray
    "SCROLL": ("#f97316", "#ffffff", "SCROLL"),   # orange
    "TALK":   ("#22c55e", "#08160c", "TALK"),     # green
    "READY":  ("#2563eb", "#ffffff", "READY"),    # blue
    "OFF":    ("#1f2937", "#9ca3af", "..."),      # dim
}
DEFAULT = STYLE["READY"]

root = tk.Tk()
root.title("GestureMode")
root.overrideredirect(True)                 # no title bar / borders
root.attributes("-topmost", True)
try:
    root.attributes("-alpha", 0.93)
except Exception:
    pass

# restore saved position (default near top-left)
px, py = 60, 60
try:
    px, py = (int(v) for v in open(POS_FILE).read().split(","))
except Exception:
    pass
root.geometry(f"+{px}+{py}")

wrap = tk.Frame(root, bg=DEFAULT[0], bd=0, highlightthickness=2, highlightbackground="#0b1220")
wrap.pack()
dot = tk.Label(wrap, text="●", font=("Segoe UI", 13, "bold"), bg=DEFAULT[0], fg=DEFAULT[1])
dot.pack(side="left", padx=(10, 5), pady=5)
text = tk.Label(wrap, text=DEFAULT[2], font=("Segoe UI Semibold", 12, "bold"), bg=DEFAULT[0], fg=DEFAULT[1])
text.pack(side="left", padx=(0, 12), pady=5)

# drag to move; save the position when released so it stays put next time
_d = {"x": 0, "y": 0}
def _down(e): _d["x"], _d["y"] = e.x, e.y
def _move(e):
    root.geometry(f"+{root.winfo_x() + e.x - _d['x']}+{root.winfo_y() + e.y - _d['y']}")
def _up(e):
    try:
        with open(POS_FILE, "w") as f:
            f.write(f"{root.winfo_x()},{root.winfo_y()}")
    except Exception:
        pass
for w in (wrap, dot, text):
    w.bind("<Button-1>", _down)
    w.bind("<B1-Motion>", _move)
    w.bind("<ButtonRelease-1>", _up)

# keep the badge from stealing keyboard focus from whatever you're dictating into
def _no_activate():
    try:
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        hwnd = root.winfo_id()
        u = ctypes.windll.user32
        ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
        u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    except Exception:
        pass

START = time.time()
cur = [None]
def poll():
    try:
        raw = open(MODE_FILE).read().strip().split("\n")
        mode = raw[0].strip()
        ts = float(raw[1]) if len(raw) > 1 else time.time()
    except Exception:
        mode, ts = None, 0.0
    now = time.time()
    # engine gone (file missing/stale) once past the startup grace -> close the badge
    if (not mode or mode == "OFF" or now - ts > 4) and now - START > 4:
        root.destroy(); return
    if mode and mode != cur[0]:
        cur[0] = mode
        bg, fg, label = STYLE.get(mode, DEFAULT)
        wrap.configure(bg=bg)
        dot.configure(bg=bg, fg=fg)
        text.configure(bg=bg, fg=fg, text=label)
    root.after(120, poll)

root.update_idletasks()
_no_activate()
poll()
root.mainloop()
