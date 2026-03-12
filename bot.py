import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, CHANNEL_ID
from downloader import download_video, is_supported_url, detect_platform
from uniqualizer import uniqualize, TEMPLATES
from subtitles import generate_subtitles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ══════════════════════════════════════════════════════
#  STATES
# ══════════════════════════════════════════════════════
class VideoFlow(StatesGroup):
    waiting_template = State()
    processing = State()


# ══════════════════════════════════════════════════════
#  SUBSCRIPTION CHECK
# ══════════════════════════════════════════════════════
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception as e:
        logger.warning(f"check_subscription error: {e}")
        return False


def sub_keyboard() -> InlineKeyboardMarkup:
    channel = CHANNEL_ID.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{channel}")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
    ])


# ══════════════════════════════════════════════════════
#  TEMPLATE KEYBOARD  (как в Opus Clip)
# ══════════════════════════════════════════════════════
def templates_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key, t in TEMPLATES.items():
        score = t.get("viral_score", 0)
        stars = "🔥" if score >= 90 else ("⚡" if score >= 75 else "✨")
        rows.append([InlineKeyboardButton(
            text=f"{stars} {t['name']}  [{score}/100]",
            callback_data=f"tpl:{key}"
        )])
    rows.append([InlineKeyboardButton(text="🎲 Случайный шаблон", callback_data="tpl:random")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sub_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔤 С субтитрами", callback_data="subs:yes"),
            InlineKeyboardButton(text="🚫 Без субтитров", callback_data="subs:no"),
        ]
    ])


# ══════════════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎬 <b>VideoBot — скачай и уникализируй за секунды</b>\n\n"
        "Поддерживаю:\n"
        "  📺 YouTube (видео + Shorts)\n"
        "  📸 Instagram (Reels, посты)\n"
        "  🎵 TikTok\n\n"
        "Просто пришли ссылку — и выбери шаблон как в <b>Opus Clip</b>!\n\n"
        "Фичи:\n"
        "  🔤 Авто-субтитры (Whisper AI)\n"
        "  🪝 Auto Hook — цепляющий текст в первые 5 сек\n"
        "  ✂️ Умная обрезка под Reels/Shorts/TikTok\n"
        "  🎨 4 шаблона уникализации со скором виральности\n\n"
        "👇 Пришли ссылку на видео!",
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Пришли ссылку YouTube / Instagram / TikTok\n"
        "2. Подпишись на канал (если ещё не подписан)\n"
        "3. Выбери шаблон обработки\n"
        "4. Выбери нужны ли субтитры\n"
        "5. Получи готовое видео!\n\n"
        "⚙️ <b>Шаблоны:</b>\n"
        "🔥 Viral Hook — Auto Hook + яркие субтитры + zoom\n"
        "📱 Reels/Shorts — вертикальный 9:16 формат\n"
        "🎬 Cinema — кинематографичный стиль\n"
        "✨ Clean — лёгкая уникализация без лишнего\n",
        parse_mode="HTML"
    )


@dp.message(F.text.regexp(r"https?://"))
async def handle_link(message: Message, state: FSMContext):
    url = message.text.strip()
    user_id = message.from_user.id

    if not is_supported_url(url):
        await message.answer(
            "❌ Ссылка не поддерживается.\n"
            "Принимаю: YouTube, Instagram, TikTok"
        )
        return

    platform = detect_platform(url)

    # Проверяем подписку
    subscribed = await check_subscription(user_id)
    if not subscribed:
        await state.update_data(pending_url=url, platform=platform)
        await message.answer(
            f"🔒 <b>Доступ закрыт!</b>\n\n"
            f"Видео с <b>{platform}</b> готово к скачиванию, но для получения нужно подписаться на канал.\n\n"
            f"Это займёт 5 секунд 👇",
            reply_markup=sub_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(pending_url=url, platform=platform)
    await show_templates(message, platform, state)


@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(callback: CallbackQuery, state: FSMContext):
    subscribed = await check_subscription(callback.from_user.id)
    if not subscribed:
        await callback.answer("❌ Подписка не найдена. Подпишись и попробуй снова!", show_alert=True)
        return

    await callback.answer("✅ Подписка подтверждена!")
    data = await state.get_data()
    url = data.get("pending_url")
    platform = data.get("platform", "видео")

    if not url:
        await callback.message.edit_text("✅ Подписка подтверждена! Пришли ссылку на видео.")
        return

    await show_templates(callback.message, platform, state, edit=True)


async def show_templates(message: Message, platform: str, state: FSMContext, edit: bool = False):
    text = (
        f"✅ Ссылка принята! Платформа: <b>{platform}</b>\n\n"
        f"🎨 <b>Выбери шаблон</b> (как в Opus Clip):\n\n"
        f"Каждый шаблон включает:\n"
        f"  🪝 Auto Hook — цепляющий заголовок\n"
        f"  ✂️ Умную обрезку\n"
        f"  🎨 Уникализацию\n"
    )
    kb = templates_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(VideoFlow.waiting_template)


@dp.callback_query(F.data.startswith("tpl:"), VideoFlow.waiting_template)
async def choose_template(callback: CallbackQuery, state: FSMContext):
    import random
    key = callback.data.split(":")[1]
    if key == "random":
        key = random.choice(list(TEMPLATES.keys()))

    await state.update_data(template_key=key)
    t = TEMPLATES[key]

    await callback.message.edit_text(
        f"✅ Шаблон: <b>{t['name']}</b>\n\n"
        f"🔤 Добавить <b>авто-субтитры</b> (Whisper AI)?\n"
        f"Субтитры как в Opus — анимированные, с выделением слов.",
        reply_markup=sub_options_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("subs:"))
async def choose_subs(callback: CallbackQuery, state: FSMContext):
    use_subs = callback.data.split(":")[1] == "yes"
    await state.update_data(use_subs=use_subs)
    await state.set_state(VideoFlow.processing)

    data = await state.get_data()
    url = data["pending_url"]
    template_key = data["template_key"]
    t = TEMPLATES[template_key]

    subs_text = "с субтитрами ✅" if use_subs else "без субтитров"
    await callback.message.edit_text(
        f"⚙️ Обрабатываю видео...\n\n"
        f"📋 Шаблон: <b>{t['name']}</b>\n"
        f"🔤 Субтитры: {subs_text}\n\n"
        f"⏳ Скачиваю видео...",
        parse_mode="HTML"
    )

    msg = callback.message
    user_id = callback.from_user.id

    try:
        # Шаг 1: Скачать
        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(None, download_video, url)

        if not video_path:
            await msg.edit_text("❌ Не удалось скачать видео. Проверь ссылку и попробуй снова.")
            await state.clear()
            return

        await msg.edit_text(
            f"⚙️ Скачано! Применяю шаблон <b>{t['name']}</b>...\n\n"
            f"🎨 Уникализация + монтаж...",
            parse_mode="HTML"
        )

        # Шаг 2: Уникализировать
        output_path = await loop.run_in_executor(
            None, uniqualize, video_path, template_key
        )

        if not output_path:
            await msg.edit_text("❌ Ошибка при обработке видео. Попробуй снова.")
            await state.clear()
            return

        # Шаг 3: Субтитры
        if use_subs:
            await msg.edit_text(
                "🔤 Генерирую субтитры через Whisper AI...\n"
                "Это может занять 30-60 сек...",
            )
            final_path = await loop.run_in_executor(
                None, generate_subtitles, output_path, template_key
            )
            if not final_path:
                final_path = output_path  # fallback без субтитров
        else:
            final_path = output_path

        # Шаг 4: Отправить
        await msg.edit_text("📤 Отправляю готовое видео...")

        viral_score = t.get("viral_score", 0)
        hook_text = t.get("hook_example", "")

        caption = (
            f"✅ <b>Готово!</b>\n\n"
            f"🎨 Шаблон: <b>{t['name']}</b>\n"
            f"🔥 Viral Score: <b>{viral_score}/100</b>\n"
            f"🔤 Субтитры: {'✅' if use_subs else '❌'}\n"
        )
        if hook_text:
            caption += f"\n🪝 <i>Auto Hook: «{hook_text}»</i>\n"

        caption += "\n🚀 Видео готово к публикации!"

        file_size = os.path.getsize(final_path)
        if file_size > 50 * 1024 * 1024:  # > 50MB — отправить как документ
            with open(final_path, "rb") as f:
                await bot.send_document(user_id, f, caption=caption, parse_mode="HTML")
        else:
            with open(final_path, "rb") as f:
                await bot.send_video(
                    user_id, f,
                    caption=caption,
                    parse_mode="HTML",
                    supports_streaming=True
                )

        await msg.delete()

    except Exception as e:
        logger.error(f"Processing error: {e}")
        await msg.edit_text(f"❌ Произошла ошибка: {str(e)[:200]}\n\nПопробуй ещё раз.")

    finally:
        # Чистим временные файлы
        for path_var in ["video_path", "output_path", "final_path"]:
            try:
                p = locals().get(path_var)
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        await state.clear()


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
async def main():
    for d in ["downloads", "outputs", "fonts"]:
        os.makedirs(d, exist_ok=True)
    logger.info("Bot started!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
