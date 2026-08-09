import sys
import json
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yt_downloader.downloader import download, fetch_video_info, DownloaderError

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Invalid arguments"}), flush=True)
        sys.exit(1)

    command = sys.argv[1]
    
    if command == "info":
        url = sys.argv[2]
        try:
            info = fetch_video_info(url)
            print(json.dumps(info), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
            sys.exit(1)
            
    elif command == "download":
        if len(sys.argv) < 7:
            print(json.dumps({"error": "Missing arguments for download"}), flush=True)
            sys.exit(1)
            
        url = sys.argv[2]
        media_type = sys.argv[3]
        quality = sys.argv[4]
        audio_format = sys.argv[5]
        output_dir = Path(sys.argv[6])
        
        def progress_hook(status: dict) -> None:
            state = status.get("status")
            if state == "downloading":
                downloaded = status.get("downloaded_bytes") or 0
                total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
                percent = (downloaded / total * 100) if total else None
                speed = status.get("_speed_str", "").strip()
                eta = status.get("_eta_str", "").strip()
                print(json.dumps({
                    "status": "downloading",
                    "percent": percent,
                    "speed": speed,
                    "eta": eta
                }), flush=True)
            elif state == "finished":
                print(json.dumps({
                    "status": "processing"
                }), flush=True)

        try:
            download(url, media_type, quality, audio_format, output_dir, progress_hook)
            print(json.dumps({"status": "done", "dest": str(output_dir)}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)
            sys.exit(1)

if __name__ == "__main__":
    main()
