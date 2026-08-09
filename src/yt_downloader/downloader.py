from __future__ import annotations

from pathlib import Path
from shutil import which
import sys
from typing import Callable

# Root directory helper
ROOT = Path(__file__).resolve().parents[2]

class DownloaderError(RuntimeError):
    pass


M4A_AUDIO_FORMAT = "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio[acodec^=mp4a]/best[ext=mp4]"
ProgressHook = Callable[[dict], None]


def require_ytdlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise DownloaderError(
            "yt-dlp is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc
    return yt_dlp


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
    yt_dlp = require_ytdlp()
    ffmpeg_available = ensure_ffmpeg() is not None

    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
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


def download(
    url: str,
    media_type: str,
    quality: str,
    audio_format: str,
    output_dir: Path,
    progress_hook: ProgressHook | None = None,
) -> None:
    yt_dlp = require_ytdlp()
    options = build_options(media_type, quality, audio_format, output_dir, progress_hook)
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except Exception as exc:
        raise DownloaderError(str(exc)) from exc


def _progress(status: dict) -> None:
    if status.get("status") == "finished":
        print("Processing downloaded file...")


def has_ffmpeg() -> bool:
    return ensure_ffmpeg() is not None


def get_ffmpeg_location() -> Path | None:
    bundled = _bundled_ffmpeg_dir()
    if bundled is not None:
        return bundled
    if which("ffmpeg") is not None:
        return Path(which("ffmpeg")).parent
    return None


def _bundled_ffmpeg_dir() -> Path | None:
    file_dir = Path(__file__).resolve().parent
    base = Path(getattr(sys, "_MEIPASS", file_dir.parents[2]))
    cwd = Path.cwd()
    python_dir = Path(sys.executable).parent

    candidates = [
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
            import urllib.request
            import zipfile

            target_dir = ROOT / "vendor" / "ffmpeg" / "bin"
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "ffmpeg.zip"

            url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffmpeg-6.1-win-64.zip"
            urllib.request.urlretrieve(url, zip_path)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(target_dir)

            if zip_path.exists():
                zip_path.unlink()

            return get_ffmpeg_location()
        except Exception:
            return None
    return None
