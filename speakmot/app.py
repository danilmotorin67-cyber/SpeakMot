import threading
import tkinter as tk
from tkinter import ttk

from .audio import list_input_devices
from .config import Config
from .engine import Engine

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = ["ru", "en", "auto"]


class App:
    def __init__(self):
        self.cfg = Config.load()
        self.engine = Engine(self.cfg, on_status=self._set_status, on_result=self._add_history)

        self.root = tk.Tk()
        self.root.title("SpeakMot — голос в текст")
        self.root.geometry("520x440")
        self.root.minsize(480, 400)
        self._build_ui()

        self.engine.install_hotkey()
        self.engine.preload_model()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._start_tray()

    # --- интерфейс ---

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Запуск…")
        ttk.Label(frm, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", **pad
        )

        settings = ttk.LabelFrame(frm, text="Настройки")
        settings.pack(fill="x", **pad)

        self.hotkey_var = tk.StringVar(value=self.cfg.hotkey)
        self._row(settings, "Горячая клавиша", ttk.Entry(settings, textvariable=self.hotkey_var))

        self.mode_var = tk.StringVar(value=self.cfg.hotkey_mode)
        self._row(
            settings,
            "Режим",
            ttk.Combobox(
                settings, textvariable=self.mode_var, values=["toggle", "hold"], state="readonly"
            ),
        )

        self.model_var = tk.StringVar(value=self.cfg.model_size)
        self._row(
            settings,
            "Модель",
            ttk.Combobox(
                settings, textvariable=self.model_var, values=MODEL_SIZES, state="readonly"
            ),
        )

        self.lang_var = tk.StringVar(value=self.cfg.language)
        self._row(
            settings,
            "Язык",
            ttk.Combobox(
                settings, textvariable=self.lang_var, values=LANGUAGES, state="readonly"
            ),
        )

        self.devices = list_input_devices()
        device_names = ["По умолчанию"] + [name for _, name in self.devices]
        current = "По умолчанию"
        for idx, name in self.devices:
            if idx == self.cfg.input_device:
                current = name
        self.device_var = tk.StringVar(value=current)
        self._row(
            settings,
            "Микрофон",
            ttk.Combobox(
                settings, textvariable=self.device_var, values=device_names, state="readonly"
            ),
        )

        self.paste_var = tk.BooleanVar(value=self.cfg.auto_paste)
        ttk.Checkbutton(
            settings, text="Вставлять текст автоматически (Ctrl+V)", variable=self.paste_var
        ).pack(anchor="w", padx=10, pady=2)

        self.sound_var = tk.BooleanVar(value=self.cfg.sound_feedback)
        ttk.Checkbutton(settings, text="Звуковой сигнал", variable=self.sound_var).pack(
            anchor="w", padx=10, pady=(2, 8)
        )

        buttons = ttk.Frame(frm)
        buttons.pack(fill="x", **pad)
        ttk.Button(buttons, text="Сохранить", command=self._apply_settings).pack(side="left")
        ttk.Button(buttons, text="Записать / остановить", command=self.engine.toggle).pack(
            side="left", padx=6
        )

        hist = ttk.LabelFrame(frm, text="Последние распознавания")
        hist.pack(fill="both", expand=True, **pad)
        self.history_box = tk.Listbox(hist)
        self.history_box.pack(fill="both", expand=True, padx=8, pady=8)
        for item in self.cfg.history:
            self.history_box.insert("end", item)

    def _row(self, parent, label: str, widget) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=10, pady=3)
        ttk.Label(row, text=label, width=18).pack(side="left")
        widget.pack(in_=row, side="left", fill="x", expand=True)

    # --- действия ---

    def _apply_settings(self) -> None:
        self.cfg.hotkey = self.hotkey_var.get().strip() or "ctrl+alt+space"
        self.cfg.hotkey_mode = self.mode_var.get()
        self.cfg.language = self.lang_var.get()
        model_changed = self.cfg.model_size != self.model_var.get()
        self.cfg.model_size = self.model_var.get()

        selected = self.device_var.get()
        self.cfg.input_device = next(
            (idx for idx, name in self.devices if name == selected), None
        )
        self.cfg.auto_paste = self.paste_var.get()
        self.cfg.sound_feedback = self.sound_var.get()
        self.cfg.save()

        self.engine.install_hotkey()
        if model_changed:
            self.engine.transcriber.unload()
            self.engine.preload_model()
        self._set_status(f"Настройки сохранены · {self.cfg.hotkey}")

    def _set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    def _add_history(self, text: str) -> None:
        self.root.after(0, lambda: self.history_box.insert(0, text))

    # --- трей ---

    def _start_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            self.tray = None
            return

        image = Image.new("RGB", (64, 64), "#1f2937")
        draw = ImageDraw.Draw(image)
        draw.ellipse((20, 12, 44, 40), fill="#38bdf8")
        draw.rectangle((30, 40, 34, 50), fill="#38bdf8")
        draw.rectangle((22, 50, 42, 54), fill="#38bdf8")

        menu = pystray.Menu(
            pystray.MenuItem("Открыть", lambda: self.root.after(0, self._show)),
            pystray.MenuItem("Запись", lambda: self.engine.toggle()),
            pystray.MenuItem("Выход", lambda: self.root.after(0, self._quit)),
        )
        self.tray = pystray.Icon("SpeakMot", image, "SpeakMot", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _hide_to_tray(self) -> None:
        if getattr(self, "tray", None):
            self.root.withdraw()
        else:
            self._quit()

    def _show(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def _quit(self) -> None:
        self.engine.remove_hotkey()
        if getattr(self, "tray", None):
            self.tray.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
