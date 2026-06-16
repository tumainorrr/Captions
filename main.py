import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk, messagebox

import numpy as np
import sounddevice as sd
from googletrans import Translator
from vosk import KaldiRecognizer, Model

SAMPLE_RATE = 16000
CHANNELS = 1

class ZoomTranslateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Translator Program")
        self.root.geometry("900x560")
        self.root.resizable(True, True)
        self.root.attributes("-alpha", 1.0)
        self.root.configure(bg="#f4f6fb")

        available_fonts = set(tkfont.families())
        preferred_thai = ["Leelawadee UI", "Sarabun", "TH Sarabun New", "TH Sarabun", "Tahoma", "Arial"]
        chosen_font = next((f for f in preferred_thai if f in available_fonts), "TkDefaultFont")

        self.heading_font = (chosen_font, 16, "bold")
        self.text_font = (chosen_font, 15)
        self.note_font = (chosen_font, 13)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Card.TFrame", background="#f4f6fb")
        style.configure("Top.TFrame", background="#eef2fd")
        style.configure("TLabel", background="#f4f6fb", foreground="#1f2a44")
        style.configure("Header.TLabel", background="#f4f6fb", foreground="#1f2a44", font=self.heading_font)
        style.configure("Muted.TLabel", background="#f4f6fb", foreground="#5c6b89", font=self.note_font)
        style.configure("Status.TLabel", background="#eef2fd", foreground="#3b4d71")
        style.configure("Accent.TButton", background="#4c7aed", foreground="#ffffff", borderwidth=0, focusthickness=3, focuscolor="")
        style.map("Accent.TButton", background=[("active", "#5e8cf8"), ("disabled", "#7a94d5")])
        style.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff", foreground="#1f2a44")
        style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])
        style.configure("TCheckbutton", background="#eef2fd", foreground="#1f2a44")
        style.configure("Vertical.TScrollbar", background="#d7dbe7", troughcolor="#f4f6fb", arrowcolor="#4c7aed", bordercolor="#d7dbe7")

        self.queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.translation_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.translate_thread = None
        self.translator = Translator()
        self.device_list = self.get_input_devices()
        self.selected_device = None
        self.stream = None
        self.request_id = 0
        self.current_request_id = None
        self.last_partial_text = ""
        self.pending_items = {}
        self.entry_data = {}

        self.src_lang = "en"
        self.dst_lang = "th"
        app_path = self.get_app_path()
        self.model_paths = {
            "en": os.environ.get(
                "VOSK_MODEL_PATH_EN",
                os.environ.get("VOSK_MODEL_PATH", os.path.join(app_path, "model")),
            ),
            "th": os.environ.get(
                "VOSK_MODEL_PATH_TH",
                os.environ.get("VOSK_MODEL_PATH", os.path.join(app_path, "model-th", "model")),
            ),
        }
        self.model = None
        self.top_controls_visible = True

        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=12, style="Card.TFrame")
        frame.pack(fill="both", expand=True)

        self.menu_toggle_frame = ttk.Frame(frame, style="Top.TFrame")
        self.menu_toggle_frame.pack(fill="x", pady=(0, 6))
        self.toggle_menu_button = ttk.Button(
            self.menu_toggle_frame,
            text="Hide Toolbar",
            command=self.toggle_menu,
            style="Accent.TButton",
            width=12,
        )
        self.toggle_menu_button.pack(side="left")

        self.top = ttk.Frame(frame, style="Top.TFrame")
        self.top.pack(fill="x", pady=(0, 10), ipady=8)

        device_label = ttk.Label(self.top, text="Input Device:")
        device_label.pack(side="left", padx=(0, 4))

        device_names = [f"{info['index']}: {info['name']}" for info in self.device_list]
        if not device_names:
            device_names = ["No input device found"]

        self.device_menu = ttk.Combobox(self.top, values=device_names, state="readonly", width=42)
        if self.device_list:
            self.device_menu.current(0)
            self.selected_device = self.device_list[0]['index']
        self.device_menu.pack(side="left", padx=(0, 8))
        self.device_menu.bind('<<ComboboxSelected>>', self.on_device_selected)

        direction_label = ttk.Label(self.top, text="Mode:")
        direction_label.pack(side="left", padx=(6, 4))
        self.direction_menu = ttk.Combobox(
            self.top,
            values=["อังกฤษ -> ไทย", "ไทย -> อังกฤษ"],
            state="readonly",
            width=16,
        )
        self.direction_menu.current(0)
        self.direction_menu.pack(side="left", padx=(0, 8))
        self.direction_menu.bind('<<ComboboxSelected>>', self.on_direction_selected)

        self.start_button = ttk.Button(self.top, text="Start", command=self.start, style="Accent.TButton")
        self.start_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(self.top, text="Stop", command=self.stop, state="disabled", style="Accent.TButton")
        self.stop_button.pack(side="left", padx=(0, 8))

        self.fullscreen_button = ttk.Button(self.top, text="Fullscreen", command=self.toggle_fullscreen, style="Accent.TButton")
        self.fullscreen_button.pack(side="left", padx=(0, 8))

        self.topmost_var = tk.BooleanVar(value=False)
        self.topmost_check = ttk.Checkbutton(
            self.top,
            text="Always on Top",
            variable=self.topmost_var,
            command=self.set_topmost,
        )
        self.topmost_check.pack(side="left", padx=(0, 8))

        self.transparent_var = tk.BooleanVar(value=False)
        self.transparent_check = ttk.Checkbutton(
            self.top,
            text="Transparent",
            variable=self.transparent_var,
            command=self.set_transparent,
        )
        self.transparent_check.pack(side="left", padx=(0, 8))

        self.show_time_var = tk.BooleanVar(value=True)
        self.time_check = ttk.Checkbutton(
            self.top,
            text="Show Time",
            variable=self.show_time_var,
            command=self.toggle_timestamp_display,
        )
        self.time_check.pack(side="left", padx=(0, 8))

        self.save_button = ttk.Button(self.top, text="Save", command=self.save_results, style="Accent.TButton")
        self.save_button.pack(side="left", padx=(0, 8))

        self.clear_button = ttk.Button(self.top, text="Clear", command=self.clear_results, style="Accent.TButton")
        self.clear_button.pack(side="left", padx=(0, 8))

        self.status_label = ttk.Label(self.top, text="Status: Stopped", style="Status.TLabel")
        self.status_label.pack(side="left", padx=(12, 0))

        content_frame = ttk.Frame(frame, style="Card.TFrame")
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(content_frame, style="Card.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_frame.rowconfigure(1, weight=1)
        right_frame = ttk.Frame(content_frame, style="Card.TFrame")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_frame.rowconfigure(1, weight=1)

        self.source_label = ttk.Label(left_frame, text="English Text", font=self.heading_font)
        self.source_label.pack(anchor="w", pady=(0, 4))
        self.english_text = tk.Text(
            left_frame,
            wrap="word",
            height=22,
            state="disabled",
            font=self.text_font,
            bg="#ffffff",
            fg="#1f2a44",
            insertbackground="#1f2a44",
            selectbackground="#dbe6ff",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground="#d7dbe7",
            highlightcolor="#4c7aed",
            spacing1=4,
            spacing3=12,
        )
        english_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.english_text.yview, style="Vertical.TScrollbar")
        self.english_text.configure(yscrollcommand=english_scroll.set)
        self.english_text.pack(fill="both", expand=True, side="left")
        english_scroll.pack(fill="y", side="right")

        self.target_label = ttk.Label(right_frame, text="Thai Translation", font=self.heading_font)
        self.target_label.pack(anchor="w", pady=(0, 4))
        self.thai_text = tk.Text(
            right_frame,
            wrap="word",
            height=22,
            state="disabled",
            font=self.text_font,
            bg="#ffffff",
            fg="#1f2a44",
            insertbackground="#1f2a44",
            selectbackground="#dbe6ff",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground="#d7dbe7",
            highlightcolor="#4c7aed",
            spacing1=4,
            spacing3=12,
        )
        thai_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.thai_text.yview, style="Vertical.TScrollbar")
        self.thai_text.configure(yscrollcommand=thai_scroll.set)
        self.thai_text.pack(fill="both", expand=True, side="left")
        thai_scroll.pack(fill="y", side="right")

        note = ttk.Label(
            frame,
            text="หมายเหตุ: หากต้องการจับเสียง Zoom ให้ตั้งค่าอุปกรณ์เสียง Windows เป็น Stereo Mix หรือใช้งาน Virtual Audio Cable. เพื่อใช้โหมดไทย->อังกฤษต้องติดตั้งโมเดล Vosk ภาษาไทยแยกต่างหาก และตั้ง VOSK_MODEL_PATH_TH หรือ VOSK_MODEL_PATH ให้ถูกต้อง.",
            style="Muted.TLabel",
            wraplength=1020,
            justify="center",
        )
        note.pack(side="bottom", pady=(10, 0))

    def get_app_path(self):
        if getattr(sys, "frozen", False):
            return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.dirname(os.path.abspath(__file__))

    def start(self):
        if not self.device_list:
            messagebox.showerror("No Input Device", "ไม่พบอุปกรณ์รับเสียง input ให้ตรวจสอบการเชื่อมต่อหรือการติดตั้ง")
            return

        model_path = self.model_paths.get(self.src_lang)
        if not model_path or not os.path.isdir(model_path):
            messagebox.showerror(
                "Missing Model",
                f"ไม่พบโมเดล Vosk สำหรับภาษาต้นทาง {self.src_lang}. กรุณาตั้งค่า VOSK_MODEL_PATH_{self.src_lang.upper()} หรือ VOSK_MODEL_PATH ให้ชี้ไปยังโฟลเดอร์โมเดลที่ถูกต้อง."
            )
            return

        self.model = Model(model_path)
        self.running = True
        self.audio_queue = queue.Queue()
        self.translation_queue = queue.Queue()
        self.request_id = 0
        self.current_request_id = None
        self.last_partial_text = ""
        self.pending_items = {}
        self.entry_order = []
        self.current_audio_buffer = bytearray()

        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        direction_label = "อังกฤษ->ไทย" if self.src_lang == "en" else "ไทย->อังกฤษ"
        self.status_label.configure(text=f"Status: Listening ({direction_label})")

        self.stream = sd.RawInputStream(
            device=self.selected_device,
            samplerate=SAMPLE_RATE,
            blocksize=4000,
            dtype="int16",
            channels=CHANNELS,
            callback=self.audio_callback,
        )
        self.stream.start()

        self.thread = threading.Thread(target=self.transcription_loop, daemon=True)
        self.thread.start()
        self.translate_thread = threading.Thread(target=self.translation_loop, daemon=True)
        self.translate_thread.start()
        self.root.after(100, self.process_queue)

    def stop(self):
        self.running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="Status: Stopped")

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get()
            if item[0] == "new":
                _, request_id, english_text = item
                self.append_entry(request_id, english_text, "Translating...")
            elif item[0] == "partial":
                _, request_id, english_text = item
                if request_id in self.pending_items:
                    self.entry_data[request_id]["english"] = english_text
                    prefix = ""
                    if self.entry_data[request_id].get("timestamp") and self.show_time_var.get():
                        prefix = f"[{self.entry_data[request_id]['timestamp']}] "
                    self.update_entry_text(self.english_text, self.pending_items[request_id]["eng_tag"], prefix + english_text)
                else:
                    self.append_entry(request_id, english_text, "Translating...")
            elif item[0] == "final":
                _, request_id, english_text, timestamp = item
                self.entry_data.setdefault(request_id, {})
                self.entry_data[request_id]["english"] = english_text
                self.entry_data[request_id]["timestamp"] = timestamp
                if request_id in self.pending_items:
                    prefix = f"[{timestamp}] " if self.show_time_var.get() else ""
                    self.update_entry_text(self.english_text, self.pending_items[request_id]["eng_tag"], prefix + english_text)
                else:
                    self.append_entry(request_id, english_text, "Translating...", timestamp=timestamp)
            elif item[0] == "update":
                _, request_id, thai_text = item
                if request_id in self.pending_items:
                    self.entry_data[request_id]["thai"] = thai_text
                    self.update_entry_text(self.thai_text, self.pending_items[request_id]["thai_tag"], thai_text)
            elif item[0] == "error":
                _, error_message = item
                self.append_entry(self.request_id, error_message, "")
                self.request_id += 1

        if self.running:
            self.root.after(100, self.process_queue)

    def append_entry(self, request_id, english_text, thai_text="Translating...", timestamp=None):
        eng_tag = f"eng_{request_id}"
        thai_tag = f"thai_{request_id}"
        self.entry_data[request_id] = {
            "english": english_text,
            "thai": thai_text,
            "timestamp": timestamp,
        }
        prefix = f"[{timestamp}] " if timestamp and self.show_time_var.get() else ""

        self.english_text.configure(state="normal")
        self.thai_text.configure(state="normal")

        self.english_text.insert("end", prefix + english_text + "\n\n", eng_tag)
        self.thai_text.insert("end", thai_text + "\n\n", thai_tag)

        self.english_text.tag_config(eng_tag, lmargin1=4, lmargin2=4)
        self.thai_text.tag_config(thai_tag, lmargin1=4, lmargin2=4)

        self.english_text.configure(state="disabled")
        self.thai_text.configure(state="disabled")

        self.pending_items[request_id] = {"eng_tag": eng_tag, "thai_tag": thai_tag}
        self.entry_order.append(request_id)

        self.english_text.see("end")
        self.thai_text.see("end")

    def update_entry_text(self, widget, tag, new_text):
        widget.configure(state="normal")
        ranges = widget.tag_ranges(tag)
        if ranges:
            start, end = ranges
            widget.delete(start, end)
            widget.insert(start, new_text + "\n\n", tag)
        widget.configure(state="disabled")
        widget.see("end")

    def transcription_loop(self):
        while self.running or not self.audio_queue.empty():
            try:
                data = self.audio_queue.get(timeout=0.1)
                if self.current_request_id is not None:
                    self.current_audio_buffer.extend(data)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    english_text = result.get("text", "").strip()
                    if english_text:
                        if self.current_request_id is None:
                            request_id = self.request_id
                            self.request_id += 1
                            self.current_audio_buffer = bytearray(data)
                        else:
                            request_id = self.current_request_id
                        timestamp = time.strftime("%H:%M:%S", time.localtime())
                        self.queue.put(("final", request_id, english_text, timestamp))
                        self.translation_queue.put((request_id, english_text))
                        self.current_request_id = None
                        self.last_partial_text = ""
                        self.current_audio_buffer = bytearray()
                else:
                    partial = json.loads(self.recognizer.PartialResult()).get("partial", "").strip()
                    if partial and partial != self.last_partial_text:
                        if self.current_request_id is None:
                            request_id = self.request_id
                            self.request_id += 1
                            self.current_request_id = request_id
                            self.current_audio_buffer = bytearray(data)
                            self.queue.put(("new", request_id, partial))
                        else:
                            self.current_audio_buffer.extend(data)
                            self.queue.put(("partial", self.current_request_id, partial))
                        self.last_partial_text = partial
            except queue.Empty:
                continue
            except Exception as err:
                self.queue.put(("error", f"Error: {err}"))
                break

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print("Audio input status:", status)

        if not self.running:
            return

        self.audio_queue.put(bytes(indata))

    def translation_loop(self):
        while self.running or not self.translation_queue.empty():
            try:
                request_id, source_text = self.translation_queue.get(timeout=0.1)
                target_text = self.translate_text(source_text)
                self.queue.put(("update", request_id, target_text))
            except queue.Empty:
                continue
            except Exception as err:
                self.queue.put(("error", f"Translation error: {err}"))

    def translate_text(self, source_text):
        if not source_text:
            return ""

        src_label = "ไทย" if self.src_lang == "th" else "อังกฤษ"
        dst_label = "อังกฤษ" if self.dst_lang == "en" else "ไทย"
        self.status_label.configure(text=f"Status: Translating {src_label} -> {dst_label}...")

        try:
            result = self.translator.translate(source_text, src=self.src_lang, dest=self.dst_lang)
            translated = (result.text or "").strip()
            if self.dst_lang == "th":
                translated = self.normalize_thai_text(translated)
            return translated
        except Exception as err:
            # ถ้าแปลไม่ได้ ให้คืนข้อความเดิมหรือข้อความแจ้งเตือนแบบไม่หยุดโปรแกรม
            return f"Translation failed: {err}"

    def normalize_thai_text(self, text):
        # Remove extra spaces before Thai combining characters and tone marks.
        import re
        thai_combinations = (
            "\u0E31\u0E34-\u0E3A\u0E47-\u0E4E"
        )
        pattern = re.compile(r"\s+(?=[%s])" % thai_combinations)
        return pattern.sub("", text)

    def get_input_devices(self):
        devices = []
        try:
            for index, device in enumerate(sd.query_devices()):
                if device['max_input_channels'] > 0:
                    devices.append({'index': index, 'name': device['name']})
        except Exception:
            pass
        return devices

    def on_device_selected(self, event):
        selection = self.device_menu.get()
        if ": " in selection:
            index = int(selection.split(": ", 1)[0])
            self.selected_device = index

    def on_direction_selected(self, event):
        selection = self.direction_menu.get()
        if selection == "ไทย -> อังกฤษ":
            self.src_lang = "th"
            self.dst_lang = "en"
            self.source_label.configure(text="Thai Text")
            self.target_label.configure(text="English Translation")
        else:
            self.src_lang = "en"
            self.dst_lang = "th"
            self.source_label.configure(text="English Text")
            self.target_label.configure(text="Thai Translation")

    def toggle_fullscreen(self):
        self.fullscreen = not getattr(self, "fullscreen", False)
        self.root.attributes("-fullscreen", self.fullscreen)
        self.fullscreen_button.configure(text="Exit Fullscreen" if self.fullscreen else "Fullscreen")

    def set_topmost(self):
        topmost = self.topmost_var.get()
        self.root.attributes("-topmost", topmost)

    def set_transparent(self):
        transparent = self.transparent_var.get()
        alpha = 0.85 if transparent else 1.0
        self.root.attributes("-alpha", alpha)

    def toggle_menu(self):
        self.top_controls_visible = not self.top_controls_visible
        if self.top_controls_visible:
            self.top.pack(fill="x", pady=(0, 10), ipady=8)
            self.toggle_menu_button.configure(text="Hide Toolbar")
        else:
            self.top.pack_forget()
            self.toggle_menu_button.configure(text="Show Toolbar")

    def toggle_timestamp_display(self):
        self.refresh_english_display()

    def refresh_english_display(self):
        self.english_text.configure(state="normal")
        self.english_text.delete("1.0", "end")
        for request_id in self.entry_order:
            data = self.entry_data.get(request_id, {})
            english_text = data.get("english", "")
            timestamp = data.get("timestamp")
            prefix = f"[{timestamp}] " if timestamp and self.show_time_var.get() else ""
            tag = f"eng_{request_id}"
            self.english_text.insert("end", prefix + english_text + "\n\n", tag)
            self.english_text.tag_config(tag, lmargin1=4, lmargin2=4)
        self.english_text.configure(state="disabled")

    def save_results(self):
        if not self.entry_order:
            messagebox.showwarning("No Data", "ไม่มีข้อความบันทึกให้บันทึก")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save transcript and translation"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for request_id in self.entry_order:
                    english = self._get_text_by_tag(self.english_text, f"eng_{request_id}")
                    thai = self._get_text_by_tag(self.thai_text, f"thai_{request_id}")
                    f.write("English: " + english + "\n")
                    f.write("Thai: " + thai + "\n\n")
            self.status_label.configure(text=f"Status: Saved to {os.path.basename(file_path)}")
            messagebox.showinfo("Saved", f"บันทึกไฟล์เรียบร้อย: {file_path}")
        except Exception as err:
            messagebox.showerror("Error", f"ไม่สามารถบันทึกไฟล์ได้: {err}")

    def clear_results(self):
        self.english_text.configure(state="normal")
        self.thai_text.configure(state="normal")
        self.english_text.delete("1.0", "end")
        self.thai_text.delete("1.0", "end")
        self.english_text.configure(state="disabled")
        self.thai_text.configure(state="disabled")
        self.pending_items.clear()
        self.entry_order.clear()
        self.status_label.configure(text="Status: Cleared results")

    def _get_text_by_tag(self, widget, tag):
        ranges = widget.tag_ranges(tag)
        if not ranges:
            return ""
        return widget.get(ranges[0], ranges[1]).strip()


def main():
    root = tk.Tk()
    app = ZoomTranslateApp(root)
    root.bind("<F11>", lambda event: app.toggle_fullscreen())
    root.bind("<Escape>", lambda event: app.toggle_fullscreen() if getattr(app, "fullscreen", False) else None)
    root.mainloop()


if __name__ == "__main__":
    main()
