# 🎬 VideoBot — Telegram бот для скачивания и уникализации видео

Аналог **Opus Clip** в Telegram: скачивает видео с YouTube/Instagram/TikTok,
уникализирует и добавляет субтитры. Доступ только после подписки на канал.

---

## ✨ Возможности

| Функция | Описание |
|---|---|
| 📥 Скачивание | YouTube, Instagram Reels, TikTok |
| 🪝 Auto Hook | Цепляющий текст в первые 5 сек (как в Opus Clip) |
| ✂️ Умная обрезка | Автоматически под 9:16, 16:9, 21:9 |
| 🎨 4 шаблона | Viral Hook (99), Reels/Shorts (95), Cinema (88), Clean (78) |
| 🔤 Субтитры | Whisper AI — авто-транскрипция и вжигание |
| 🔒 Подписка-гейт | Видео только после подписки на канал |
| 🎲 Рандом | Случайный шаблон по кнопке |

---

## 🚀 Установка

### 1. Системные зависимости

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install ffmpeg python3 python3-pip -y

# macOS
brew install ffmpeg python3
```

### 2. Клонировать проект

```bash
git clone <repo>
cd video_bot
```

### 3. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

> ⚠️ `openai-whisper` установит PyTorch (~2GB). Если нужна только лёгкая версия, можно использовать `faster-whisper`:
> ```bash
> pip install faster-whisper
> ```
> И поменять в `subtitles.py` вызов whisper на faster-whisper.

### 4. Настройка .env

```bash
cp .env.example .env
nano .env   # или любой редактор
```

Заполни:
```
BOT_TOKEN=токен_от_BotFather
CHANNEL_ID=@твой_канал
ADMIN_ID=твой_telegram_id
WHISPER_MODEL=base
```

### 5. Настройка бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather)
2. `/newbot` → задай имя и username
3. Скопируй токен в `.env`
4. Добавь бота как **администратора** в свой канал (чтобы он мог проверять подписку)

### 6. Запуск

```bash
python bot.py
```

Для фонового запуска:
```bash
nohup python bot.py > bot.log 2>&1 &
```

Или через `screen`:
```bash
screen -S videobot
python bot.py
# Ctrl+A, D — отсоединиться
```

---

## 🎨 Шаблоны

### 🔥 Viral Hook [99/100]
- Формат: 9:16 (вертикальный)
- Zoom эффект
- Насыщенность +40%
- Auto Hook сверху: белый текст, чёрная обводка
- Скорость: -3% (чуть медленнее = драматичнее)

### 📱 Reels / Shorts [95/100]
- Формат: 9:16
- Яркие цвета
- Auto Hook снизу: жёлтый текст
- Скорость: +5% (энергичнее)

### 🎬 Cinema [88/100]
- Формат: горизонтальный с чёрными полосами (21:9)
- Тёмные тона, кинематограф
- Auto Hook: белый по центру
- Скорость: -5%

### ✨ Clean [78/100]
- Минимальные изменения
- Лёгкий hue shift + яркость
- Без Hook
- Просто уникализация

---

## 🔤 Субтитры (Whisper AI)

Бот использует [OpenAI Whisper](https://github.com/openai/whisper) для транскрипции:

1. Из видео извлекается аудио (16kHz WAV)
2. Whisper генерирует `.srt` файл с таймкодами
3. FFmpeg вжигает субтитры в видео со стилем шаблона

Стили субтитров:
- **Viral**: белый + чёрный бокс, крупный шрифт
- **Reels**: жёлтый текст снизу
- **Cinema**: классический белый

---

## 📁 Структура проекта

```
video_bot/
├── bot.py           # Основная логика бота (aiogram 3)
├── downloader.py    # Скачивание через yt-dlp
├── uniqualizer.py   # FFmpeg уникализация + Auto Hook
├── subtitles.py     # Whisper субтитры + вжигание
├── config.py        # Конфигурация
├── requirements.txt
├── .env.example
├── downloads/       # Временные скачанные файлы
└── outputs/         # Готовые видео (очищаются после отправки)
```

---

## ⚙️ Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `BOT_TOKEN` | Токен от BotFather | `123:AAFxxx` |
| `CHANNEL_ID` | Username или ID канала | `@mychannel` |
| `ADMIN_ID` | Твой Telegram ID | `123456789` |
| `WHISPER_MODEL` | Модель Whisper | `tiny`/`base`/`small` |

---

## 🐛 Частые проблемы

**Бот не проверяет подписку:**
→ Добавь бота администратором в канал

**Ошибка скачивания Instagram:**
→ yt-dlp требует cookies для некоторых видео. Добавь `--cookies-from-browser chrome` в ydl_opts

**Whisper очень долго работает:**
→ Поменяй `WHISPER_MODEL=tiny` в `.env`

**Видео > 50MB не отправляется:**
→ Бот автоматически отправит как документ. Для больших файлов нужен Telegram Bot API Local Server.

---

## 📝 Лицензия

MIT — используй свободно.
