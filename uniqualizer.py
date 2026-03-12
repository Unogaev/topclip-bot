import subprocess
import os
import uuid
import random
import json

OUTPUT_DIR = "outputs"

# ══════════════════════════════════════════════════════
#  ШАБЛОНЫ (как в Opus Clip)
#  viral_score — рейтинг виральности
#  hook_text   — текст Auto Hook (первые 5 сек)
# ══════════════════════════════════════════════════════
TEMPLATES = {
    "viral_hook": {
        "name": "🔥 Viral Hook",
        "viral_score": 99,
        "hook_example": "Ты должен это увидеть...",
        "hook_texts": [
            "Ты должен это увидеть...",
            "Никто не ожидал этого 👀",
            "Это изменит всё!",
            "Смотри до конца 🔥",
            "ТОП секрет раскрыт!",
        ],
        # Вертикальный 9:16, zoom, насыщенность
        "vf": (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=saturation=1.4:contrast=1.15:brightness=0.03,"
            "zoompan=z='if(lte(mod(on\\,90),45),zoom+0.002,zoom-0.002)':d=1:s=1080x1920"
        ),
        "speed_range": (0.97, 1.0),
        "add_hook": True,
        "hook_style": "viral",  # белый текст, чёрная тень, сверху
    },
    "reels_shorts": {
        "name": "📱 Reels / Shorts",
        "viral_score": 95,
        "hook_example": "Сохрани это видео!",
        "hook_texts": [
            "Сохрани это видео!",
            "Подпишись чтобы не пропустить",
            "Лайк если согласен 👍",
            "Поделись с другом!",
        ],
        # Вертикальный формат, яркий
        "vf": (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=saturation=1.3:brightness=0.05"
        ),
        "speed_range": (1.0, 1.05),  # слегка ускорить — типично для Reels
        "add_hook": True,
        "hook_style": "reels",  # текст снизу, жёлтый
    },
    "cinema": {
        "name": "🎬 Cinema Style",
        "viral_score": 88,
        "hook_example": "История, которую скрывали...",
        "hook_texts": [
            "История, которую скрывали...",
            "Правда о...",
            "Это изменило мой взгляд на мир",
        ],
        # Широкий формат 21:9 (letterbox), тёмный
        "vf": (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,"
            "drawbox=x=0:y=0:w=iw:h=ih*0.12:color=black@1:t=fill,"
            "drawbox=x=0:y=ih*0.88:w=iw:h=ih*0.12:color=black@1:t=fill,"
            "eq=gamma=0.88:saturation=0.75:contrast=1.1"
        ),
        "speed_range": (0.95, 0.98),  # замедлить = кинематографично
        "add_hook": True,
        "hook_style": "cinema",  # белый, по центру, serif
    },
    "clean": {
        "name": "✨ Clean Unique",
        "viral_score": 78,
        "hook_example": "",
        "hook_texts": [],
        # Минимальные изменения, просто уникализация
        "vf": (
            "hue=h=2,"
            "eq=brightness=0.02:saturation=1.05"
        ),
        "speed_range": (0.98, 1.02),
        "add_hook": False,
        "hook_style": None,
    },
}


def get_video_info(input_path: str) -> dict:
    """Получить информацию о видео через ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        input_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"),
            {}
        )
        return {
            "width": int(video_stream.get("width", 1920)),
            "height": int(video_stream.get("height", 1080)),
            "duration": float(data.get("format", {}).get("duration", 60)),
        }
    except Exception as e:
        print(f"[ffprobe] Error: {e}")
        return {"width": 1920, "height": 1080, "duration": 60}


def build_hook_filter(hook_text: str, style: str, video_info: dict) -> str:
    """Построить drawtext фильтр для Auto Hook."""
    if not hook_text or not style:
        return ""

    w = video_info["width"]
    h = video_info["height"]

    # Общие настройки
    font_size = max(48, w // 20)
    shadow = "shadowx=3:shadowy=3:shadowcolor=black@0.8"
    fade = "alpha='if(lt(t,0.3),t/0.3,if(lt(t,4.5),1,if(lt(t,5),(5-t)/0.5,0)))'"

    if style == "viral":
        # Сверху, большой белый текст с чёрной обводкой
        y_pos = int(h * 0.08)
        return (
            f"drawtext=text='{hook_text}':"
            f"fontsize={font_size + 10}:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"box=1:boxcolor=black@0.6:boxborderw=12:"
            f"{shadow}:{fade}"
        )

    elif style == "reels":
        # Снизу, жёлтый
        y_pos = int(h * 0.82)
        return (
            f"drawtext=text='{hook_text}':"
            f"fontsize={font_size}:"
            f"fontcolor=yellow:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"box=1:boxcolor=black@0.7:boxborderw=10:"
            f"{shadow}:{fade}"
        )

    elif style == "cinema":
        # По центру кадра, белый, italic
        y_pos = int(h * 0.45)
        return (
            f"drawtext=text='{hook_text}':"
            f"fontsize={font_size - 4}:"
            f"fontcolor=white@0.95:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"{shadow}:{fade}"
        )

    return ""


def smart_crop(input_path: str, output_path: str, template_key: str) -> bool:
    """
    Умная обрезка:
    - Viral / Reels → вертикальный 9:16
    - Cinema        → горизонтальный 16:9 с полосами
    - Clean         → без изменений размера
    """
    t = TEMPLATES[template_key]
    info = get_video_info(input_path)
    speed = round(random.uniform(*t["speed_range"]), 3)

    # Выбрать случайный hook текст
    hook_text = ""
    if t["add_hook"] and t["hook_texts"]:
        hook_text = random.choice(t["hook_texts"])
        # Экранируем спецсимволы для ffmpeg drawtext
        hook_text = hook_text.replace("'", "\\'").replace(":", "\\:")

    # Строим цепочку фильтров
    vf_parts = [t["vf"]]

    if t["add_hook"] and hook_text:
        hook_filter = build_hook_filter(hook_text, t["hook_style"], info)
        if hook_filter:
            vf_parts.append(hook_filter)

    # Добавляем изменение скорости в видео-фильтр
    vf_parts.append(f"setpts={round(1/speed, 4)}*PTS")

    vf_chain = ",".join(vf_parts)
    af = f"atempo={speed}"

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", vf_chain,
        "-af", af,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[FFmpeg] Error:\n{result.stderr[-1000:]}")
            return False
        return True
    except Exception as e:
        print(f"[FFmpeg] Exception: {e}")
        return False


def uniqualize(input_path: str, template_key: str) -> str | None:
    """Главная функция уникализации."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.mp4")

    success = smart_crop(input_path, output_path, template_key)
    if success and os.path.exists(output_path):
        return output_path
    return None
