#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CYBERPUNK MEDIA TO ASCII RENDERER v4.0
Install: pip install opencv-python Pillow numpy
"""

import os
import sys
import time
import threading
import queue
import json
import shutil
from pathlib import Path
from collections import deque
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import cv2
from PIL import Image, ImageSequence
if os.name == 'nt':
    import msvcrt
    import ctypes
    import subprocess

class WindowsConsoleConfigurator:
    @staticmethod
    def configure_full_utf8():
        if os.name != 'nt':
            return True
        try:
            os.system('chcp 65001 >nul 2>&1')
            for stream in [sys.stdin, sys.stdout, sys.stderr]:
                try:
                    stream.reconfigure(encoding='utf-8', errors='replace')
                except:
                    pass
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)
            kernel32.SetConsoleOutputCP(65001)
            stdout_handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode))
            mode.value |= 0x0004 | 0x0001 | 0x0002
            kernel32.SetConsoleMode(stdout_handle, mode)
            return True
        except:
            return False

    @staticmethod
    def clear_screen_ansi():
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

    @staticmethod
    def reset_console():
        sys.stdout.write('\033[0m')
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

class UnicodePathSanitizer:
    @staticmethod
    def sanitize_path(raw_input):
        if not raw_input:
            return None
        if isinstance(raw_input, bytes):
            try:
                raw_input = raw_input.decode('utf-8', errors='ignore')
            except:
                return None
        path_str = raw_input.strip()
        quote_pairs = [('"', '"'), ("'", "'"), ('"', "'"), ("'", '"')]
        for start_q, end_q in quote_pairs:
            if path_str.startswith(start_q) and path_str.endswith(end_q):
                path_str = path_str[1:-1]
                break
        if os.name == 'nt':
            path_str = path_str.rstrip('. ')
            path_str = path_str.replace('/', '\\')
        try:
            return Path(path_str)
        except:
            try:
                return Path(path_str.encode('utf-8').decode('utf-8'))
            except:
                return None

    @staticmethod
    def get_windows_short_path(path):
        if os.name != 'nt':
            return str(path)
        path_str = str(path)
        if all(ord(c) < 128 for c in path_str):
            return path_str
        try:
            result = subprocess.run(
                ['cmd', '/c', f'for %I in ("{path_str}") do @echo %~sI'],
                capture_output=True, text=True, encoding='utf-8',
                errors='ignore', timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        return path_str

    @staticmethod
    def validate_file_exists(path):
        try:
            return path.exists() and path.is_file()
        except:
            try:
                short_path = UnicodePathSanitizer.get_windows_short_path(path)
                return Path(short_path).exists()
            except:
                return False

class ASCIICharacterSets:
    STANDARD = " .,:;irsXA253hMHGS#9B&@"
    DETAILED = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    MINIMAL = " .:-=+*#%@"
    BLOCKS = " ░▒▓█"
    MATRIX = " 01"
    BOX_DRAWING = " ─│┌┐└┘├┤┬┴┼"

    @classmethod
    def get_character_sets(cls):
        return {
            'standard': cls.STANDARD,
            'detailed': cls.DETAILED,
            'minimal': cls.MINIMAL,
            'blocks': cls.BLOCKS,
            'matrix': cls.MATRIX,
            'box_drawing': cls.BOX_DRAWING,
        }

    @classmethod
    def get_set_names(cls):
        return list(cls.get_character_sets().keys())

class RenderModes:
    MONOCHROME = 'monochrome'
    TRUECOLOR = 'truecolor'
    MATRIX = 'matrix'
    GRAYSCALE = 'grayscale'

    @classmethod
    def get_all_modes(cls):
        return [cls.MONOCHROME, cls.TRUECOLOR, cls.MATRIX, cls.GRAYSCALE]

class ASCIIRenderingEngine:
    def __init__(self, char_set=None, render_mode=None):
        self.char_set = char_set or ASCIICharacterSets.STANDARD
        self.render_mode = render_mode or RenderModes.TRUECOLOR
        self.contrast = 1.0
        self.brightness = 0.0
        self._char_array = np.array(list(self.char_set))
        self._char_count = len(self.char_set)
        self._gray_to_char = np.linspace(0, self._char_count - 1, 256, dtype=np.uint8)
        self._matrix_colors = np.array([[0, 255, 70], [0, 200, 50], [0, 150, 30], [0, 100, 20]], dtype=np.uint8)

    def set_char_set(self, char_set):
        self.char_set = char_set
        self._char_array = np.array(list(char_set))
        self._char_count = len(char_set)
        self._gray_to_char = np.linspace(0, self._char_count - 1, 256, dtype=np.uint8)

    def set_render_mode(self, mode):
        if mode in RenderModes.get_all_modes():
            self.render_mode = mode

    def set_contrast(self, value):
        self.contrast = np.clip(value, 0.5, 2.0)

    def _apply_adjustments(self, gray_array):
        adjusted = gray_array.astype(np.float32)
        adjusted = adjusted * self.contrast + self.brightness
        return np.clip(adjusted, 0, 255).astype(np.uint8)

    def frame_to_ascii_monochrome(self, frame, width, height):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        gray_resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)
        gray_adjusted = self._apply_adjustments(gray_resized)
        char_indices = self._gray_to_char[gray_adjusted]
        char_matrix = self._char_array[char_indices]
        return '\n'.join(''.join(row) for row in char_matrix)

    def frame_to_ascii_truecolor(self, frame, width, height):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (width, height), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_RGB2GRAY)
        gray_adjusted = self._apply_adjustments(gray)
        char_indices = self._gray_to_char[gray_adjusted]
        lines = []
        for y in range(height):
            line_parts = []
            for x in range(width):
                r, g, b = frame_resized[y, x]
                char = self._char_array[char_indices[y, x]]
                line_parts.append(f'\033[38;2;{r};{g};{b}m{char}')
            line_parts.append('\033[0m')
            lines.append(''.join(line_parts))
        return '\n'.join(lines)

    def frame_to_ascii_matrix(self, frame, width, height):
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        gray_resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)
        gray_adjusted = self._apply_adjustments(gray_resized)
        char_indices = self._gray_to_char[gray_adjusted]
        lines = []
        for y in range(height):
            line_parts = []
            for x in range(width):
                char = self._char_array[char_indices[y, x]]
                intensity = gray_adjusted[y, x]
                if intensity > 200:
                    color = self._matrix_colors[0]
                elif intensity > 150:
                    color = self._matrix_colors[1]
                elif intensity > 100:
                    color = self._matrix_colors[2]
                else:
                    color = self._matrix_colors[3]
                line_parts.append(f'\033[38;2;{color[0]};{color[1]};{color[2]}m{char}')
            line_parts.append('\033[0m')
            lines.append(''.join(line_parts))
        return '\n'.join(lines)

    def render_frame(self, frame, width, height):
        if self.render_mode == RenderModes.TRUECOLOR:
            return self.frame_to_ascii_truecolor(frame, width, height)
        elif self.render_mode == RenderModes.MATRIX:
            return self.frame_to_ascii_matrix(frame, width, height)
        else:
            return self.frame_to_ascii_monochrome(frame, width, height)

class TerminalViewportManager:
    def __init__(self):
        self.width, self.height = self._get_terminal_size()
        self.char_aspect_ratio = 0.5
        self.last_check_time = 0
        self.check_interval = 0.3

    def _get_terminal_size(self):
        try:
            size = shutil.get_terminal_size()
            return max(size.columns - 2, 40), max(size.lines - 3, 20)
        except:
            return 80, 24

    def check_resize(self):
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval:
            self.last_check_time = current_time
            new_width, new_height = self._get_terminal_size()
            if new_width != self.width or new_height != self.height:
                self.width, self.height = new_width, new_height
                return True
        return False

    def get_target_dimensions(self, source_width, source_height):
        adjusted_source_height = source_height * self.char_aspect_ratio
        aspect_ratio = source_width / adjusted_source_height
        target_width = min(self.width, int(self.height * aspect_ratio))
        target_height = int(target_width / aspect_ratio)
        return max(target_width, 20), max(target_height, 10)

class AsynchronousInputHandler:
    def __init__(self):
        self.use_msvcrt = os.name == 'nt'
        self.special_keys = {b'H': 'up', b'P': 'down', b'M': 'right', b'K': 'left'}

    def get_key(self):
        if self.use_msvcrt:
            if msvcrt.kbhit():
                key_bytes = msvcrt.getch()
                if key_bytes == b'\xe0' or key_bytes == b'\x00':
                    key_bytes = msvcrt.getch()
                    return self.special_keys.get(key_bytes, None)
                elif key_bytes == b' ':
                    return 'space'
                elif key_bytes == b'\r':
                    return 'enter'
                elif key_bytes == b'\x1b':
                    return 'escape'
                else:
                    try:
                        return key_bytes.decode('utf-8').lower()
                    except:
                        try:
                            return chr(key_bytes[0]).lower()
                        except:
                            return None
        return None

    def flush_input_buffer(self):
        if self.use_msvcrt:
            while msvcrt.kbhit():
                msvcrt.getch()

class VideoProcessingEngine:
    def __init__(self, file_path, renderer):
        self.file_path = file_path
        self.renderer = renderer
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=100)
        self.running = False
        self.paused = False
        self.reverse = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30.0
        self.frame_width = 0
        self.frame_height = 0
        self.buffer_thread = None
        self.frame_counter_lock = threading.Lock()

    def open_video(self):
        video_path = UnicodePathSanitizer.get_windows_short_path(self.file_path)
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open: {self.file_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0 or self.fps > 120:
            self.fps = 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def start_buffer_thread(self):
        self.running = True
        self.buffer_thread = threading.Thread(target=self._buffer_frames_worker, daemon=True)
        self.buffer_thread.start()

    def _buffer_frames_worker(self):
        while self.running:
            if self.paused:
                time.sleep(0.01)
                continue
            if self.frame_queue.qsize() < 80:
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_counter_lock:
                        frame_number = self.current_frame
                        self.current_frame += 1
                    try:
                        self.frame_queue.put((frame_number, frame), timeout=0.1)
                    except queue.Full:
                        pass
                else:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    with self.frame_counter_lock:
                        self.current_frame = 0
            else:
                time.sleep(0.001)

    def get_next_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None, None

    def seek_to_frame(self, frame_number):
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        with self.frame_counter_lock:
            self.current_frame = frame_number
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

    def toggle_pause(self):
        self.paused = not self.paused

    def toggle_reverse(self):
        self.reverse = not self.reverse

    def close(self):
        self.running = False
        if self.buffer_thread and self.buffer_thread.is_alive():
            self.buffer_thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

class GIFProcessingEngine:
    def __init__(self, file_path, renderer):
        self.file_path = file_path
        self.renderer = renderer
        self.frames = []
        self.durations = []
        self.total_frames = 0
        self.paused = False
        self.reverse = False

    def load_gif(self):
        gif = Image.open(str(self.file_path))
        for frame in ImageSequence.Iterator(gif):
            self.frames.append(frame.copy())
            duration = frame.info.get('duration', 100) / 1000.0
            self.durations.append(duration)
        self.total_frames = len(self.frames)

    def get_frame(self, index):
        index = index % self.total_frames
        return self.frames[index], self.durations[index]

    def toggle_pause(self):
        self.paused = not self.paused

    def toggle_reverse(self):
        self.reverse = not self.reverse

class CyberHackerDashboard:
    @staticmethod
    def print_main_banner():
        print("\033[38;2;0;255;70m")
        print("CYBERPUNK MEDIA TO ASCII RENDERER v4.0 - READY")
        print("\033[0m")
        print("=" * 60)

    @staticmethod
    def display_render_menu():
        print("\nSELECT RENDERING ENGINE:")
        print("[1] True Color RGB  [2] Grayscale  [3] Monochrome  [4] Matrix Mode")
        print("\nSELECT CHARACTER SET:")
        print("[6] Standard  [7] Detailed  [8] Minimal  [9] Blocks  [10] Binary  [11] Box")
        print("\nPress Enter for defaults")
        print("SELECTION: ", end="")

    @staticmethod
    def display_status_bar(file_info, viewport_width):
        status = "PAUSED" if file_info.get('paused') else ("REVERSE" if file_info.get('reverse') else "PLAYING")
        hud = f" {status} | {file_info.get('file_name','')} | {file_info.get('frame_num',0)}/{file_info.get('total_frames',0)} | {file_info.get('current_fps',0):.1f}/{file_info.get('target_fps',0):.1f} FPS | {file_info.get('render_mode','')} | {file_info.get('resolution','')}"
        print(hud.ljust(viewport_width), end='')

    @staticmethod
    def display_controls_help():
        print("\n[Space]=Pause [C]=Color [M]=CharSet [R]=Reverse [+/-]=Contrast [Q]=Quit")

class HTMLExportEngine:
    @staticmethod
    def export_ascii_to_txt(ascii_art, output_path):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ascii_art)
            return True
        except:
            return False

    @staticmethod
    def export_ascii_to_html(ascii_frames, output_path, fps=30.0):
        try:
            html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{{background:#000;color:#00ff46;font-family:monospace;font-size:8px;line-height:1.0;margin:20px}}pre{{white-space:pre}}</style></head><body><pre id="d">{ascii_frames[0] if ascii_frames else ''}</pre><script>const f={json.dumps(ascii_frames)};let c=0;setInterval(()=>{{document.getElementById('d').textContent=f[c];c=(c+1)%f.length}},{1000.0/fps});</script></body></html>"""
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return True
        except:
            return False

class CyberpunkASCIIApplication:
    def __init__(self):
        self.renderer = ASCIIRenderingEngine()
        self.viewport = TerminalViewportManager()
        self.input_handler = AsynchronousInputHandler()
        self.char_sets = ASCIICharacterSets.get_character_sets()
        self.char_set_names = ASCIICharacterSets.get_set_names()
        self.current_char_set_index = 0
        self.render_modes = RenderModes.get_all_modes()
        self.current_render_mode_index = 0
        self.running = True
        self.paused = False
        self.reverse = False
        self.resolution_scale = 1.0
        self.fps_history = deque(maxlen=30)
        self.last_frame_time = time.time()

    def setup_terminal(self):
        WindowsConsoleConfigurator.configure_full_utf8()
        WindowsConsoleConfigurator.clear_screen_ansi()
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

    def cleanup_terminal(self):
        sys.stdout.write('\033[?25h')
        sys.stdout.write('\033[0m')
        WindowsConsoleConfigurator.clear_screen_ansi()
        WindowsConsoleConfigurator.reset_console()
        sys.stdout.flush()

    def get_user_selection(self):
        CyberHackerDashboard.display_render_menu()
        selection = input().strip()
        if selection == '1':
            self.renderer.set_render_mode(RenderModes.TRUECOLOR)
        elif selection == '2':
            self.renderer.set_render_mode(RenderModes.GRAYSCALE)
        elif selection == '3':
            self.renderer.set_render_mode(RenderModes.MONOCHROME)
        elif selection == '4':
            self.renderer.set_render_mode(RenderModes.MATRIX)
        elif selection == '6':
            self.current_char_set_index = 0
        elif selection == '7':
            self.current_char_set_index = 1
        elif selection == '8':
            self.current_char_set_index = 2
        elif selection == '9':
            self.current_char_set_index = 3
        elif selection == '10':
            self.current_char_set_index = 4
        elif selection == '11':
            self.current_char_set_index = 5
        self.renderer.set_char_set(self.char_sets[self.char_set_names[self.current_char_set_index]])

    def _calculate_fps(self):
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        if elapsed > 0:
            fps = 1.0 / elapsed
            self.fps_history.append(fps)
            self.last_frame_time = current_time
            if self.fps_history:
                return sum(self.fps_history) / len(self.fps_history)
        return 0.0

    def handle_keyboard_input(self, video_engine=None, gif_engine=None):
        key = self.input_handler.get_key()
        if key is None:
            return True
        if key == 'q' or key == 'escape':
            return False
        elif key == 'space':
            self.paused = not self.paused
            if video_engine:
                video_engine.toggle_pause()
            if gif_engine:
                gif_engine.toggle_pause()
        elif key == 'r':
            self.reverse = not self.reverse
            if video_engine:
                video_engine.toggle_reverse()
            if gif_engine:
                gif_engine.toggle_reverse()
        elif key == 'c':
            self.current_render_mode_index = (self.current_render_mode_index + 1) % len(self.render_modes)
            self.renderer.set_render_mode(self.render_modes[self.current_render_mode_index])
        elif key == 'm':
            self.current_char_set_index = (self.current_char_set_index + 1) % len(self.char_set_names)
            self.renderer.set_char_set(self.char_sets[self.char_set_names[self.current_char_set_index]])
        elif key == 'up':
            self.resolution_scale = min(2.0, self.resolution_scale + 0.1)
        elif key == 'down':
            self.resolution_scale = max(0.25, self.resolution_scale - 0.1)
        elif key == '+' or key == '=':
            self.renderer.set_contrast(self.renderer.contrast + 0.1)
        elif key == '-':
            self.renderer.set_contrast(self.renderer.contrast - 0.1)
        elif key == 'right':
            if video_engine:
                video_engine.seek_to_frame(video_engine.current_frame + int(5 * video_engine.fps))
        elif key == 'left':
            if video_engine:
                video_engine.seek_to_frame(max(0, video_engine.current_frame - int(5 * video_engine.fps)))
        return True

    def play_video(self, file_path):
        engine = VideoProcessingEngine(file_path, self.renderer)
        try:
            engine.open_video()
            WindowsConsoleConfigurator.clear_screen_ansi()
            print(f"Playing: {file_path.name}")
            print(f"Resolution: {engine.frame_width}x{engine.frame_height} | FPS: {engine.fps:.2f} | Frames: {engine.total_frames}")
            CyberHackerDashboard.display_controls_help()
            time.sleep(1)
            engine.start_buffer_thread()
            base_w, base_h = self.viewport.get_target_dimensions(engine.frame_width, engine.frame_height)
            while self.running:
                if self.viewport.check_resize():
                    base_w, base_h = self.viewport.get_target_dimensions(engine.frame_width, engine.frame_height)
                if not self.handle_keyboard_input(video_engine=engine):
                    break
                tw = int(base_w * self.resolution_scale)
                th = int(base_h * self.resolution_scale)
                fn, frame = engine.get_next_frame()
                if frame is not None and not self.paused:
                    art = self.renderer.render_frame(frame, tw, th)
                    sys.stdout.write('\033[H')
                    sys.stdout.write(art)
                    sys.stdout.write('\n')
                    info = {'file_name': file_path.name, 'frame_num': fn, 'total_frames': engine.total_frames,
                            'current_fps': self._calculate_fps(), 'target_fps': engine.fps,
                            'render_mode': self.renderer.render_mode, 'resolution': f"{tw}x{th}",
                            'paused': self.paused, 'reverse': self.reverse}
                    CyberHackerDashboard.display_status_bar(info, self.viewport.width)
                    sys.stdout.flush()
                elif self.paused:
                    time.sleep(0.05)
                else:
                    time.sleep(0.001)
        except KeyboardInterrupt:
            print("\nInterrupted")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            engine.close()

    def play_gif(self, file_path):
        engine = GIFProcessingEngine(file_path, self.renderer)
        try:
            engine.load_gif()
            WindowsConsoleConfigurator.clear_screen_ansi()
            print(f"Playing: {file_path.name} | Frames: {engine.total_frames}")
            CyberHackerDashboard.display_controls_help()
            time.sleep(1)
            base_w, base_h = self.viewport.get_target_dimensions(engine.frames[0].width, engine.frames[0].height)
            idx = 0
            while self.running:
                if self.viewport.check_resize():
                    base_w, base_h = self.viewport.get_target_dimensions(engine.frames[0].width, engine.frames[0].height)
                if not self.handle_keyboard_input(gif_engine=engine):
                    break
                tw = int(base_w * self.resolution_scale)
                th = int(base_h * self.resolution_scale)
                if not self.paused:
                    frame, dur = engine.get_frame(idx)
                    art = self.renderer.render_frame(np.array(frame), tw, th)
                    sys.stdout.write('\033[H')
                    sys.stdout.write(art)
                    sys.stdout.write('\n')
                    info = {'file_name': file_path.name, 'frame_num': idx, 'total_frames': engine.total_frames,
                            'current_fps': self._calculate_fps(), 'target_fps': 1.0/dur if dur > 0 else 10,
                            'render_mode': self.renderer.render_mode, 'resolution': f"{tw}x{th}",
                            'paused': self.paused, 'reverse': self.reverse}
                    CyberHackerDashboard.display_status_bar(info, self.viewport.width)
                    sys.stdout.flush()
                    idx = (idx - 1) % engine.total_frames if self.reverse else (idx + 1) % engine.total_frames
                    time.sleep(dur)
                else:
                    time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nInterrupted")
        except Exception as e:
            print(f"Error: {e}")

    def display_image(self, file_path):
        try:
            img = Image.open(str(file_path))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            tw, th = self.viewport.get_target_dimensions(img.width, img.height)
            art = self.renderer.render_frame(np.array(img), tw, th)
            WindowsConsoleConfigurator.clear_screen_ansi()
            print(f"Displaying: {file_path.name}")
            sys.stdout.write(art)
            sys.stdout.write('\n')
            sys.stdout.flush()
            print("\n[S]=Save TXT [H]=Save HTML [Enter]=Continue")
            c = input().strip().lower()
            if c == 's':
                out = file_path.parent / f"{file_path.stem}_ascii.txt"
                if HTMLExportEngine.export_ascii_to_txt(art, out):
                    print(f"Saved: {out}")
            elif c == 'h':
                out = file_path.parent / f"{file_path.stem}_ascii.html"
                if HTMLExportEngine.export_ascii_to_html([art], out):
                    print(f"Saved: {out}")
            input("Press Enter to continue...")
        except Exception as e:
            print(f"Error: {e}")

    def run(self):
        self.setup_terminal()
        CyberHackerDashboard.print_main_banner()
        while True:
            try:
                self.get_user_selection()
                WindowsConsoleConfigurator.clear_screen_ansi()
                print("\nDrag and drop file (or 'quit' to exit):")
                self.input_handler.flush_input_buffer()
                fp = input().strip()
                if fp.lower() in ['quit', 'exit', 'q']:
                    break
                path = UnicodePathSanitizer.sanitize_path(fp)
                if path is None:
                    print("Invalid path")
                    input("Press Enter...")
                    continue
                if not UnicodePathSanitizer.validate_file_exists(path):
                    print(f"Not found: {path}")
                    input("Press Enter...")
                    continue
                ext = path.suffix.lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
                    self.display_image(path)
                elif ext == '.gif':
                    self.play_gif(path)
                elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']:
                    self.play_video(path)
                else:
                    print(f"Unsupported: {ext}")
                    input("Press Enter...")
                    continue
                self.paused = False
                self.reverse = False
                self.resolution_scale = 1.0
                WindowsConsoleConfigurator.clear_screen_ansi()
                print("Done! Ready for next file.")
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Unexpected: {e}")
                input("Press Enter...")
                continue
        self.cleanup_terminal()
        print("\nGoodbye!")

if __name__ == "__main__":
    app = CyberpunkASCIIApplication()
    app.run()
    sys.exit(0)