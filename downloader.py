import yt_dlp
import os
import uuid
import re

DOWNLOAD_DIR = "downloads"

SUPPORTED_PATTERNS = [
    (r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts)", "YouTube"),
    (r"instagram\.com/(p|reel|tv|stories)/", "Instagram"),
    (r"(tiktok\.com/|vm\.tiktok\.com/)", "TikTok"),
]


def is_supported_url(url: str) -> bool:
    return any(re.search(p, url) for p, _ in SUPPORTED_PATTERNS)


def detect_platform(url: str) -> str:
    for pattern, name in SUPPORTED_PATTERNS:
        if re.search(pattern, url):
            return name
    return "Видео"


def download_video(url: str) -> str | None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    filename = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, filename + ".%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
        # Обходы блокировок
        "extractor_args": {
            "youtube": {"skip": ["dash", "hls"]},
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Найти скачанный файл
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(filename) and f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)

        # Если mp4 не нашли, ищем любой файл с этим именем
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(filename):
                return os.path.join(DOWNLOAD_DIR, f)

    except yt_dlp.utils.DownloadError as e:
        print(f"[Downloader] DownloadError: {e}")
    except Exception as e:
        print(f"[Downloader] Error: {e}")

    return None
