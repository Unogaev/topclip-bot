import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")   # @username или -100xxxxxxxxxx
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "outputs"
FONTS_DIR = "fonts"

# Whisper модель: tiny/base/small/medium (больше = точнее, но медленнее)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
