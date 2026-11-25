"""Cross-platform local desktop launcher for Trilingual PDF Converter.

Windows and macOS: configurable global shortcut, long-press trigger, and a
small format picker. Files are processed locally and written beside the PDF.
"""
from __future__ import annotations

import json
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pynput import keyboard

from app import analyze_text, extract_pdf, make_docx, markdown_content

CONFIG_PATH = Path.home() / ".trilingual-pdf-converter.json"
FORMATS = {
    "Markdown (.md)": "md",
    "Word (.docx)": "docx",
    "JSON (.json)": "json",
    "纯文本 (.txt)": "txt",
    "全部格式 (.zip)": "zip",
}
APP_NAME = "コン"


class DesktopApp:
    def __init__(self, input_path: str | None = None) -> None:
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("470x560")
        self.root.minsize(430, 500)
        self.root.configure(bg="#fbfcfa")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.config = self.load_config()
        self.listener = None
        self.press_started = None
        self.press_key = self.config.get("long_press_key", "p")
        self.build_ui()
        self.start_hotkey_listener()
        if input_path:
            self.root.after(150, lambda: self.open_input_file(input_path))

    def load_config(self):
        try:
            return {"trigger": "<ctrl>+<alt>+p", "mode": "shortcut", "long_press_seconds": 0.8, **json.loads(CONFIG_PATH.read_text())}
        except (OSError, json.JSONDecodeError):
            return {"trigger": "<ctrl>+<alt>+p", "mode": "shortcut", "long_press_seconds": 0.8}

    def save_config(self):
        CONFIG_PATH.write_text(json.dumps(self.config, ensure_ascii=False, indent=2))

    def build_ui(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        brand = tk.Frame(self.root, bg="#fbfcfa")
        brand.pack(fill="x", padx=28, pady=(24, 4))
        icon = tk.Canvas(brand, width=58, height=58, bg="#9ad6b4", highlightthickness=0)
        icon.pack(side="left", padx=(0, 12))
        icon.create_rectangle(15, 9, 45, 49, fill="#f9fffb", outline="")
        icon.create_polygon(36, 9, 45, 18, 36, 18, fill="#bcebd0", outline="")
        icon.create_oval(21, 25, 26, 30, fill="#193129", outline="")
        icon.create_oval(34, 25, 39, 30, fill="#193129", outline="")
        icon.create_arc(25, 31, 35, 40, start=200, extent=140, style="arc", outline="#2f8064", width=2)
        titlebox = tk.Frame(brand, bg="#fbfcfa")
        titlebox.pack(side="left", anchor="w")
        tk.Label(titlebox, text=APP_NAME, font=("Arial", 20, "bold"), bg="#fbfcfa", fg="#1e2725").pack(anchor="w")
        tk.Label(titlebox, text="PDF", font=("Arial", 8), bg="#fbfcfa", fg="#71807a").pack(anchor="w")
        tk.Label(self.root, text="三語識別 · 構成を保って変換", font=("Arial", 11), bg="#fbfcfa", fg="#71807a").pack(anchor="w", padx=28, pady=(7, 0))
        card = tk.Frame(self.root, bg="#e5f3ec", padx=18, pady=16)
        card.pack(fill="x", padx=24, pady=22)
        self.mode = tk.StringVar(value=self.config.get("mode", "shortcut"))
        tk.Label(card, text="QUICK ACTION SETTINGS", bg="#e5f3ec", fg="#2c7560", font=("Arial", 9, "bold")).pack(anchor="w")
        tk.Label(card, text="触发方式", bg="#e5f3ec", fg="#1e2725", font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 0))
        for value, label in [("shortcut", "快捷键"), ("long_press", "长按快捷键")]:
            tk.Radiobutton(card, text=label, variable=self.mode, value=value, bg="#e5f3ec", activebackground="#e5f3ec", command=self.update_mode).pack(anchor="w")
        row = tk.Frame(card, bg="#e5f3ec")
        row.pack(fill="x", pady=(9, 0))
        tk.Label(row, text="快捷键（pynput 格式）", bg="#e5f3ec", fg="#71807a").pack(side="left")
        self.trigger = tk.Entry(row, width=18)
        self.trigger.insert(0, self.config.get("trigger", "<ctrl>+<alt>+p"))
        self.trigger.pack(side="right")
        tk.Label(card, text="快捷键默认 Ctrl/⌘ + Alt/Option + P；长按模式默认按住 p 约 0.8 秒", bg="#e5f3ec", fg="#71807a", font=("Arial", 9), wraplength=350).pack(anchor="w", pady=(8, 0))
        action = tk.Frame(self.root, bg="#fbfcfa")
        action.pack(fill="x", padx=24, pady=(3, 0))
        ttk.Button(action, text="保存设置", command=self.save_settings).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(action, text="选择 PDF 开始", command=self.save_and_choose).pack(side="left", expand=True, fill="x", padx=(5, 0))
        tk.Label(self.root, text="OUTPUT FORMAT", bg="#fbfcfa", fg="#71807a", font=("Arial", 9, "bold")).pack(anchor="w", padx=28, pady=(26, 6))
        self.format_label = tk.Label(self.root, text="全部格式（ZIP） · 保存到原 PDF 文件夹", bg="#fbfcfa", fg="#1e2725", font=("Arial", 10))
        self.format_label.pack(anchor="w", padx=28)
        ttk.Button(self.root, text="设置默认输出格式", command=self.choose_default_format).pack(anchor="w", padx=24, pady=(8, 0))
        self.status = tk.Label(self.root, text="按快捷键可从任意应用唤起", bg="#fbfcfa", fg="#71807a", wraplength=360)
        self.status.pack(pady=15)

    def update_mode(self):
        self.status.config(text="长按模式：按住快捷键约 0.8 秒后弹出选择面板" if self.mode.get() == "long_press" else "快捷键模式：按一次快捷键弹出选择面板")

    def save_and_choose(self):
        self.save_settings()
        self.choose_pdf()

    def save_settings(self):
        trigger = self.trigger.get().strip()
        self.press_key = trigger if self.mode.get() == "long_press" else self.press_key
        self.config.update({"trigger": trigger, "mode": self.mode.get(), "long_press_key": self.press_key})
        self.save_config()
        self.restart_listener()
        self.status.config(text="设置已保存。按快捷键或点击“选择 PDF 开始”。")

    def choose_default_format(self):
        selected = tk.StringVar(value=self.config.get("default_format", "zip"))
        popup = tk.Toplevel(self.root)
        popup.title("默认输出格式")
        popup.geometry("300x270")
        popup.configure(bg="#fbfcfa")
        popup.grab_set()
        tk.Label(popup, text="默认输出格式", bg="#fbfcfa", fg="#1e2725", font=("Arial", 14, "bold")).pack(pady=18)
        for label, value in FORMATS.items():
            tk.Radiobutton(popup, text=label, variable=selected, value=value, bg="#fbfcfa", activebackground="#fbfcfa").pack(anchor="w", padx=55)
        def commit():
            self.config["default_format"] = selected.get()
            self.save_config()
            self.format_label.config(text=f"{next(k for k,v in FORMATS.items() if v == selected.get())} · 保存到原 PDF 文件夹")
            popup.destroy()
        ttk.Button(popup, text="保存", command=commit).pack(pady=15)

    def start_hotkey_listener(self):
        if self.config.get("mode") == "long_press":
            self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.listener.start()
            return
        try:
            self.listener = keyboard.GlobalHotKeys({self.config["trigger"]: self.on_hotkey})
            self.listener.start()
        except (ValueError, RuntimeError) as exc:
            self.status.config(text=f"快捷键格式无法识别：{exc}")

    def restart_listener(self):
        if self.listener:
            self.listener.stop()
        self.start_hotkey_listener()

    def on_hotkey(self):
        self.root.after(0, self.choose_pdf)

    def on_key_press(self, key):
        try:
            pressed = key.char.lower() == self.press_key.lower()
        except AttributeError:
            pressed = str(key).lower().replace("key.", "") == self.press_key.lower()
        if pressed and self.press_started is None:
            self.press_started = time.monotonic()

    def on_key_release(self, key):
        try:
            released = key.char.lower() == self.press_key.lower()
        except AttributeError:
            released = str(key).lower().replace("key.", "") == self.press_key.lower()
        if released and self.press_started is not None:
            duration = time.monotonic() - self.press_started
            self.press_started = None
            if duration >= float(self.config.get("long_press_seconds", 0.8)):
                self.root.after(0, self.choose_pdf)

    def hide(self):
        self.root.withdraw()

    def choose_pdf(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(250, lambda: self.root.attributes("-topmost", False))
        path = filedialog.askopenfilename(title="选择 PDF 文件", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.show_format_picker(Path(path))

    def open_input_file(self, input_path: str):
        path = Path(input_path).expanduser()
        if path.is_file() and path.suffix.lower() == ".pdf":
            self.show_format_picker(path)
        else:
            messagebox.showerror(APP_NAME, "请选择 PDF 文件。")

    def show_format_picker(self, pdf_path: Path):
        popup = tk.Toplevel(self.root)
        popup.title("选择输出格式")
        popup.geometry("330x310")
        popup.configure(bg="#fbfcfa")
        popup.grab_set()
        tk.Label(popup, text=pdf_path.name, bg="#fbfcfa", fg="#1e2725", font=("Arial", 11, "bold"), wraplength=280).pack(pady=(20, 4))
        tk.Label(popup, text="选择要生成的格式", bg="#fbfcfa", fg="#71807a").pack(pady=(0, 10))
        default_value = self.config.get("default_format", "zip")
        selected = tk.StringVar(value=next((label for label, value in FORMATS.items() if value == default_value), "全部格式 (.zip)"))
        for label in FORMATS:
            tk.Radiobutton(popup, text=label, variable=selected, value=label, bg="#fbfcfa", activebackground="#fbfcfa").pack(anchor="w", padx=62)
        ttk.Button(popup, text="开始转换", command=lambda: self.convert(pdf_path, FORMATS[selected.get()], popup)).pack(pady=18)

    def convert(self, pdf_path: Path, fmt: str, popup):
        try:
            with pdf_path.open("rb") as source:
                class Upload:
                    def read(self_inner): return source.read()
                text, pages = extract_pdf(Upload())
            stats = analyze_text(text)
            stem = pdf_path.stem
            outputs = {
                f"{stem}.md": markdown_content(text, stats, stem).encode(),
                f"{stem}.json": json.dumps({"filename": pdf_path.name, "statistics": stats, "pages": pages, "text": text}, ensure_ascii=False, indent=2).encode(),
                f"{stem}.txt": text.encode(),
                f"{stem}.docx": make_docx(text, stats, stem).getvalue(),
            }
            if fmt == "zip":
                import zipfile
                target = pdf_path.with_name(f"{stem}-converted.zip")
                with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name, content in outputs.items(): archive.writestr(name, content)
            else:
                target = pdf_path.with_name(f"{stem}.{fmt}")
                target.write_bytes(outputs[f"{stem}.{fmt}"])
            popup.destroy()
            messagebox.showinfo("转换完成", f"已保存到：\n{target}")
        except Exception as exc:
            messagebox.showerror("转换失败", str(exc))

    def run(self):
        self.root.mainloop()
        if self.listener:
            self.listener.stop()


if __name__ == "__main__":
    DesktopApp(sys.argv[1] if len(sys.argv) > 1 else None).run()
