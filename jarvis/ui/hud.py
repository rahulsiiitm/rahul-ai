"""jarvis/ui/hud.py — Animated circular JARVIS HUD drawn on tkinter Canvas."""
from __future__ import annotations
import math, tkinter as tk

SKY  = "#00BFFF"; GLOW = "#1E90FF"; DIM = "#0a2035"; WHITE = "#ffffff"; BG = "#050810"
RING_COLS = ["#002040", "#003060", SKY, GLOW, SKY, "#003060", "#002040"]

class HudCanvas(tk.Canvas):
    def __init__(self, parent, size=350, **kw):
        super().__init__(parent, width=size, height=size, bg=BG, highlightthickness=0, **kw)
        self.cx = self.cy = size // 2
        self.R  = size // 2 - 10
        self._a1 = 0.0; self._a2 = 120.0; self._pulse = 0.0
        self._status = "STANDBY"; self._tick_active = set()
        self._running = True
        self._draw()

    def set_status(self, s: str): self._status = s
    def stop(self): self._running = False

    def _draw(self):
        if not self._running: return
        self.delete("all"); cx, cy, R = self.cx, self.cy, self.R

        # Outer tick ring
        for i in range(72):
            ang = math.radians(i * 5 - 90)
            r_out = R; r_in = R - (8 if i % 9 == 0 else 5 if i % 3 == 0 else 3)
            col   = SKY if i % 9 == 0 else (GLOW if i % 3 == 0 else DIM)
            lw    = 2 if i % 9 == 0 else 1
            self.create_line(cx + r_out*math.cos(ang), cy + r_out*math.sin(ang),
                             cx + r_in *math.cos(ang), cy + r_in *math.sin(ang),
                             fill=col, width=lw)

        # Outer rotating arc (glow layers)
        r = R - 14
        for offset, col, wid in [(-3,"#003050",6), (-1,"#005070",4), (0, SKY, 2)]:
            self.create_arc(cx-r+offset, cy-r+offset, cx+r-offset, cy+r-offset,
                            start=self._a1, extent=260, outline=col, width=wid, style="arc")

        # Middle counter-arc
        r2 = R - 50
        for offset, col, wid in [(-2,"#002844",5),(0, GLOW, 2)]:
            self.create_arc(cx-r2+offset, cy-r2+offset, cx+r2-offset, cy+r2-offset,
                            start=-self._a2, extent=200, outline=col, width=wid, style="arc")

        # Small segment dots around middle ring
        for i in range(12):
            ang = math.radians(i * 30 + self._a1 * 0.5)
            x = cx + (r2 - 8) * math.cos(ang); y = cy + (r2 - 8) * math.sin(ang)
            col = SKY if i % 3 == 0 else DIM
            self.create_oval(x-3, y-3, x+3, y+3, fill=col, outline="")

        # Inner pulsing ring
        p   = abs(math.sin(self._pulse)) * 12
        r3  = R - 95
        col3= SKY if self._status == "STANDBY" else ("#00FF88" if self._status in ("THINKING","RUNNING") else GLOW)
        for offset, col, wid in [(-2, "#003050", 5), (0, col3, 2)]:
            self.create_oval(cx-r3-p+offset, cy-r3-p+offset,
                             cx+r3+p-offset, cy+r3+p-offset,
                             outline=col, width=wid)

        # Core fill
        r4 = R - 120
        self.create_oval(cx-r4, cy-r4, cx+r4, cy+r4, fill="#020d18", outline=GLOW, width=1)

        # Status text
        self.create_text(cx, cy-10, text="JARVIS", fill=SKY,  font=("Consolas", 13, "bold"))
        self.create_text(cx, cy+10, text=self._status, fill=WHITE, font=("Consolas", 10))

        # Advance angles
        self._a1   = (self._a1   + 1.4)  % 360
        self._a2   = (self._a2   + 2.1)  % 360
        self._pulse = self._pulse + 0.055

        self.after(16, self._draw)   # ~60 fps
