import subprocess
import os
import uuid
import json

OUTPUT_DIR = "outputs"

# Стили субтитров под каждый шаблон (как в Opus Clip)
SUBTITLE_STYLES = {
    "viral_hook": {
        # Большие белые слова, одно слово — одна строка, жёлтое выделение
        "fontname": "Arial Black",
        "fontsize": 22,
        "primary_color": "&H00FFFFFF",   # белый
        "outline_color": "&H00000000",   # чёрная обводка
        "back_color": "&H80000000",      # полупрозрачный фон
        "outline": 3,
        "shadow": 2,
        "margin_v": 120,
        "alignment": 2,  # снизу по центру
        "bold": 1,
    },
    "reels_shorts": {
        # Жёлтый текст снизу
        "fontname": "Arial",
        "fontsize": 20,
        "primary_color": "&H00FFFF00",   # жёлтый
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "outline": 2,
        "shadow": 1,
        "margin_v": 80,
        "alignment": 2,
        "bold": 1,
    },
    "cinema": {
        # Классические белые субтитры по центру снизу
        "fontname": "Georgia",
        "fontsize": 18,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H40000000",
        "outline": 2,
        "shadow": 1,
        "margin_v": 60,
        "alignment": 2,
        "bold": 0,
    },
    "clean": {
        "fontname": "Arial",
        "fontsize": 18,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "outline": 2,
        "shadow": 1,
        "margin_v": 60,
        "alignment": 2,
        "bold": 0,
    },
}


def check_whisper() -> bool:
    """Проверить что whisper установлен."""
    try:
        result = subprocess.run(["whisper", "--help"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def extract_audio(video_path: str) -> str | None:
    """Извлечь аудио из видео для Whisper."""
    audio_path = video_path.replace(".mp4", "_audio.wav")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-ar", "16000",   # 16kHz — оптимально для Whisper
        "-ac", "1",       # моно
        "-c:a", "pcm_s16le",
        "-y", audio_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"[Audio] Extract error: {e}")
        return None


def run_whisper(audio_path: str) -> str | None:
    """Запустить Whisper и получить .srt файл."""
    from config import WHISPER_MODEL
    output_dir = os.path.dirname(audio_path)
    base = os.path.splitext(audio_path)[0]

    cmd = [
        "whisper", audio_path,
        "--model", WHISPER_MODEL,
        "--output_format", "srt",
        "--output_dir", output_dir,
        "--task", "transcribe",
        "--word_timestamps", "True",
        "--max_line_width", "30",
        "--max_line_count", "2",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
        srt_path = base + ".srt"
        if os.path.exists(srt_path):
            return srt_path
    except subprocess.TimeoutExpired:
        print("[Whisper] Timeout!")
    except subprocess.CalledProcessError as e:
        print(f"[Whisper] Error: {e.stderr[-500:]}")
    except FileNotFoundError:
        print("[Whisper] Not installed! pip install openai-whisper")

    return None


def build_ass_style(template_key: str) -> str:
    """Построить ASS стиль для субтитров."""
    s = SUBTITLE_STYLES.get(template_key, SUBTITLE_STYLES["clean"])
    return (
        f"fontname={s['fontname']},"
        f"fontsize={s['fontsize']},"
        f"primary_color={s['primary_color']},"
        f"outline_color={s['outline_color']},"
        f"back_color={s['back_color']},"
        f"outline={s['outline']},"
        f"shadow={s['shadow']},"
        f"marginv={s['margin_v']},"
        f"alignment={s['alignment']},"
        f"bold={s['bold']}"
    )


def burn_subtitles(video_path: str, srt_path: str, template_key: str) -> str | None:
    """Вжечь субтитры в видео через ffmpeg."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}_subbed.mp4")

    style = build_ass_style(template_key)

    # Экранируем путь к srt для ffmpeg
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-y", output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Subtitles] Burn error:\n{result.stderr[-800:]}")
            return None
        return output_path
    except Exception as e:
        print(f"[Subtitles] Exception: {e}")
        return None


def generate_subtitles(video_path: str, template_key: str) -> str | None:
    """
    Полный pipeline субтитров:
    1. Извлечь аудио
    2. Запустить Whisper
    3. Вжечь субтитры
    4. Вернуть путь к готовому видео
    """
    print("[Subtitles] Starting pipeline...")

    # 1. Извлечь аудио
    audio_path = extract_audio(video_path)
    if not audio_path:
        print("[Subtitles] Audio extraction failed")
        return None

    try:
        # 2. Whisper → .srt
        srt_path = run_whisper(audio_path)
        if not srt_path:
            print("[Subtitles] Whisper failed — skipping subtitles")
            return None

        # 3. Вжечь субтитры
        output_path = burn_subtitles(video_path, srt_path, template_key)

        return output_path

    finally:
        # Чистим временные файлы
        for f in [audio_path]:
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        srt_path_local = locals().get("srt_path")
        if srt_path_local and os.path.exists(srt_path_local):
            try:
                os.remove(srt_path_local)
            except Exception:
                pass
