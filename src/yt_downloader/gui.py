from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .downloader import DownloaderError, download, has_ffmpeg, fetch_video_info
from .paths import default_download_dir, resolve_output_dir


VIDEO_QUALITIES = {
    "Best available": "best",
    "1080p": "1080",
    "720p": "720",
    "480p": "480",
    "Smallest file": "small",
}

AUDIO_FORMATS = {
    "Original": "original",
    "MP3": "mp3",
    "M4A": "m4a",
    "Opus": "opus",
}


class DownloaderApp(tk.Tk):
    COLORS = {
        "background": "#faf8ff",
        "surface": "#ffffff",
        "surface_low": "#f2f3ff",
        "surface_mid": "#ecedfa",
        "surface_high": "#e6e7f4",
        "outline": "#c2c6d8",
        "outline_strong": "#727687",
        "primary": "#0050cb",
        "primary_hover": "#0054d6",
        "primary_soft": "#d0e1fb",
        "text": "#191b24",
        "muted": "#424656",
        "white": "#ffffff",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("YT Downloader")
        self.minsize(940, 620)
        self.geometry("1040x680")

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.fetched_url = ""
        self.fetched_qualities = {
            "Best available": "best",
            "Smallest file": "small"
        }

        self.url_var = tk.StringVar()
        self.video_title_var = tk.StringVar(value="")
        self.media_type_var = tk.StringVar(value="video")
        self.quality_var = tk.StringVar(value="Fetch info first")
        self.audio_format_var = tk.StringVar(value="Original")
        self.output_dir_var = tk.StringVar(value=str(default_download_dir()))
        self.status_var = tk.StringVar(value=self._initial_status())
        self.progress_var = tk.DoubleVar(value=0)

        self._configure_style()
        self._build_ui()
        self.after(120, self._poll_events)

    def _configure_style(self) -> None:
        colors = self.COLORS
        self.configure(bg=colors["background"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=colors["background"])
        style.configure("Top.TFrame", background=colors["surface"])
        style.configure("Sidebar.TFrame", background=colors["surface_low"])
        style.configure("Main.TFrame", background=colors["background"])
        style.configure("Card.TFrame", background=colors["surface"], relief="solid", borderwidth=1)
        style.configure("Footer.TFrame", background=colors["surface_mid"])
        style.configure("TLabel", background=colors["background"], foreground=colors["text"], font=("Inter", 10))
        style.configure("Card.TLabel", background=colors["surface"], foreground=colors["text"], font=("Inter", 10))
        style.configure("Muted.TLabel", background=colors["surface"], foreground=colors["muted"], font=("Inter", 9))
        style.configure("PageTitle.TLabel", background=colors["background"], foreground=colors["text"], font=("Inter Semibold", 22))
        style.configure("PageHint.TLabel", background=colors["background"], foreground=colors["muted"], font=("Inter", 10))
        style.configure("Brand.TLabel", background=colors["surface"], foreground=colors["primary"], font=("Inter Black", 18))
        style.configure("SideBrand.TLabel", background=colors["surface_low"], foreground=colors["primary"], font=("Inter Semibold", 14))
        style.configure("SideMuted.TLabel", background=colors["surface_low"], foreground=colors["muted"], font=("Inter", 9))
        style.configure("Footer.TLabel", background=colors["surface_mid"], foreground=colors["muted"], font=("Inter", 9))
        style.configure("TButton", font=("Inter Semibold", 10), padding=(12, 8))
        style.configure("TRadiobutton", background=colors["surface"], foreground=colors["text"], font=("Inter", 10))
        style.configure(
            "TCombobox",
            fieldbackground=colors["surface"],
            background=colors["surface"],
            foreground=colors["text"],
            arrowcolor=colors["primary"],
            bordercolor=colors["outline"],
            lightcolor=colors["outline"],
            darkcolor=colors["outline"],
            padding=(10, 6),
        )
        style.map("TCombobox", fieldbackground=[("readonly", colors["surface"])])
        style.configure(
            "Horizontal.TProgressbar",
            thickness=8,
            troughcolor=colors["surface_high"],
            background=colors["primary"],
            bordercolor=colors["surface_high"],
            lightcolor=colors["primary"],
            darkcolor=colors["primary"],
        )

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_body()
        self._build_footer()
        self._sync_controls()

    def _build_top_bar(self) -> None:
        colors = self.COLORS
        top = tk.Frame(self, bg=colors["surface"], height=64, highlightthickness=1, highlightbackground=colors["outline"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.columnconfigure(0, weight=1)

        tk.Label(
            top,
            text="YT_Downloader",
            bg=colors["surface"],
            fg=colors["primary"],
            font=("Inter", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24)
        self._icon_button(top, "Settings", self._show_settings).grid(row=0, column=1, padx=(0, 8), pady=14)
        self._icon_button(top, "Help", self._show_help).grid(row=0, column=2, padx=(0, 20), pady=14)

    def _build_body(self) -> None:
        colors = self.COLORS
        body = ttk.Frame(self, style="Main.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)

        main = ttk.Frame(body, style="Main.TFrame", padding=(32, 28, 32, 28))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)

        ttk.Label(main, text="New Download", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            main,
            text="Paste a YouTube link, choose the format, and save it locally.",
            style="PageHint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))

        url_card = self._card(main)
        url_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        url_card.columnconfigure(0, weight=1)
        url_card.columnconfigure(1, weight=0)
        ttk.Label(url_card, text="YouTube URL", style="Card.TLabel", font=("Inter", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        self.url_entry = tk.Entry(
            url_card,
            textvariable=self.url_var,
            font=("Inter", 10),
            bg=colors["surface"],
            fg=colors["text"],
            insertbackground=colors["primary"],
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground=colors["outline"],
            highlightcolor=colors["primary"],
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0), ipady=8)
        self.url_entry.bind("<Return>", lambda event: self._fetch_video_details())
        self.url_entry.focus()

        self.fetch_button = self._secondary_button(url_card, "Fetch Info", self._fetch_video_details)
        self.fetch_button.grid(row=1, column=1, sticky="e", pady=(8, 0), padx=(12, 0))

        self.video_title_label = ttk.Label(
            url_card,
            textvariable=self.video_title_var,
            style="Muted.TLabel",
            font=("Inter Italic", 10)
        )
        self.video_title_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        settings_grid = ttk.Frame(main, style="Main.TFrame")
        settings_grid.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        settings_grid.columnconfigure(0, weight=1)
        settings_grid.columnconfigure(1, weight=1)

        mode_card = self._card(settings_grid)
        mode_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        mode_card.columnconfigure(0, weight=1)
        ttk.Label(mode_card, text="Mode", style="Card.TLabel", font=("Inter", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        radio_row = tk.Frame(mode_card, bg=colors["surface"])
        radio_row.grid(row=1, column=0, sticky="w", pady=(12, 14))
        self._radio(radio_row, "Video", "video").pack(side=tk.LEFT, padx=(0, 22))
        self._radio(radio_row, "Audio", "audio").pack(side=tk.LEFT)
        tk.Frame(mode_card, bg=colors["outline"], height=1).grid(row=2, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(mode_card, text="Video quality", style="Card.TLabel", font=("Inter", 10, "bold")).grid(
            row=3, column=0, sticky="w"
        )
        self.quality_combo = ttk.Combobox(
            mode_card,
            textvariable=self.quality_var,
            values=["Fetch info first"],
            state="readonly",
            font=("Inter", 10),
        )
        self.quality_combo.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        audio_card = self._card(settings_grid)
        audio_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        audio_card.columnconfigure(0, weight=1)
        ttk.Label(audio_card, text="Audio format", style="Card.TLabel", font=("Inter", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            audio_card,
            text="Choose this when downloading audio only.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 42))
        self.audio_combo = ttk.Combobox(
            audio_card,
            textvariable=self.audio_format_var,
            values=list(AUDIO_FORMATS),
            state="readonly",
            font=("Inter", 10),
        )
        self.audio_combo.grid(row=2, column=0, sticky="ew")

        path_card = self._card(main)
        path_card.grid(row=4, column=0, sticky="ew", pady=(0, 18))
        path_card.columnconfigure(0, weight=1)
        ttk.Label(path_card, text="Save to", style="Card.TLabel", font=("Inter", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        self.path_entry = tk.Entry(
            path_card,
            textvariable=self.output_dir_var,
            font=("Inter", 10),
            bg=colors["surface"],
            fg=colors["text"],
            insertbackground=colors["primary"],
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground=colors["outline"],
            highlightcolor=colors["primary"],
        )
        self.path_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 10), ipady=8)
        self._secondary_button(path_card, "Browse", self._browse_output_dir).grid(row=1, column=1, sticky="e", pady=(8, 0))

        action_row = ttk.Frame(main, style="Main.TFrame")
        action_row.grid(row=5, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(action_row, variable=self.progress_var, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 18))
        self.download_button = self._primary_button(action_row, "Download", self._start_download)
        self.download_button.grid(row=0, column=1, sticky="e")

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        colors = self.COLORS
        sidebar = tk.Frame(
            parent,
            bg=colors["surface_low"],
            width=240,
            highlightthickness=1,
            highlightbackground=colors["outline"],
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text="YT_Downloader", style="SideBrand.TLabel").pack(anchor="w", padx=18, pady=(22, 2))
        ttk.Label(sidebar, text="Utility v1.0", style="SideMuted.TLabel").pack(anchor="w", padx=18, pady=(0, 18))
        self._nav_item(sidebar, "Downloads", active=True).pack(fill=tk.X, padx=12, pady=(0, 8))
        self._nav_item(sidebar, "Finished").pack(fill=tk.X, padx=12, pady=(0, 8))
        self._nav_item(sidebar, "Library").pack(fill=tk.X, padx=12, pady=(0, 8))
        tk.Frame(sidebar, bg=colors["surface_low"]).pack(fill=tk.BOTH, expand=True)
        self._nav_item(sidebar, "Settings").pack(fill=tk.X, padx=12, pady=(0, 16))

    def _build_footer(self) -> None:
        colors = self.COLORS
        footer = tk.Frame(self, bg=colors["surface_mid"], height=36, highlightthickness=1, highlightbackground=colors["outline"])
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Footer.TLabel").grid(row=0, column=0, sticky="w", padx=22)
        self._footer_button(footer, "Check for Updates", self._show_updates).grid(row=0, column=1, padx=(0, 18))
        self._footer_button(footer, "Logs", self._show_logs).grid(row=0, column=2, padx=(0, 22))

    def _card(self, parent: tk.Misc) -> ttk.Frame:
        return ttk.Frame(parent, style="Card.TFrame", padding=18)

    def _radio(self, parent: tk.Misc, text: str, value: str) -> tk.Radiobutton:
        colors = self.COLORS
        return tk.Radiobutton(
            parent,
            text=text,
            value=value,
            variable=self.media_type_var,
            command=self._sync_controls,
            bg=colors["surface"],
            fg=colors["text"],
            activebackground=colors["surface"],
            activeforeground=colors["primary"],
            selectcolor=colors["surface"],
            font=("Inter", 10),
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=0,
        )

    def _nav_item(self, parent: tk.Misc, text: str, active: bool = False) -> tk.Label:
        colors = self.COLORS
        bg = colors["primary_soft"] if active else colors["surface_low"]
        fg = colors["primary"] if active else colors["muted"]
        label = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            anchor="w",
            padx=14,
            pady=10,
            font=("Inter", 10, "bold" if active else "normal"),
            cursor="hand2",
        )
        label.bind("<Button-1>", lambda _event: self.status_var.set(f"{text} view is coming soon."))
        return label

    def _primary_button(self, parent: tk.Misc, text: str, command: object) -> tk.Button:
        colors = self.COLORS
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors["primary"],
            fg=colors["white"],
            activebackground=colors["primary_hover"],
            activeforeground=colors["white"],
            disabledforeground="#dbe4ff",
            relief=tk.FLAT,
            bd=0,
            padx=28,
            pady=11,
            font=("Inter", 10, "bold"),
            cursor="hand2",
        )

    def _secondary_button(self, parent: tk.Misc, text: str, command: object) -> tk.Button:
        colors = self.COLORS
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors["surface"],
            fg=colors["text"],
            activebackground=colors["surface_high"],
            activeforeground=colors["primary"],
            relief=tk.SOLID,
            bd=1,
            padx=18,
            pady=8,
            font=("Inter", 10, "bold"),
            cursor="hand2",
        )

    def _icon_button(self, parent: tk.Misc, text: str, command: object) -> tk.Button:
        colors = self.COLORS
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors["surface"],
            fg=colors["primary"],
            activebackground=colors["surface_high"],
            activeforeground=colors["primary"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
            font=("Inter", 9, "bold"),
            cursor="hand2",
        )

    def _footer_button(self, parent: tk.Misc, text: str, command: object) -> tk.Button:
        colors = self.COLORS
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors["surface_mid"],
            fg=colors["muted"],
            activebackground=colors["surface_high"],
            activeforeground=colors["primary"],
            relief=tk.FLAT,
            bd=0,
            font=("Inter", 9),
            cursor="hand2",
        )

    def _browse_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(default_download_dir()))
        if selected:
            self.output_dir_var.set(selected)

    def _show_settings(self) -> None:
        messagebox.showinfo("Settings", "Settings will be added in a future version.")

    def _show_help(self) -> None:
        messagebox.showinfo("Help", "Paste a YouTube URL, choose video or audio, pick a folder, then download.")

    def _show_updates(self) -> None:
        self.status_var.set("Update checks are not wired yet.")

    def _show_logs(self) -> None:
        self.status_var.set("Logs view is not wired yet.")

    def _sync_controls(self) -> None:
        is_audio = self.media_type_var.get() == "audio"
        self.quality_combo.configure(state="disabled" if is_audio else "readonly")
        self.audio_combo.configure(state="readonly" if is_audio else "disabled")

    def _start_download(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube URL first.")
            return

        if url != self.fetched_url:
            messagebox.showwarning(
                "Fetch Details First",
                "The URL has changed or video details haven't been fetched yet. "
                "Please click 'Fetch Info' first to load the available qualities for this video."
            )
            return

        try:
            output_dir = resolve_output_dir(self.output_dir_var.get())
        except OSError as exc:
            messagebox.showerror("Invalid folder", str(exc))
            return

        media_type = self.media_type_var.get()
        quality_display = self.quality_var.get()
        quality = self.fetched_qualities.get(quality_display, "best")
        audio_format = AUDIO_FORMATS[self.audio_format_var.get()]

        self.progress_var.set(0)
        self.status_var.set("Starting download...")
        self.download_button.configure(state="disabled")
        self.fetch_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        self.worker = threading.Thread(
            target=self._download_worker,
            args=(url, media_type, quality, audio_format, output_dir),
            daemon=True,
        )
        self.worker.start()

    def _download_worker(
        self,
        url: str,
        media_type: str,
        quality: str,
        audio_format: str,
        output_dir: Path,
    ) -> None:
        try:
            download(url, media_type, quality, audio_format, output_dir, self._progress_hook)
        except DownloaderError as exc:
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("done", output_dir))

    def _progress_hook(self, status: dict) -> None:
        state = status.get("status")
        if state == "downloading":
            downloaded = status.get("downloaded_bytes") or 0
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            percent = (downloaded / total * 100) if total else None
            speed = status.get("_speed_str", "").strip()
            eta = status.get("_eta_str", "").strip()
            if percent is None:
                message = "Downloading..."
            else:
                message = f"Downloading... {percent:.1f}%"
            if speed:
                message += f" at {speed}"
            if eta:
                message += f", ETA {eta}"
            self.events.put(("progress", (percent, message)))
        elif state == "finished":
            self.events.put(("processing", "Processing downloaded file..."))

    def _fetch_video_details(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube URL first.")
            return

        self.status_var.set("Fetching video details...")
        self.download_button.configure(state="disabled")
        self.fetch_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.progress_var.set(0)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        self.video_title_var.set("Loading video details...")
        self.quality_combo.configure(values=["Fetching..."])
        self.quality_var.set("Fetching...")

        self.worker = threading.Thread(
            target=self._fetch_worker,
            args=(url,),
            daemon=True,
        )
        self.worker.start()

    def _fetch_worker(self, url: str) -> None:
        try:
            info = fetch_video_info(url)
            self.events.put(("fetch_done", (url, info)))
        except Exception as exc:
            self.events.put(("fetch_error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    percent, message = payload
                    self.status_var.set(str(message))
                    if percent is None:
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(12)
                    else:
                        self.progress.stop()
                        self.progress.configure(mode="determinate")
                        self.progress_var.set(float(percent))
                elif kind == "processing":
                    self.progress.stop()
                    self.progress.configure(mode="indeterminate")
                    self.progress.start(12)
                    self.status_var.set(str(payload))
                elif kind == "done":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(100)
                    self.status_var.set(f"Downloaded to {payload}")
                    self.download_button.configure(state="normal")
                    self.fetch_button.configure(state="normal")
                    self.url_entry.configure(state="normal")
                    messagebox.showinfo("Download complete", f"File saved to:\n{payload}")
                elif kind == "error":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.download_button.configure(state="normal")
                    self.fetch_button.configure(state="normal")
                    self.url_entry.configure(state="normal")
                    self.status_var.set("Download failed.")
                    messagebox.showerror("Download failed", str(payload))
                elif kind == "fetch_done":
                    url, info = payload
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(100)

                    self.fetched_url = url
                    title = info.get("title", "Unknown Title")
                    heights = info.get("heights", [])

                    self.video_title_var.set(title)

                    self.fetched_qualities = {}
                    if heights:
                        combo_values = []
                        for h in heights:
                            display_str = f"{h}p"
                            self.fetched_qualities[display_str] = str(h)
                            combo_values.append(display_str)

                        self.fetched_qualities["Best available"] = "best"
                        self.fetched_qualities["Smallest file"] = "small"
                        combo_values.insert(0, "Best available")
                        combo_values.append("Smallest file")

                        self.quality_combo.configure(values=combo_values)
                        self.quality_var.set(combo_values[0])
                    else:
                        self.fetched_qualities = {
                            "Best available": "best",
                            "Smallest file": "small"
                        }
                        self.quality_combo.configure(values=["Best available", "Smallest file"])
                        self.quality_var.set("Best available")

                    self.status_var.set("Loaded video details successfully.")
                    self.download_button.configure(state="normal")
                    self.fetch_button.configure(state="normal")
                    self.url_entry.configure(state="normal")
                elif kind == "fetch_error":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress_var.set(0)

                    self.video_title_var.set("")
                    self.quality_combo.configure(values=["Fetch info first"])
                    self.quality_var.set("Fetch info first")

                    self.download_button.configure(state="normal")
                    self.fetch_button.configure(state="normal")
                    self.url_entry.configure(state="normal")
                    self.status_var.set("Failed to load video details.")
                    messagebox.showerror("Error", f"Failed to fetch video details:\n{payload}")
        except queue.Empty:
            pass
        self.after(120, self._poll_events)

    def _initial_status(self) -> str:
        if has_ffmpeg():
            return "Ready. FFmpeg found for merging and audio conversion."
        return "Ready. FFmpeg not found; MP3, Opus, and merged video need bundled FFmpeg."


def main() -> None:
    app = DownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
