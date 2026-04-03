#!/usr/bin/env python3
"""
Claude Performance Dashboard — Vintage Instrument Cluster
Monitors Claude Code session performance in real-time via JSONL session files.
Spring-damper needle physics with intentional idle quiver.
"""
import sys
import json
import math
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ── Performance Constants ─────────────────────────────────────────────────
ITL_NORM_MAX_MS = 2800
ITL_WARNING_MAX_MS = 12000
HEARTBEAT_TIMEOUT_SEC = 20
CONTEXT_LIMIT = 1_000_000
POLL_INTERVAL_MS = 1500
SPEEDOMETER_WINDOW = 5
SPEED_MAX = 100
BOOST_MAX = 10

# ── Relative paths to assets ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent / "assets"
DRUM_STRIP_PATH = BASE_DIR / "odometer_drum.png"
RED_NEEDLE_PATH = BASE_DIR / "red_needle.png"
ORANGE_NEEDLE_PATH = BASE_DIR / "orange_needle.png"
DARK_MM_NEEDLE_PATH = BASE_DIR / "dark_needle_mm.png"
YELLOW_MM_NEEDLE_PATH = BASE_DIR / "yellow_needle_mm.png"
FUEL_MM_NEEDLE_PATH = BASE_DIR / "fuel_needle_mm.png"
RED_MODERN_1_PATH = BASE_DIR / "red_needle_modern_1.png"
RED_MODERN_2_PATH = BASE_DIR / "red_needle_modern_2.png"
YELLOW_MODERN_PATH = BASE_DIR / "yellow_needle_modern.png"
CHRONO_SECOND_PATH = BASE_DIR / "chrono_second.png"
CHRONO_MINUTE_PATH = BASE_DIR / "chrono_minute.png"
CHRONO_HOUR_PATH = BASE_DIR / "chrono_hour.png"
CHRONO_SECOND_MM_PATH = BASE_DIR / "chrono_sec_mm.png"
CHRONO_MINUTE_MM_PATH = BASE_DIR / "chrono_min_mm.png"
CHRONO_HOUR_MM_PATH = BASE_DIR / "chrono_hour_mm.png"
LIGHT_OFF_PATH = BASE_DIR / "light_off.png"
LIGHT_ON_PATH = BASE_DIR / "light_on.png"
CYAN_FUTURE_PATH = BASE_DIR / "future" / "needle_cyan_future_1024.png"
YELLOW_FUTURE_PATH = BASE_DIR / "future" / "needle_yellow_future_1024.png"
PURPLE_FUTURE_PATH = BASE_DIR / "future" / "needle_purple_future_1024.png"
CHRONO_HOUR_FUTURE_PATH = BASE_DIR / "future" / "chrono_hour_future.png"
CHRONO_MIN_FUTURE_PATH = BASE_DIR / "future" / "chrono_min_future.png"
CHRONO_SEC_FUTURE_PATH = BASE_DIR / "future" / "chrono_sec_future.png"

# ── Needle Source Geometry (measured from 1024x1024 PNGs) ─────────────────
RED_HUB = (512, 835)
RED_TIP_DIST = 713
ORANGE_HUB = (512, 842)
ORANGE_TIP_DIST = 735
DARK_MM_HUB = (481, 661)
DARK_MM_TIP_DIST = 651
YELLOW_MM_HUB = (493, 688)
YELLOW_MM_TIP_DIST = 682
FUEL_MM_HUB = (509, 504)
FUEL_MM_TIP_DIST = 200
RED_MODERN_1_HUB = (476, 617)
RED_MODERN_1_TIP_DIST = 385
RED_MODERN_2_HUB = (492, 601)
RED_MODERN_2_TIP_DIST = 369
YELLOW_MODERN_HUB = (500, 502)
YELLOW_MODERN_TIP_DIST = 124
# Chrono hands: all hubs at canvas center (512,512), rivet placed there by image processing
CHRONO_HUB = (512, 512)
CHRONO_TIP_DIST = 501
# MM chrono hands — black replacements (measured from rivet holes)
# MM chrono hands — pivot from dark rivet holes (darkness=0, surrounded)
CHRONO_MM_HOUR_HUB = (509, 642)   # A: stubby, height=181px
CHRONO_MM_HOUR_TIP_DIST = 102
CHRONO_MM_MIN_HUB = (520, 534)    # B: medium, height=550px
CHRONO_MM_MIN_TIP_DIST = 268
CHRONO_MM_SEC_HUB = (521, 593)    # C: long double-ended, height=368px
CHRONO_MM_SEC_TIP_DIST = 187
# Future neon needles (1024x1024 PNGs with glow)
CYAN_FUTURE_HUB = (507, 945)
CYAN_FUTURE_TIP_DIST = 896
YELLOW_FUTURE_HUB = (509, 948)
YELLOW_FUTURE_TIP_DIST = 882
PURPLE_FUTURE_HUB = (507, 945)    # same geometry as cyan
PURPLE_FUTURE_TIP_DIST = 896

# ── Animation ─────────────────────────────────────────────────────────────
NEEDLE_DAMPING = 0.15
NEEDLE_SPRING = 0.04
JITTER_FREQ = 8.0
JITTER_AMP = 0.20
GAUGE_UPDATE_MS = 16       # ~60fps
CLOCK_UPDATE_MS = 50

# ── Dashboard Skin Configurations ─────────────────────────────────────────
SKINS = {
    "vintage": {
        "name": "Vintage",
        "image": "dashboard_dg.png",
        "glass": "glass_overlay_transparent.png",
        "native_w": 1376,
        "native_h": 752,
        "speed": {      # Big left — Tokens per Second
            "cx": 463, "cy": 358, "r": 186,
            "start": 225, "sweep": 270,
            "max": 100, "needle": "red",
            "data_key": "speed",
        },
        "boost": {      # Big right — MCP Boost (-10 to +10, zero at 12 o'clock)
            "cx": 929, "cy": 358, "r": 186,
            "start": 180, "sweep": 180,
            "max": 20, "needle": "red",
            "data_key": "boost",
        },
        "fuel": {       # Small right — Tokens
            "cx": 1222, "cy": 375, "r": 85,
            "start": 35.7, "sweep": 71.4,
            "max": 100, "needle": "orange",
            "data_key": "context_pct",
        },
        "clock": {"cx": 156, "cy": 375, "r": 86},
        "led": {"cx": 690, "cy": 730},
        "odometer": {"cx": 699, "cy": 605, "w": 318, "h": 50, "digits": 12},
        "star_cover": (1310, 690, 1376, 752),
    },
    "modern": {
        "name": "Sports",
        "image": "dashboard_mg.png",
        "glass": None,
        "native_w": 1376,
        "native_h": 752,
        "speed": {      # Big left — Tokens/sec
            "cx": 463, "cy": 360, "r": 184,
            "start": 225, "sweep": 270,
            "max": 200, "needle": "red_modern_1",
            "data_key": "speed",
        },
        "boost": {      # Big right — MCP Boost (-10 to +10, zero at 12 o'clock)
            "cx": 935, "cy": 360, "r": 160,
            "start": 180, "sweep": 180,
            "max": 20, "needle": "red_modern_2",
            "data_key": "boost",
        },
        "fuel": {       # Small right — Context remaining
            "cx": 1252, "cy": 377, "r": 60,
            "start": 35.7, "sweep": 71.4,
            "max": 100, "needle": "yellow_modern",
            "data_key": "context_pct",
        },
        "clock": {"cx": 156, "cy": 377, "r": 86},
        "led": {"cx": 690, "cy": 730},
        "odometer": {"cx": 699, "cy": 605, "w": 318, "h": 50, "digits": 12, "style": "digital"},
        "star_cover": (1310, 690, 1376, 752),
    },
    "madmax": {
        "name": "Apocalypse",
        "image": "dashboard_mm.png",
        "glass": "glass_overlay_mm.png",
        "native_w": 1376,
        "native_h": 752,
        "speed": {      # Big left — Tokens/Sec (0-200)
            "cx": 463, "cy": 358, "r": 186,
            "start": 225, "sweep": 270,
            "max": 200, "needle": "dark_mm",
            "data_key": "speed",
        },
        "latency": {    # Big right — Latency / MCP Boost (0-100)
            "cx": 929, "cy": 358, "r": 186,
            "start": 225, "sweep": 270,
            "max": 100, "needle": "yellow_mm",
            "data_key": "latency",
        },
        "fuel": {       # Small right — Context remaining (E to F, counter-clockwise)
            "cx": 1254, "cy": 375, "r": 85,
            "start": 180, "sweep": 180,
            "max": 100, "needle": "fuel_chrono_sec_mm",
            "data_key": "fuel",
        },
        "clock": {"cx": 156, "cy": 375, "r": 86,
                  "chrono_hands": "mm"},
        "led": {"cx": 690, "cy": 730},
        "odometer": {"cx": 699, "cy": 605, "w": 318, "h": 50, "digits": 12},
        "star_cover": (1310, 690, 1376, 752),
    },
    "future": {
        "name": "Futuristic",
        "image": "future/dashboard_future.png",
        "glass": None,
        "native_w": 1376,
        "native_h": 752,
        "speed": {      # Big left — Tokens/Sec (0-200)
            "cx": 463, "cy": 358, "r": 186,
            "start": 225, "sweep": 270,
            "max": 200, "needle": "yellow_future",
            "data_key": "speed",
        },
        "latency": {    # Big right — Latency (0-100)
            "cx": 931, "cy": 358, "r": 186,
            "start": 225, "sweep": 270,
            "max": 100, "needle": "cyan_future",
            "data_key": "latency",
        },
        "fuel": {       # Small right — Context Tank (F at 4:30, E at 7:30, CCW)
            "cx": 1254, "cy": 375, "r": 85,
            "start": -45, "sweep": -270,
            "max": 100, "needle": "purple_future",
            "data_key": "context_pct",
        },
        "clock": {"cx": 156, "cy": 375, "r": 86,
                  "chrono_hands": "future"},
        "led": {"cx": 690, "cy": 730},
        "odometer": {"cx": 699, "cy": 605, "w": 318, "h": 50, "digits": 12, "style": "glow"},
        "star_cover": (1310, 690, 1376, 752),
    },
}

# ── Data Helpers ──────────────────────────────────────────────────────────
def find_active_jsonl():
    """Find the most recently modified JSONL session file."""
    candidates = []
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None
    for project in claude_dir.iterdir():
        if project.is_dir():
            for f in project.iterdir():
                if f.suffix == ".jsonl" and "subagents" not in str(f):
                    candidates.append(f)
    return max(candidates, key=lambda f: f.stat().st_mtime) if candidates else None


def parse_session(filepath):
    """Parse a JSONL session file and extract performance metrics."""
    total_output = 0
    output_events = 0
    context_size = 0
    speed = 0.0
    ttft_ms = 0.0
    cache_hit_ratio = 0.0

    turn_speeds = []       # per-response generation speeds (tok/sec)
    turn_cache_ratios = [] # per-response cache hit ratios
    last_event_ts = None   # timestamp of any preceding event
    last_user_ts = None
    first_assistant_after_user_ts = None

    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")
                timestamp_str = obj.get("timestamp")
                ts = None
                if timestamp_str:
                    try:
                        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
                    except (ValueError, TypeError):
                        pass

                if msg_type == "user" and ts:
                    last_user_ts = ts
                    first_assistant_after_user_ts = None

                elif msg_type == "assistant" and "message" in obj:
                    usage = obj["message"].get("usage", {})
                    out_tokens = usage.get("output_tokens", 0)
                    total_output += out_tokens
                    output_events += 1

                    # Context size from latest turn
                    inp = usage.get("input_tokens", 0)
                    cache_create = usage.get("cache_creation_input_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    ctx = inp + cache_create + cache_read
                    if ctx > 0:
                        context_size = ctx

                    # Per-response generation speed (excludes idle time)
                    if last_event_ts and ts and out_tokens > 0:
                        delta = ts - last_event_ts
                        if delta > 0.1:  # ignore sub-100ms deltas (system noise)
                            turn_speeds.append(out_tokens / delta)

                    # Per-response cache hit ratio
                    if ctx > 0:
                        turn_cache_ratios.append(cache_read / ctx)

                    # TTFT: first assistant response after user message
                    if last_user_ts and first_assistant_after_user_ts is None and ts:
                        first_assistant_after_user_ts = ts
                        ttft_ms = (ts - last_user_ts) * 1000

                # Update last_event_ts for ALL event types so idle gaps are excluded
                if ts:
                    last_event_ts = ts

    except (OSError, IOError):
        pass

    # Speed: average of recent per-response generation speeds
    if turn_speeds:
        window = turn_speeds[-SPEEDOMETER_WINDOW:]
        speed = sum(window) / len(window)

    # Cache hit ratio: rolling average of recent responses
    if turn_cache_ratios:
        window = turn_cache_ratios[-SPEEDOMETER_WINDOW:]
        cache_hit_ratio = sum(window) / len(window)

    context_pct = min((context_size / CONTEXT_LIMIT) * 100, 100) if context_size > 0 else 0

    return {
        "speed": speed,
        "context_pct": context_pct,
        "total_output": total_output,
        "output_events": output_events,
        "ttft_ms": ttft_ms,
        "context_size": context_size,
        "cache_hit_ratio": cache_hit_ratio,
    }


def choose_skin():
    """Show a startup dialog to choose the dashboard skin."""
    chosen = {"skin": None}

    dialog = tk.Tk()
    dialog.title("GAiges Cluster")
    dialog.configure(bg="#1a1a1a")
    dialog.resizable(False, False)

    # Center on screen
    dw, dh = 340, 330
    sx = (dialog.winfo_screenwidth() - dw) // 2
    sy = (dialog.winfo_screenheight() - dh) // 2
    dialog.geometry(f"{dw}x{dh}+{sx}+{sy}")

    label = tk.Label(dialog, text="Choose Dashboard", font=("Helvetica", 18, "bold"),
                     fg="#cccccc", bg="#1a1a1a")
    label.pack(pady=(25, 20))

    def pick(skin_key):
        chosen["skin"] = skin_key
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg="#1a1a1a")
    btn_frame.pack()

    for key, skin in SKINS.items():
        btn = tk.Button(btn_frame, text=skin["name"], font=("Helvetica", 14, "bold"),
                        width=16, height=2, bg="#444444", fg="#000000",
                        activebackground="#666666", activeforeground="#000000",
                        highlightbackground="#444444",
                        relief="raised", bd=2,
                        command=lambda k=key: pick(k))
        btn.pack(pady=5)

    dialog.protocol("WM_DELETE_WINDOW", lambda: (chosen.update({"skin": "vintage"}), dialog.destroy()))
    dialog.mainloop()
    return chosen["skin"] or "vintage"


class TokenDashboard:
    def __init__(self, skin_key="modern"):
        self._skin_key = skin_key
        self._skin = SKINS[skin_key]

        self.root = tk.Tk()
        self.root.title("Claude Performance Dashboard")
        self.root.configure(bg="#000000")

        # Native dimensions from skin
        self._native_w = self._skin["native_w"]
        self._native_h = self._skin["native_h"]

        # Load dashboard background
        img_path = BASE_DIR / self._skin["image"]
        try:
            self._src_image = Image.open(str(img_path)).convert("RGBA")
        except Exception as e:
            print(f"Error loading background: {e}")
            self._src_image = Image.new("RGBA", (self._native_w, self._native_h), "#1a0d00")

        # Load glass overlay if skin has one
        self._glass_image = None
        glass_file = self._skin.get("glass")
        if glass_file:
            glass_path = BASE_DIR / glass_file
            try:
                self._glass_image = Image.open(str(glass_path)).convert("RGBA")
            except Exception:
                print(f"{glass_file} not found — skipping overlay")

        # Load LEDs
        self._light_off = self._light_on = None
        try:
            self._light_off = Image.open(str(LIGHT_OFF_PATH)).convert("RGBA")
            self._light_on = Image.open(str(LIGHT_ON_PATH)).convert("RGBA")
        except Exception:
            print("LED images missing — falling back to canvas ovals")

        # Load needles
        self._needle_images = {}
        needle_paths = {
            "red": RED_NEEDLE_PATH,
            "orange": ORANGE_NEEDLE_PATH,
            "dark_mm": DARK_MM_NEEDLE_PATH,
            "yellow_mm": YELLOW_MM_NEEDLE_PATH,
            "fuel_mm": FUEL_MM_NEEDLE_PATH,
            "chrono_sec_mm": CHRONO_SECOND_MM_PATH,
            "fuel_chrono_sec_mm": CHRONO_SECOND_MM_PATH,
            "red_modern_1": RED_MODERN_1_PATH,
            "red_modern_2": RED_MODERN_2_PATH,
            "yellow_modern": YELLOW_MODERN_PATH,
            "cyan_future": CYAN_FUTURE_PATH,
            "yellow_future": YELLOW_FUTURE_PATH,
            "purple_future": PURPLE_FUTURE_PATH,
        }
        for ntype, npath in needle_paths.items():
            try:
                self._needle_images[ntype] = Image.open(str(npath)).convert("RGBA")
            except Exception:
                print(f"{ntype} needle image missing: {npath.name}")

        # Needle geometry lookup: hub (x,y) and tip distance per type
        self._needle_geometry = {
            "red": (RED_HUB, RED_TIP_DIST),
            "orange": (ORANGE_HUB, ORANGE_TIP_DIST),
            "dark_mm": (DARK_MM_HUB, DARK_MM_TIP_DIST),
            "yellow_mm": (YELLOW_MM_HUB, YELLOW_MM_TIP_DIST),
            "fuel_mm": (FUEL_MM_HUB, FUEL_MM_TIP_DIST),
            "chrono_sec_mm": (CHRONO_MM_SEC_HUB, CHRONO_MM_SEC_TIP_DIST),
            "fuel_chrono_sec_mm": (CHRONO_MM_SEC_HUB, CHRONO_MM_SEC_TIP_DIST),
            "red_modern_1": (RED_MODERN_1_HUB, RED_MODERN_1_TIP_DIST),
            "red_modern_2": (RED_MODERN_2_HUB, RED_MODERN_2_TIP_DIST),
            "yellow_modern": (YELLOW_MODERN_HUB, YELLOW_MODERN_TIP_DIST),
            "cyan_future": (CYAN_FUTURE_HUB, CYAN_FUTURE_TIP_DIST),
            "yellow_future": (YELLOW_FUTURE_HUB, YELLOW_FUTURE_TIP_DIST),
            "purple_future": (PURPLE_FUTURE_HUB, PURPLE_FUTURE_TIP_DIST),
        }

        # Load chronograph hand images — pick MM or standard based on skin
        chrono_style = self._skin.get("clock", {}).get("chrono_hands", "standard")
        if chrono_style == "mm":
            chrono_paths = [
                ("_chrono_second_base", CHRONO_SECOND_MM_PATH),
                ("_chrono_minute_base", CHRONO_MINUTE_MM_PATH),
                ("_chrono_hour_base", CHRONO_HOUR_MM_PATH),
            ]
            self._chrono_geometry = {
                "hour": (CHRONO_MM_HOUR_HUB, CHRONO_MM_HOUR_TIP_DIST),
                "minute": (CHRONO_MM_MIN_HUB, CHRONO_MM_MIN_TIP_DIST),
                "second": (CHRONO_MM_SEC_HUB, CHRONO_MM_SEC_TIP_DIST),
            }
        elif chrono_style == "future":
            chrono_paths = [
                ("_chrono_second_base", CHRONO_SEC_FUTURE_PATH),   # yellow
                ("_chrono_minute_base", CHRONO_MIN_FUTURE_PATH),   # cyan
                ("_chrono_hour_base", CHRONO_HOUR_FUTURE_PATH),    # cyan
            ]
            self._chrono_geometry = {
                "hour": (CYAN_FUTURE_HUB, CYAN_FUTURE_TIP_DIST),
                "minute": (CYAN_FUTURE_HUB, CYAN_FUTURE_TIP_DIST),
                "second": (YELLOW_FUTURE_HUB, YELLOW_FUTURE_TIP_DIST),
            }
        else:
            chrono_paths = [
                ("_chrono_second_base", CHRONO_SECOND_PATH),
                ("_chrono_minute_base", CHRONO_MINUTE_PATH),
                ("_chrono_hour_base", CHRONO_HOUR_PATH),
            ]
            self._chrono_geometry = {
                "hour": (CHRONO_HUB, CHRONO_TIP_DIST),
                "minute": (CHRONO_HUB, CHRONO_TIP_DIST),
                "second": (CHRONO_HUB, CHRONO_TIP_DIST),
            }
        self._chrono_second_base = self._chrono_minute_base = self._chrono_hour_base = None
        for attr, path in chrono_paths:
            try:
                setattr(self, attr, Image.open(str(path)).convert("RGBA"))
            except Exception:
                print(f"Chrono hand image missing: {path.name}")

        # Canvas
        self.canvas = tk.Canvas(self.root, bg="#000000", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        # Initial sizing — start compact (~600px wide), user can resize
        self.root.update_idletasks()
        self._cur_w = 600
        self._cur_h = int(600 / (self._native_w / self._native_h))
        scale = self._cur_w / self._native_w
        self._scale = scale
        self.root.geometry(f"{self._cur_w}x{self._cur_h}")

        # Background rendering
        self._bg_photo = None
        self._bg_canvas_id = None
        self._star_cover_id = None
        self._glass_canvas_id = None
        self._glass_photo = None
        self._render_background()
        
        # Persistent photo references to prevent GC
        self._needle_photos = []
        self._led_photo = None

        # ── Gauge state ───────────────────────────────────────────────
        # Collect gauge configs from skin (everything except clock, led, odometer, ttft, star_cover)
        self._gauge_configs = {}
        skip_keys = {"name", "image", "glass", "native_w", "native_h",
                      "clock", "led", "odometer", "ttft", "star_cover"}
        for key, val in self._skin.items():
            if key not in skip_keys and isinstance(val, dict) and "cx" in val and "start" in val:
                self._gauge_configs[key] = val

        # Per-gauge animation state
        self._gauge_state = {}
        for key in self._gauge_configs:
            self._gauge_state[key] = {
                "current": 0.0,
                "target": 0.0,
                "velocity": 0.0,
                "items": [],
            }

        # Session state
        self._last_mtime = 0
        self._last_size = 0
        self._last_filepath = None
        self._first_load = True
        self._last_chunk_time = time.time()
        self._last_event_count = 0
        self._total_output = 0
        self._ttft_ms = 0.0
        self._check_engine = False

        # Odometer state
        self._odo_displayed = 0.0
        self._odo_target = 0
        self._odo_photo = None
        self._drum_strip = None
        try:
            full_drum = Image.open(str(DRUM_STRIP_PATH)).convert("RGBA")
            # Crop to digit face (remove heavy metallic rails, keep thin edges)
            # Use full height to preserve exact digit spacing
            self._drum_strip = full_drum.crop((25, 0, 158, full_drum.height))
        except Exception:
            print("odometer_drum.png not found — odometer disabled")

        # Canvas item IDs for cleanup
        self._clock_items = []
        self._clock_photos = []
        self._led_canvas_id = None
        self._odo_canvas_id = None
        self._ttft_text_id = None

        # Bind resize
        self.canvas.bind("<Configure>", self._on_resize)

        # Start loops
        self._update_clock()
        self._update_gauges()
        self._poll()

        self.root.mainloop()

    # ── Scaling helper ────────────────────────────────────────────────
    def _s(self, v):
        """Scale a native-coordinate value to current window size (pixel-snapped)."""
        return round(v * self._scale)

    # ── Background ────────────────────────────────────────────────────
    def _render_background(self):
        """Render dashboard background. Glass overlay is a separate top layer."""
        bg = self._src_image.resize((self._cur_w, self._cur_h), Image.LANCZOS)

        self._bg_photo = ImageTk.PhotoImage(bg)

        if self._bg_canvas_id:
            self.canvas.delete(self._bg_canvas_id)
        self._bg_canvas_id = self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)
        self.canvas.tag_lower(self._bg_canvas_id)

        # Glass overlay as top layer — needles/odometer render between bg and glass
        if hasattr(self, '_glass_canvas_id') and self._glass_canvas_id:
            self.canvas.delete(self._glass_canvas_id)
            self._glass_canvas_id = None
        if self._glass_image:
            glass = self._glass_image.resize((self._cur_w, self._cur_h), Image.LANCZOS)
            self._glass_photo = ImageTk.PhotoImage(glass)
            self._glass_canvas_id = self.canvas.create_image(0, 0, anchor="nw", image=self._glass_photo)
            self.canvas.tag_raise(self._glass_canvas_id)

        # Cover the Nano Banana watermark
        star = self._skin.get("star_cover")
        if star:
            if self._star_cover_id:
                self.canvas.delete(self._star_cover_id)
            self._star_cover_id = self.canvas.create_rectangle(
                self._s(star[0]), self._s(star[1]),
                self._s(star[2]), self._s(star[3]),
                fill="#000000", outline="#000000"
            )

    # ── Resize ────────────────────────────────────────────────────────
    def _on_resize(self, e):
            if e.width < 200 or e.height < 100:
                return
            # Lock to native 1376:752 ratio so it never stretches
            ratio = self._native_w / self._native_h
            if e.width / e.height > ratio:
                self._cur_w = e.width
                self._cur_h = int(e.width / ratio)
            else:
                self._cur_h = e.height
                self._cur_w = int(e.height * ratio)
            self._scale = self._cur_w / self._native_w
            self.root.geometry(f"{self._cur_w}x{self._cur_h}")
            # Clear and redraw everything at the locked size
            for key, state in self._gauge_state.items():
                for item in state["items"]:
                    self.canvas.delete(item)
                state["items"].clear()
            for item in self._clock_items:
                self.canvas.delete(item)
            self._clock_items.clear()
            if self._led_canvas_id:
                self.canvas.delete(self._led_canvas_id)
                self._led_canvas_id = None
            if self._odo_canvas_id:
                self.canvas.delete(self._odo_canvas_id)
                self._odo_canvas_id = None
            if self._ttft_text_id:
                self.canvas.delete(self._ttft_text_id)
                self._ttft_text_id = None
            self._render_background()

    # ── Clock ─────────────────────────────────────────────────────────
    def _update_clock(self):
        for item in self._clock_items:
            self.canvas.delete(item)
        self._clock_items.clear()
        self._clock_photos = []

        clock_cfg = self._skin.get("clock")
        if not clock_cfg:
            self.root.after(CLOCK_UPDATE_MS, self._update_clock)
            return

        now = datetime.now()
        cx = self._s(clock_cfg["cx"])
        cy = self._s(clock_cfg["cy"])
        r = self._s(clock_cfg["r"])

        # Clock angles (math convention: 90° = 12 o'clock)
        sec_frac = now.second + now.microsecond / 1e6
        sec_angle = 90 - sec_frac * 6
        min_frac = now.minute + now.second / 60
        min_angle = 90 - min_frac * 6
        hour_frac = (now.hour % 12) + now.minute / 60
        hour_angle = 90 - hour_frac * 30

        # Hand images with per-hand geometry
        # Z-order: first drawn = bottom. Stack: seconds, minutes, hours on top.
        chrono_style = clock_cfg.get("chrono_hands", "standard")
        if chrono_style == "mm":
            hands = [
                (sec_angle,   self._chrono_minute_base, 0.70, self._chrono_geometry["minute"]),   # B: medium → second
                (min_angle,   self._chrono_second_base, 0.80, self._chrono_geometry["second"]),   # C: long → minute
                (hour_angle,  self._chrono_hour_base,   0.50, self._chrono_geometry["hour"]),     # A: stubby → hour
            ]
        else:
            hands = [
                (sec_angle,   self._chrono_second_base, 0.82, self._chrono_geometry["second"]),   # second (red/thin)
                (min_angle,   self._chrono_hour_base,   0.70, self._chrono_geometry["hour"]),     # minute (regular)
                (hour_angle,  self._chrono_minute_base, 0.55, self._chrono_geometry["minute"]),   # hour (top)
            ]

        for angle_deg, base_img, reach_pct, geom in hands:
            hub = geom[0]
            tip_dist = geom[1]
            if base_img is None:
                rad = math.radians(angle_deg)
                tip_r = r * reach_pct
                ex = cx + tip_r * math.cos(rad)
                ey = cy - tip_r * math.sin(rad)
                item = self.canvas.create_line(cx, cy, ex, ey, fill="#222222",
                                               width=max(1, int(self._s(2))), capstyle="round")
                self._clock_items.append(item)
                continue

            # Scale hand so tip reaches the desired fraction of gauge radius
            desired_tip = r * reach_pct
            nscale = desired_tip / tip_dist

            scaled = base_img.resize((int(1024 * nscale), int(1024 * nscale)), Image.LANCZOS)
            s_hub_x = hub[0] * nscale
            s_hub_y = hub[1] * nscale

            # Square canvas centered on hub for symmetric rotation
            max_r = int(math.sqrt(
                max(s_hub_x, scaled.width - s_hub_x) ** 2 +
                max(s_hub_y, scaled.height - s_hub_y) ** 2
            )) + 2
            canvas_size = max_r * 2
            hand_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            paste_x = max_r - int(s_hub_x)
            paste_y = max_r - int(s_hub_y)
            hand_canvas.paste(scaled, (paste_x, paste_y), scaled)

            rotation = angle_deg - 90
            rotated = hand_canvas.rotate(rotation, expand=False, resample=Image.BICUBIC)

            place_x = cx - max_r
            place_y = cy - max_r

            photo = ImageTk.PhotoImage(rotated)
            img_id = self.canvas.create_image(place_x, place_y, anchor="nw", image=photo)
            self._clock_items.append(img_id)
            self._clock_photos.append(photo)

        self.root.after(CLOCK_UPDATE_MS, self._update_clock)

    # ── Gauge Animation Loop ──────────────────────────────────────────
    def _update_gauges(self):
        # Clear old needle photos
        self._needle_photos.clear()

        # Phase offsets for per-gauge jitter (so they don't vibrate in sync)
        phase_offsets = {
            "speed": 0.0,
            "context": 1.57,
            "context_upper": 1.57,
            "latency": 1.57,
            "boost": 3.14,
            "fuel": 4.71,
        }
        jitter_scales = {
            "speed": 1.0,
            "context": 1.0,
            "context_upper": 0.8,
            "latency": 1.0,
            "boost": 0.5,
            "fuel": 0.6,
        }
        # Per-gauge damping overrides (higher = settles faster, no overshoot)
        damping_overrides = {
            "boost": 0.45,
        }

        t = time.time()

        for key, cfg in self._gauge_configs.items():
            state = self._gauge_state[key]

            # Spring-damper physics
            damping = damping_overrides.get(key, NEEDLE_DAMPING)
            force = (state["target"] - state["current"]) * NEEDLE_SPRING
            state["velocity"] = (state["velocity"] + force) * (1.0 - damping)
            state["current"] += state["velocity"]

            # Jitter when near target (the idle quiver)
            draw_value = state["current"]
            if abs(state["current"] - state["target"]) < 0.5:
                phase = phase_offsets.get(key, 0.0)
                amp_scale = jitter_scales.get(key, 1.0)
                draw_value += math.sin(t * JITTER_FREQ + phase) * JITTER_AMP * amp_scale

            # Draw needle
            self._draw_needle(
                state["items"],
                cfg["cx"], cfg["cy"], cfg["r"],
                draw_value, cfg["max"],
                cfg["start"], cfg["sweep"],
                cfg["needle"]
            )


        # ── TTFT readout ──────────────────────────────────────────────
        ttft_cfg = self._skin.get("ttft")
        if ttft_cfg:
            if self._ttft_text_id:
                self.canvas.delete(self._ttft_text_id)
            if self._ttft_ms > 0:
                if self._ttft_ms < ITL_NORM_MAX_MS:
                    ttft_color = "#22ff88"
                elif self._ttft_ms < ITL_WARNING_MAX_MS:
                    ttft_color = "#ffaa00"
                else:
                    ttft_color = "#ff4444"
                self._ttft_text_id = self.canvas.create_text(
                    self._s(ttft_cfg["cx"]), self._s(ttft_cfg["cy"]),
                    text=f"TTFT {self._ttft_ms:.0f}ms",
                    fill=ttft_color,
                    font=("Courier", max(10, int(self._s(16)))),
                    anchor="center"
                )

        # ── Check engine LED ──────────────────────────────────────────
        led_cfg = self._skin.get("led")
        if led_cfg:
            if self._led_canvas_id:
                self.canvas.delete(self._led_canvas_id)
                self._led_canvas_id = None

            led_img = self._light_on if self._check_engine else self._light_off
            if led_img:
                led_size = max(20, int(self._s(35)))
                resized_led = led_img.resize((led_size, led_size), Image.LANCZOS)
                self._led_photo = ImageTk.PhotoImage(resized_led)
                self._led_canvas_id = self.canvas.create_image(
                    self._s(led_cfg["cx"]), self._s(led_cfg["cy"]),
                    image=self._led_photo, anchor="center"
                )
            else:
                fill = "#ff0000" if self._check_engine else "#333333"
                r = max(8, int(self._s(12)))
                lx, ly = self._s(led_cfg["cx"]), self._s(led_cfg["cy"])
                self._led_canvas_id = self.canvas.create_oval(
                    lx - r, ly - r, lx + r, ly + r, fill=fill, outline=fill
                )

        # ── Odometer (rolling digit strips) ──────────────────────────
        self._render_odometer()

        # Keep glass overlay on top of everything
        if hasattr(self, '_glass_canvas_id') and self._glass_canvas_id:
            self.canvas.tag_raise(self._glass_canvas_id)

        self.root.after(GAUGE_UPDATE_MS, self._update_gauges)

    # ── Odometer Rendering ──────────────────────────────────────────
    def _render_odometer(self):
        """Render odometer — drum-roll style (vintage) or digital snap (modern)."""
        odo_cfg = self._skin.get("odometer")
        if not odo_cfg:
            return

        style = odo_cfg.get("style", "drum")

        if style == "digital":
            self._render_odometer_digital(odo_cfg)
            return

        if style == "glow":
            self._render_odometer_glow(odo_cfg)
            return

        if self._drum_strip is None:
            return

        # Animate displayed value toward target — ease-out snap-to
        if self._odo_displayed != self._odo_target:
            diff = self._odo_target - self._odo_displayed
            if abs(diff) < 3.0:
                self._odo_displayed = float(self._odo_target)  # snap clean
            else:
                self._odo_displayed += diff * 0.25
                # Round to integer to prevent fractional pixel jitter on stable digits
                self._odo_displayed = round(self._odo_displayed)

        num_digits = odo_cfg.get("digits", 12)
        win_w = odo_cfg["w"]
        win_h = odo_cfg["h"]
        digit_h_src = 75.2  # pixels per digit in source strip (752px / 10 digits)

        # Slot dimensions at native resolution
        gap_w = 3
        num_gaps = (num_digits - 1) // 3
        slot_w = (win_w - num_gaps * gap_w) // num_digits

        # Scale the drum strip: width→slot_w, height so each digit→win_h
        scale_y = win_h / digit_h_src
        scaled_h = int(self._drum_strip.height * scale_y)
        scaled_strip = self._drum_strip.resize((slot_w, scaled_h), Image.LANCZOS)

        # Tile vertically for 9→0 wrapping
        tiled = Image.new("RGBA", (slot_w, scaled_h + win_h * 2), (0, 0, 0, 0))
        tiled.paste(scaled_strip, (0, 0))
        tiled.paste(scaled_strip.crop((0, 0, slot_w, win_h * 2)), (0, scaled_h))

        # Compose odometer image
        odo_total_w = num_digits * slot_w + num_gaps * gap_w
        odo_img = Image.new("RGBA", (odo_total_w, win_h), (40, 35, 30, 255))

        x = 0
        for d_idx in range(num_digits):
            pos_from_right = num_digits - 1 - d_idx
            place_value = 10 ** pos_from_right
            if pos_from_right == 0:
                # Ones digit: smooth roll
                digit_float = (self._odo_displayed / place_value) % 10
            else:
                # Higher digits: snap to integer, only advance when lower digit crosses 9→0
                digit_float = float(int(self._odo_displayed) // place_value % 10)

            # y-offset into the scaled strip
            y_off = int(digit_float * win_h)

            # Crop a window-height slice from the tiled strip
            window = tiled.crop((0, y_off, slot_w, y_off + win_h))
            odo_img.paste(window, (x, 0), window)

            x += slot_w

            # Small gap between groups of 3
            if pos_from_right > 0 and pos_from_right % 3 == 0:
                x += gap_w

        # Scale to current display size
        disp_w = max(1, int(odo_total_w * self._scale))
        disp_h = max(1, int(win_h * self._scale))
        display = odo_img.resize((disp_w, disp_h), Image.LANCZOS)

        self._odo_photo = ImageTk.PhotoImage(display)
        if self._odo_canvas_id:
            self.canvas.delete(self._odo_canvas_id)
        self._odo_canvas_id = self.canvas.create_image(
            self._s(odo_cfg["cx"]), self._s(odo_cfg["cy"]),
            image=self._odo_photo, anchor="center"
        )

    def _render_odometer_digital(self, odo_cfg):
        """Digital odometer — instant snap, opaque image covers background."""
        self._odo_displayed = float(self._odo_target)
        num_digits = odo_cfg.get("digits", 12)
        val_str = str(int(self._odo_displayed)).zfill(num_digits)
        # Insert commas from right: groups of 3
        parts = []
        for i, ch in enumerate(val_str):
            parts.append(ch)
            pos_from_right = num_digits - 1 - i
            if pos_from_right > 0 and pos_from_right % 3 == 0:
                parts.append(",")
        display_str = "".join(parts)

        win_w = odo_cfg.get("w", 318)
        win_h = odo_cfg.get("h", 50)

        # Render white digital numbers on opaque black background
        from PIL import ImageDraw, ImageFont
        odo_img = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 255))
        draw = ImageDraw.Draw(odo_img)
        font_size = int(win_h * 0.65)
        try:
            font = ImageFont.truetype("Menlo", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("Courier", font_size)
            except Exception:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), display_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (win_w - tw) // 2
        ty = (win_h - th) // 2 - bbox[1]
        draw.text((tx, ty), display_str, fill=(255, 255, 255, 255), font=font)

        disp_w = max(1, int(win_w * self._scale))
        disp_h = max(1, int(win_h * self._scale))
        display = odo_img.resize((disp_w, disp_h), Image.LANCZOS)

        self._odo_photo = ImageTk.PhotoImage(display)
        if self._odo_canvas_id:
            self.canvas.delete(self._odo_canvas_id)
        self._odo_canvas_id = self.canvas.create_image(
            self._s(odo_cfg["cx"]), self._s(odo_cfg["cy"]),
            image=self._odo_photo, anchor="center"
        )

    def _render_odometer_glow(self, odo_cfg):
        """Glowing digital odometer — cyan neon numerals on transparent background."""
        self._odo_displayed = float(self._odo_target)
        num_digits = odo_cfg.get("digits", 12)
        val_str = str(int(self._odo_displayed)).zfill(num_digits)
        parts = []
        for i, ch in enumerate(val_str):
            parts.append(ch)
            pos_from_right = num_digits - 1 - i
            if pos_from_right > 0 and pos_from_right % 3 == 0:
                parts.append(",")
        display_str = "".join(parts)

        win_w = odo_cfg.get("w", 318)
        win_h = odo_cfg.get("h", 50)

        from PIL import ImageDraw, ImageFont, ImageFilter
        # Render at 2x for glow quality then downscale
        scale = 2
        img = Image.new("RGBA", (win_w * scale, win_h * scale), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        font_size = int(win_h * 0.65 * scale)
        try:
            font = ImageFont.truetype("Menlo", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("Courier", font_size)
            except Exception:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), display_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (win_w * scale - tw) // 2
        ty = (win_h * scale - th) // 2 - bbox[1]

        # Draw glow layer (blurred cyan)
        glow = Image.new("RGBA", (win_w * scale, win_h * scale), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.text((tx, ty), display_str, fill=(0, 220, 255, 120), font=font)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=6 * scale))

        # Draw sharp text on top
        draw.text((tx, ty), display_str, fill=(180, 255, 255, 255), font=font)

        # Composite glow under text
        result = Image.alpha_composite(glow, img)
        result = result.resize((win_w, win_h), Image.LANCZOS)

        disp_w = max(1, int(win_w * self._scale))
        disp_h = max(1, int(win_h * self._scale))
        display = result.resize((disp_w, disp_h), Image.LANCZOS)

        self._odo_photo = ImageTk.PhotoImage(display)
        if self._odo_canvas_id:
            self.canvas.delete(self._odo_canvas_id)
        self._odo_canvas_id = self.canvas.create_image(
            self._s(odo_cfg["cx"]), self._s(odo_cfg["cy"]),
            image=self._odo_photo, anchor="center"
        )

    # ── Needle Drawing ────────────────────────────────────────────────

    def _draw_needle(self, items, cx, cy, r, value, maxv, start, sweep, needle_type):
        """Draw a rotated needle image centered on the gauge hub.
        Centers the hub in a square canvas so rotation is always symmetric."""
        for item in items:
            self.canvas.delete(item)
        items.clear()

        pct = max(0.0, min(value / maxv, 1.0))
        angle_deg = start - pct * sweep

        base = self._needle_images.get(needle_type)
        geom = self._needle_geometry.get(needle_type)
        if not base or not geom:
            # Fallback: draw a simple line
            rad = math.radians(angle_deg)
            sr = self._s(r) * 0.88
            ex = self._s(cx) + sr * math.cos(rad)
            ey = self._s(cy) - sr * math.sin(rad)
            item = self.canvas.create_line(self._s(cx), self._s(cy), ex, ey,
                                           fill="#ff0000" if "red" in needle_type else "#ff8800",
                                           width=max(3, int(self._s(4))), capstyle="round")
            items.append(item)
            return
        hub_x, hub_y = geom[0]
        tip_dist = geom[1]

        # Scale needle so tip reaches the gauge edge
        multiplier = 0.70 if r > 100 else 0.93
        desired_tip = self._s(r) * multiplier
        nscale = desired_tip / tip_dist

        scaled = base.resize((int(1024 * nscale), int(1024 * nscale)), Image.LANCZOS)
        s_hub_x = hub_x * nscale
        s_hub_y = hub_y * nscale

        # Place hub at center of a square canvas — guarantees symmetric rotation
        max_r = int(math.sqrt(
            max(s_hub_x, scaled.width - s_hub_x) ** 2 +
            max(s_hub_y, scaled.height - s_hub_y) ** 2
        )) + 2
        canvas_size = max_r * 2
        needle_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = max_r - int(s_hub_x)
        paste_y = max_r - int(s_hub_y)
        needle_canvas.paste(scaled, (paste_x, paste_y))

        # Rotate around center — perfectly symmetric, no expand needed
        rotation = angle_deg - 90
        rotated = needle_canvas.rotate(rotation, expand=False, resample=Image.BICUBIC)

        # Hub is at canvas center; place so hub aligns with gauge center
        place_x = self._s(cx) - max_r
        place_y = self._s(cy) - max_r

        photo = ImageTk.PhotoImage(rotated)
        img_id = self.canvas.create_image(place_x, place_y, anchor="nw", image=photo)
        items.append(img_id)
        self._needle_photos.append(photo)
        
    # ── Data Polling ──────────────────────────────────────────────────
    def _poll(self):
        try:
            active = find_active_jsonl()
            if active:
                stat = active.stat()
                # Only re-parse if file changed
                if stat.st_mtime != self._last_mtime or stat.st_size != self._last_size:
                    self._last_mtime = stat.st_mtime
                    self._last_size = stat.st_size
                    data = parse_session(active)
                    self._update_from_data(data)
        except Exception as e:
            print(f"Poll error: {e}")
        self.root.after(POLL_INTERVAL_MS, self._poll)

    def _update_from_data(self, data):
        speed = data.get("speed", 0)
        context_pct = data.get("context_pct", 0)
        self._total_output = data.get("total_output", 0)
        self._ttft_ms = data.get("ttft_ms", 0)

        # Boost: cache efficiency — 0% cache hits → 0 (far left / -10 on face),
        # 50% → 10 (center / 0), 100% → 20 (far right / +10)
        cache_ratio = data.get("cache_hit_ratio", 0)
        boost = cache_ratio * 20

        # Fuel: inverse of context consumed
        fuel = 100 - context_pct

        # Latency: cache efficiency as 0-100 scale (same concept as boost)
        latency = cache_ratio * 100

        # Map data to gauge targets via data_key
        data_map = {
            "speed": speed,
            "context_pct": context_pct,
            "boost": boost,
            "fuel": fuel,
            "latency": latency,
        }

        for key, cfg in self._gauge_configs.items():
            data_key = cfg.get("data_key", key)
            if data_key in data_map:
                target = data_map[data_key]
                maxv = cfg["max"]
                self._gauge_state[key]["target"] = max(0, min(target, maxv))

        # Check engine: stalled or dead
        now = time.time()
        events = data.get("output_events", 0)
        stalled = events > 5 and (now - self._last_chunk_time > HEARTBEAT_TIMEOUT_SEC)
        self._check_engine = stalled or (speed < 1.0 and events > 10)

        if events > self._last_event_count:
            self._last_chunk_time = now
            self._last_event_count = events

        # Odometer target
        self._odo_target = self._total_output

        # On first load, snap needles and odometer to targets (no animation lag)
        if self._first_load:
            for key in self._gauge_state:
                self._gauge_state[key]["current"] = self._gauge_state[key]["target"]
            self._odo_displayed = float(self._odo_target)
            self._first_load = False


# ── Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    skin = choose_skin()
    TokenDashboard(skin)
