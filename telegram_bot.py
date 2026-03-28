# telegram_bot.py
import os
import sys
import base64
import logging
from io import BytesIO
from dotenv import load_dotenv

# aiogram v3.x
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# ✅ Импорт общей функции генерации
from logo_generator import generate_logo

# ─────────────────────────────────────────────────────────────
# 🔧 Конфигурация и логирование
# ─────────────────────────────────────────────────────────────
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 🔐 Валидация токена при старте
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ─────────────────────────────────────────────────────────────
# 🎨 Пресеты стилей (синхронизировано с app.py)
# ─────────────────────────────────────────────────────────────
PRESET_STYLES = {
    'minimalist': 'минималистичный логотип, чистый дизайн, простые геометрические формы',
    'modern': 'современный логотип, яркие цвета, динамичный дизайн',
    'geometric': 'геометрический логотип, четкие линии, абстрактные формы',
    'vintage': 'винтажный логотип, ретро стиль, классические элементы',
    'tech': 'технологичный логотип, футуристичный стиль, цифровой дизайн',
    'corporate': 'корпоративный логотип, профессиональный вид, строгий стиль',
    'creative': 'креативный логотип, художественный стиль, яркие цвета',
    'elegant': 'элегантный логотип, изысканный дизайн, утонченные формы'
}


# ─────────────────────────────────────────────────────────────
# 🧭 Машина состояний (FSM)
# ─────────────────────────────────────────────────────────────
class LogoGen(StatesGroup):
    waiting_for_name = State()  # Ожидание названия компании
    waiting_for_style = State()  # Ожидание выбора стиля
    waiting_for_details = State()  # Ожидание доработок / новых запросов


# ─────────────────────────────────────────────────────────────
# ⌨️ Вспомогательные функции: клавиатуры
# ─────────────────────────────────────────────────────────────
def get_styles_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопками стилей"""
    builder = ReplyKeyboardBuilder()
    # Кнопки в 2 колонки
    styles_list = list(PRESET_STYLES.keys())
    for i in range(0, len(styles_list), 2):
        row = [KeyboardButton(text=styles_list[i])]
        if i + 1 < len(styles_list):
            row.append(KeyboardButton(text=styles_list[i + 1]))
        builder.row(*row)
    builder.row(KeyboardButton(text="⏭ Пропустить выбор стиля"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_refinement_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопки после генерации логотипа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔧 Доработать этот", callback_data="refine_current")
    builder.button(text="🔄 Создать новый", callback_data="start_new")
    builder.button(text="🌐 Веб-версия", url="http://127.0.0.1:5000")  # ← замените на ваш домен
    builder.adjust(2, 1)
    return builder.as_markup()


# ─────────────────────────────────────────────────────────────
# 📦 Вспомогательная функция: отправка изображения
# ─────────────────────────────────────────────────────────────
async def send_logo_photo(message: types.Message, image_base64: str, caption: str, reply_markup=None):
    """Отправляет изображение из base64 в Телеграм"""
    try:
        image_data = base64.b64decode(image_base64)
        photo_file = BytesIO(image_data)
        photo_file.name = "logo.png"

        await message.answer_photo(
            photo=types.BufferedInputFile(file=photo_file.read(), filename="logo.png"),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer("❌ Не удалось отправить изображение. Попробуйте ещё раз.")
        return False


# ─────────────────────────────────────────────────────────────
# 🎬 Обработчики команд и сообщений (ИСПРАВЛЕННЫЕ)
# ─────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Старт диалога"""
    await state.clear()  # ✅ Исправлено: было dp.storage.clear(...)

    welcome_text = (
        f"🎨 *Привет, {message.from_user.first_name}!*\n\n"
        "Я бот для генерации логотипов с помощью ИИ.\n"
        "Создам уникальный логотип для вашей компании за 1-2 минуты.\n\n"
        "🌐 Также доступно [веб-приложение](http://127.0.0.1:5000) "
        "с расширенными настройками.\n\n"
        "👇 *Введите название вашей компании*, чтобы начать:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(LogoGen.waiting_for_name)  # ✅ Исправлено: было dp.storage.set_state(...)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка по командам"""
    help_text = (
        "📚 *Команды бота:*\n"
        "/start — начать генерацию нового логотипа\n"
        "/new — сбросить и начать заново\n"
        "/help — показать эту справку\n"
        "/settings — настройки (скоро)\n\n"
        "💡 *Советы:*\n"
        "• После генерации можно написать, что изменить — я доработаю логотип\n"
        "• Используйте стили для более точного результата\n"
        "• Веб-версия поддерживает загрузку референсов"
    )
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("new"))
async def cmd_new(message: types.Message, state: FSMContext):
    """Сброс и начало заново"""
    await cmd_start(message, state)  # ✅ Передаём state


# ─────────────────────────────────────────────────────────────
# 📝 Шаг 1: Ввод названия компании
# ─────────────────────────────────────────────────────────────

@dp.message(LogoGen.waiting_for_name)
async def handle_company_name(message: types.Message, state: FSMContext):
    """Обработка названия компании"""
    company_name = message.text.strip()

    # Валидация
    if len(company_name) < 2:
        await message.answer("❌ Название слишком короткое. Попробуйте ещё раз:")
        return

    if len(company_name) > 50:
        await message.answer("❌ Название слишком длинное (макс. 50 символов). Попробуйте короче:")
        return

    # Экранирование спецсимволов
    company_name_safe = company_name.replace('"', '\\"').replace("'", "\\'")

    await state.update_data(company_name=company_name_safe)

    # Показываем клавиатуру со стилями
    await message.answer(
        f"✅ *{company_name}* — отличное название!\n\n"
        "🎨 Выберите стиль логотипа:",
        parse_mode="Markdown",
        reply_markup=get_styles_keyboard()
    )
    await state.set_state(LogoGen.waiting_for_style)


# ─────────────────────────────────────────────────────────────
# 🎨 Шаг 2: Выбор стиля
# ─────────────────────────────────────────────────────────────

@dp.message(LogoGen.waiting_for_style)
async def handle_style(message: types.Message, state: FSMContext):
    """Обработка выбора стиля и запуск генерации"""
    data = await state.get_data()
    company_name = data.get('company_name')
    style_choice = message.text.strip()

    # Формируем базовый промпт
    prompt = f'Создай логотип для компании "{company_name}".'

    if style_choice in PRESET_STYLES:
        prompt += f' {PRESET_STYLES[style_choice]}.'
    elif style_choice != "⏭ Пропустить выбор стиля":
        # Пользователь ввёл свой текст — используем как дополнение к стилю
        prompt += f' {style_choice[:200]}.'  # ограничиваем длину

    prompt += ' Логотип на белом или прозрачном фоне, профессиональный дизайн, векторная графика.'

    await state.update_data(prompt=prompt)

    # Информируем о начале генерации
    status_msg = await message.answer(
        "⏳ *Генерирую логотип...*\n"
        "Это займёт около 1-2 минут. Пожалуйста, подождите.",
        parse_mode="Markdown"
    )

    # 🚀 Вызов общей функции генерации
    logger.info(f"Генерация для '{company_name}', стиль: '{style_choice}'")
    result = generate_logo(prompt)

    await status_msg.delete()  # Удаляем сообщение о статусе

    if 'error' in result:
        logger.error(f"Ошибка генерации: {result['error']}")
        await message.answer(
            f"❌ Ошибка генерации: {result['error']}\n\n"
            "Попробуйте ещё раз или напишите /help для помощи.",
            reply_markup=get_styles_keyboard()
        )
        return

    # ✅ Успешная генерация — отправляем изображение
    caption = (
        f"✨ *Готово! Логотип для \"{company_name}\"*\n\n"
        f"🎨 Стиль: `{style_choice if style_choice in PRESET_STYLES else 'пользовательский'}`\n"
        f"🔧 Хотите что-то изменить? Напишите ниже или используйте кнопки:"
    )

    await send_logo_photo(
        message=message,
        image_base64=result['image'],
        caption=caption,
        reply_markup=get_refinement_keyboard()
    )

    # Сохраняем контекст для доработки
    await state.update_data(seed=result['seed'], prompt=prompt, last_image=result['image'])
    await state.set_state(LogoGen.waiting_for_details)


# ─────────────────────────────────────────────────────────────
# 🔧 Шаг 3: Доработка / новые запросы
# ─────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "refine_current")
async def cb_refine_current(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки «Доработать этот»"""
    data = await state.get_data()
    if not data.get('prompt'):
        await callback.answer("❌ Сначала создайте логотип", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✏️ *Опишите, что нужно изменить:*\n"
        "Например:\n"
        "• «сделай цвета ярче»\n"
        "• «добавь круглую рамку»\n"
        "• «упрости форму, убери детали»\n"
        "• «используй синие оттенки»",
        parse_mode="Markdown"
    )
    # Состояние уже LogoGen.waiting_for_details — ждём текст


@dp.callback_query(F.data == "start_new")
async def cb_start_new(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки «Создать новый»"""
    await callback.answer()
    await callback.message.delete()
    await cmd_start(callback.message, state)  # ✅ Передаём state


@dp.message(LogoGen.waiting_for_details)
async def handle_refinement(message: types.Message, state: FSMContext):
    """Обработка доработки или нового запроса"""
    user_input = message.text.strip()

    # Проверка на команды
    if user_input.lower() in ['/start', '/new', 'новый', 'начать заново']:
        await cmd_start(message, state)
        return

    if user_input.lower() in ['/help']:
        await cmd_help(message)
        return

    data = await state.get_data()
    original_prompt = data.get('prompt')
    original_seed = data.get('seed')

    if not original_prompt:
        await message.answer("❌ Произошла ошибка: нет исходного промпта. Начните заново: /start")
        await cmd_start(message, state)
        return

    # Формируем промпт для доработки
    new_prompt = f'{original_prompt} Дополнительно: {user_input[:300]}'

    # Информируем о процессе
    status_msg = await message.answer("🔄 *Дорабатываю логотип...* Подождите ~1 минуту.", parse_mode="Markdown")

    # 🚀 Вызов генерации с тем же seed для сохранения структуры
    logger.info(f"Доработка: seed={original_seed}, дополнение='{user_input[:50]}...'")
    result = generate_logo(new_prompt, seed=original_seed)

    await status_msg.delete()

    if 'error' in result:
        logger.error(f"Ошибка доработки: {result['error']}")
        await message.answer(
            f"❌ Не удалось доработать: {result['error']}\n\n"
            "Попробуйте упростить запрос или начать заново: /new"
        )
        return

    # ✅ Отправляем доработанный логотип
    company_name = data.get('company_name', 'вашей компании')
    caption = (
        f"✅ *Готово! Обновлённый логотип*\n\n"
        f"🔧 Изменения: `{user_input[:100]}{'...' if len(user_input) > 100 else ''}`\n\n"
        f"Ещё правки? Напишите ниже 👇"
    )

    await send_logo_photo(
        message=message,
        image_base64=result['image'],
        caption=caption,
        reply_markup=get_refinement_keyboard()
    )

    # Обновляем контекст
    await state.update_data(prompt=new_prompt, seed=result['seed'], last_image=result['image'])


# ─────────────────────────────────────────────────────────────
# 🛡️ Обработчик неизвестных команд / сообщений
# ─────────────────────────────────────────────────────────────

@dp.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    """Обработка сообщений вне контекста"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "🤔 Я не совсем понял. Используйте команды:\n"
            "/start — создать логотип\n"
            "/help — справка",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        # Если в состоянии — передаём дальше (для гибкости)
        await message.answer("⏳ Обрабатываю ваш запрос...")


# ─────────────────────────────────────────────────────────────
# 🚀 Запуск бота
# ─────────────────────────────────────────────────────────────

async def on_startup():
    """Действия при старте бота"""
    logger.info("🤖 Telegram-бот запущен")
    try:
        bot_info = await bot.get_me()
        logger.info(f"✓ Бот: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"❌ Не удалось получить информацию о боте: {e}")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🛑 Telegram-бот останавливается")
    await bot.session.close()


if __name__ == "__main__":
    # Регистрация хуков старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🔄 Запуск polling...")

    # 🚀 Запуск бота (блокирующий)
    try:
        import asyncio

        asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
    except KeyboardInterrupt:
        logger.info("⌨️ Остановка по Ctrl+C")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {e}")
        sys.exit(1)