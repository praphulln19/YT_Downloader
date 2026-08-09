from __future__ import annotations

import os
from pathlib import Path
from shutil import which
import subprocess
import sys
from typing import Callable

# Root directory helper
ROOT = Path(__file__).resolve().parents[2]

class DownloaderError(RuntimeError):
    pass


M4A_AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio[acodec^=mp4a]/best[ext=mp4]"
ProgressHook = Callable[[dict], None]


def require_ytdlp():
    # Always try to upgrade yt-dlp first (silently) — YouTube changes formats
    # frequently and outdated yt-dlp versions return only 360p streams
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception:
        pass

    try:
        # Reload module in case it was just upgraded
        if "yt_dlp" in sys.modules:
            del sys.modules["yt_dlp"]
        import yt_dlp
        return yt_dlp
    except ImportError:
        # Fallback 1: Full pip install with dependencies
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", "yt-dlp", "requests", "certifi"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
            import yt_dlp
            return yt_dlp
        except Exception:
            pass

        # Fallback 2: Standalone yt-dlp.exe check / auto-download
        exe_loc = ensure_ytdlp_exe()
        if exe_loc is not None:
            return exe_loc

        raise DownloaderError(
            "yt-dlp could not be initialized automatically. Please run: pip install yt-dlp"
        )


def build_options(
    media_type: str,
    quality: str,
    audio_format: str,
    output_dir: Path,
    progress_hook: ProgressHook | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_location = ensure_ffmpeg()
    ffmpeg_available = ffmpeg_location is not None
    progress_hooks = [_progress]
    if progress_hook is not None:
        progress_hooks.append(progress_hook)

    options = {
        "outtmpl": str(output_dir / "%(title).180s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": False,
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": progress_hooks,
    }
    if ffmpeg_location is not None:
        ffmpeg_dir = str(ffmpeg_location.parent if ffmpeg_location.is_file() else ffmpeg_location)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
        options["ffmpeg_location"] = str(ffmpeg_location)

    if media_type == "audio":
        if audio_format in {"mp3", "opus"} and ffmpeg_available:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }
            ]
        else:
            options["format"] = M4A_AUDIO_FORMAT
        return options

    if not ffmpeg_available:
        if quality == "best":
            options["format"] = "best[ext=mp4]/best"
        elif quality == "small":
            options["format"] = "worst[ext=mp4]/worst"
        else:
            options["format"] = f"best[height<={quality}][ext=mp4]/best[height<={quality}]/best"
        return options

    if quality == "best":
        options["format"] = "bv*+ba/best"
    elif quality == "small":
        options["format"] = "worstvideo*+worstaudio/worst"
    else:
        options["format"] = f"bv*[height={quality}]+ba/bv*[height<={quality}]+ba/b[height<={quality}]/best"

    options["merge_output_format"] = "mp4"
    return options


def fetch_video_info(url: str) -> dict:
    ytdlp_obj = require_ytdlp()
    ffmpeg_available = ensure_ffmpeg() is not None

    if hasattr(ytdlp_obj, "YoutubeDL"):
        options = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        with ytdlp_obj.YoutubeDL(options) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:
                raise DownloaderError(str(exc)) from exc

            if info.get("_type") == "playlist":
                entries = info.get("entries", [])
                if not entries:
                    raise DownloaderError("The playlist is empty.")
                info = entries[0]
                if not info:
                    raise DownloaderError("Failed to extract details from the first playlist item.")

            formats = info.get("formats", [])
            heights = set()
            for f in formats:
                vcodec = f.get("vcodec")
                acodec = f.get("acodec")
                height = f.get("height")

                if vcodec != "none" and vcodec is not None and height:
                    if ffmpeg_available:
                        heights.add(height)
                    else:
                        if acodec != "none" and acodec is not None:
                            heights.add(height)

            sorted_heights = sorted(list(heights), reverse=True)
            return {
                "title": info.get("title", "Unknown Title"),
                "heights": sorted_heights,
            }
    else:
        import json
        cmd = [str(ytdlp_obj), "-J", "--no-playlist", url]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise DownloaderError(res.stderr.strip() or "Failed to extract video details")
        info = json.loads(res.stdout)
        formats = info.get("formats", [])
        heights = set()
        for f in formats:
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            height = f.get("height")
            if vcodec != "none" and vcodec is not None and height:
                if ffmpeg_available or (acodec != "none" and acodec is not None):
                    heights.add(height)
        sorted_heights = sorted(list(heights), reverse=True)
        return {
            "title": info.get("title", "Unknown Title"),
            "heights": sorted_heights,
        }


def download(
    url: str,
    media_type: str,
    quality: str,
    audio_format: str,
    output_dir: Path,
    progress_hook: ProgressHook | None = None,
) -> None:
    ytdlp_obj = require_ytdlp()
    options = build_options(media_type, quality, audio_format, output_dir, progress_hook)
    
    if hasattr(ytdlp_obj, "YoutubeDL"):
        try:
            with ytdlp_obj.YoutubeDL(options) as ydl:
                ydl.download([url])
        except Exception as exc:
            raise DownloaderError(str(exc)) from exc
    else:
        fmt = options.get("format", "best")
        cmd = [str(ytdlp_obj), "-f", fmt, "-o", str(output_dir / "%(title).180s [%(id)s].%(ext)s"), url]
        if "ffmpeg_location" in options:
            cmd.extend(["--ffmpeg-location", options["ffmpeg_location"]])
        res = subprocess.run(cmd)
        if res.returncode != 0:
            raise DownloaderError("Download process failed.")


def _progress(status: dict) -> None:
    if status.get("status") == "finished":
        print("Processing downloaded file...")


def has_ffmpeg() -> bool:
    return ensure_ffmpeg() is not None


def get_ffmpeg_location() -> Path | None:
    bundled = _bundled_ffmpeg_dir()
    if bundled is not None:
        exe_file = bundled / "ffmpeg.exe"
        if exe_file.exists():
            return exe_file
        return bundled
    if which("ffmpeg") is not None:
        return Path(which("ffmpeg"))
    return None


def _bundled_ffmpeg_dir() -> Path | None:
    file_dir = Path(__file__).resolve().parent
    base = Path(getattr(sys, "_MEIPASS", file_dir.parents[2]))
    cwd = Path.cwd()
    python_dir = Path(sys.executable).parent

    appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    user_appdata_ffmpeg = Path(appdata) / "YTDownloader" / "bin"

    candidates = [
        user_appdata_ffmpeg,
        base / "vendor" / "ffmpeg" / "bin",
        base / "vendor" / "ffmpeg",
        base / "ffmpeg" / "bin",
        base / "ffmpeg",
        base,
        cwd / "vendor" / "ffmpeg" / "bin",
        cwd / "vendor" / "ffmpeg",
        cwd / "ffmpeg",
        cwd,
        file_dir.parents[1] / "vendor" / "ffmpeg" / "bin",
        python_dir / "ffmpeg",
        python_dir / "Scripts",
    ]
    for candidate in candidates:
        if (candidate / "ffmpeg.exe").exists() or (candidate / "ffmpeg").exists():
            return candidate
    return None


def ensure_ffmpeg() -> Path | None:
    loc = get_ffmpeg_location()
    if loc is not None:
        return loc

    if sys.platform == "win32":
        try:
            import zipfile

            appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
            target_dir = Path(appdata) / "YTDownloader" / "bin"
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "ffmpeg.zip"

            url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffmpeg-6.1-win-64.zip"

            # Use curl.exe (built into Windows 10+) — handles SSL and redirects properly
            result = subprocess.run(
                ["curl.exe", "-L", "-o", str(zip_path), url],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0 or not zip_path.exists() or zip_path.stat().st_size < 1000:
                print(f"[YTD] FFmpeg download failed: curl exit {result.returncode}", file=sys.stderr, flush=True)
                if zip_path.exists():
                    zip_path.unlink()
                return None

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(target_dir)

            if zip_path.exists():
                zip_path.unlink()

            exe_path = target_dir / "ffmpeg.exe"
            if exe_path.exists():
                print(f"[YTD] FFmpeg installed to {exe_path}", file=sys.stderr, flush=True)
                return exe_path
            return get_ffmpeg_location()
        except Exception as exc:
            print(f"[YTD] FFmpeg auto-install error: {exc}", file=sys.stderr, flush=True)
            return None
    return None


def ensure_ytdlp_exe() -> Path | None:
    appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    target_dir = Path(appdata) / "YTDownloader" / "bin"
    exe_path = target_dir / "yt-dlp.exe"
    if exe_path.exists():
        return exe_path
        
    if sys.platform == "win32":
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            result = subprocess.run(
                ["curl.exe", "-L", "-o", str(exe_path), url],
                capture_output=True,
                timeout=120,
            )
            if result.returncode == 0 and exe_path.exists() and exe_path.stat().st_size > 1000:
                print(f"[YTD] yt-dlp installed to {exe_path}", file=sys.stderr, flush=True)
                return exe_path
            print(f"[YTD] yt-dlp download failed: curl exit {result.returncode}", file=sys.stderr, flush=True)
        except Exception as exc:
            print(f"[YTD] yt-dlp auto-install error: {exc}", file=sys.stderr, flush=True)
    return None

