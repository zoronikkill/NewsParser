import os
import psycopg2
from datetime import datetime, timedelta
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "news")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


MAIN_MENU = [
    ["🔹 Все Новости"],
    ["🗂 Выбрать категорию"],
    ["🔍 Поиск по ключевому слову"]
]

CATEGORY_MENU = [
    [KeyboardButton("🔹 Все Новости")],
    [KeyboardButton("🗂 Выбрать категорию")]
]


CATEGORY_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Новости", callback_data="category_novosti")],
    [InlineKeyboardButton("Политика", callback_data="category_politics")],
    [InlineKeyboardButton("Экономика", callback_data="category_economics")],
    [InlineKeyboardButton("Общество", callback_data="category_society")],
    [InlineKeyboardButton("Происшествия", callback_data="category_incident")],
    [InlineKeyboardButton("Культура и спорт", callback_data="category_culture-i-sport")]
])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать! Выберите опцию из меню ниже.",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )


async def news_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите опцию:",
        reply_markup=ReplyKeyboardMarkup(CATEGORY_MENU, resize_keyboard=True)
    )


async def all_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите период:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Сегодня", callback_data="news_today")],
            [InlineKeyboardButton("5 последних дней", callback_data="news_5days")],
            [InlineKeyboardButton("N последних дней", callback_data="news_custom_days")],
            [InlineKeyboardButton("Задать диапазон", callback_data="news_period")]
        ])
    )


def fetch_news(query, params):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите категорию новостей:",
        reply_markup=CATEGORY_KEYBOARD
    )


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_map = {
        "category_novosti": "novosti",
        "category_politics": "politics",
        "category_economics": "economics",
        "category_society": "society",
        "category_incident": "incident",
        "category_culture-i-sport": "culture-i-sport",
    }
    selected_category = category_map.get(query.data)

    if selected_category:
        context.user_data['selected_category'] = selected_category
        await query.message.reply_text(
            f"Вы выбрали категорию: {selected_category}. Теперь выберите период:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Сегодня", callback_data="period_today")],
                [InlineKeyboardButton("5 последних дней", callback_data="period_5days")],
                [InlineKeyboardButton("N последних дней", callback_data="period_custom_days")],
                [InlineKeyboardButton("Задать диапазон", callback_data="period_custom_range")]
            ])
        )
    else:
        await query.message.reply_text("Произошла ошибка. Попробуйте ещё раз.")


async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_category = context.user_data.get('selected_category')

    if not selected_category:
        await query.message.reply_text("Ошибка! Категория не выбрана.")
        return

    if query.data == "period_today":
        news = fetch_news(
            "SELECT title, date, link FROM news WHERE category ILIKE %s AND date >= %s ORDER BY date DESC",
            [f"%{selected_category}%", datetime.now().date()]
        )
        await send_news_response(query, news)

    elif query.data == "period_5days":
        days_ago = datetime.now() - timedelta(days=5)
        news = fetch_news(
            "SELECT title, date, link FROM news WHERE category ILIKE %s AND date >= %s ORDER BY date DESC",
            [f"%{selected_category}%", days_ago]
        )
        await send_news_response(query, news)

    elif query.data == "period_custom_days":
        await query.message.reply_text("Введите количество дней (например, 10):")
        context.user_data['await_days_for_category'] = True

    elif query.data == "period_custom_range":
        await query.message.reply_text("Введите период в формате YYYY-MM-DD YYYY-MM-DD:")
        context.user_data['await_range_for_category'] = True


async def handle_news_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "news_today":
        news = fetch_news("SELECT title, date, link FROM news WHERE date >= %s", [datetime.now().date()])
        await send_news_response(query, news)

    elif query.data == "news_5days":
        days_ago = datetime.now() - timedelta(days=5)
        news = fetch_news("SELECT title, date, link FROM news WHERE date >= %s", [days_ago])
        await send_news_response(query, news)

    elif query.data == "news_custom_days":
        await query.message.reply_text("Введите количество дней (например, 10):")
        context.user_data['await_days'] = True

    elif query.data == "news_period":
        await query.message.reply_text("Введите период в формате YYYY-MM-DD YYYY-MM-DD:")
        context.user_data['await_period'] = True


async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите ключевое слова для поиска. Вы можете также указать диапазон дат в формате:\n"
        "`ключевое_слово YYYY-MM-DD YYYY-MM-DD`\n\n"
        "Примеры: `\nДТП\nДТП 2024-12-01 2024-12-15`",
        parse_mode="Markdown"
    )
    context.user_data['await_search'] = True

async def custom_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    selected_category = context.user_data.get('selected_category')

    
    if context.user_data.get('await_days'):
        try:
            days = int(text)
            days_ago = datetime.now() - timedelta(days=days)
            news = fetch_news(
                "SELECT title, date, link FROM news WHERE date >= %s ORDER BY date DESC",
                [days_ago]
            )
            await send_news_response(update, news)
        except ValueError:
            await update.message.reply_text("Некорректный ввод. Введите число.")
        context.user_data.pop('await_days', None)

    
    elif context.user_data.get('await_period'):
        try:
            start_date, end_date = text.split()
            news = fetch_news(
                "SELECT title, date, link FROM news WHERE date BETWEEN %s AND %s ORDER BY date DESC",
                [start_date, end_date]
            )
            await send_news_response(update, news)
        except ValueError:
            await update.message.reply_text("Некорректный формат. Введите в формате YYYY-MM-DD YYYY-MM-DD.")
        context.user_data.pop('await_period', None)

    
    elif context.user_data.get('await_days_for_category') and selected_category:
        try:
            days = int(text)
            days_ago = datetime.now() - timedelta(days=days)
            news = fetch_news(
                "SELECT title, date, link FROM news WHERE category ILIKE %s AND date >= %s ORDER BY date DESC",
                [f"%{selected_category}%", days_ago]
            )
            await send_news_response(update, news)
        except ValueError:
            await update.message.reply_text("Некорректный ввод. Введите число.")
        context.user_data.pop('await_days_for_category', None)

    
    elif context.user_data.get('await_range_for_category') and selected_category:
        try:
            start_date, end_date = text.split()
            news = fetch_news(
                "SELECT title, date, link FROM news WHERE category ILIKE %s AND date BETWEEN %s AND %s ORDER BY date DESC",
                [f"%{selected_category}%", start_date, end_date]
            )
            await send_news_response(update, news)
        except ValueError:
            await update.message.reply_text("Некорректный формат. Введите в формате YYYY-MM-DD YYYY-MM-DD.")
        context.user_data.pop('await_range_for_category', None)

    elif text == "🔍 Поиск по ключевому слову":
        await search_menu(update, context)

    elif context.user_data.get('await_search'):
        try:
            parts = text.split()
            if len(parts) == 1:
                keywords = parts[0]
                start_date = None
                end_date = None
            elif len(parts) == 3:
                keywords = parts[0]
                start_date, end_date = parts[1], parts[2]
            else:
                raise ValueError("Некорректный ввод.")

            query = "SELECT title, date, link FROM news WHERE title ~* %s"
            params = [fr'\m{keywords}\M']

            if start_date and end_date:
                query += " AND date BETWEEN %s AND %s"
                params.extend([start_date, end_date])

            news = fetch_news(query, params)
            await send_news_response(update, news)
        except ValueError:
            await update.message.reply_text("Некорректный ввод. Введите ключевое слова и, при необходимости, диапазон дат в формате YYYY-MM-DD YYYY-MM-DD.")
        context.user_data.pop('await_search', None)


async def send_news_response(target, news):
    MAX_MESSAGE_LENGTH = 4000  
    if not news:
        await target.message.reply_text("Нет новостей для отображения.")
        return

    response = ""
    for row in news:
        news_item = f"🔹 {row[0]} ({row[1].strftime('%Y-%m-%d')}): {row[2]}\n\n"
        if len(response) + len(news_item) > MAX_MESSAGE_LENGTH:
            await target.message.reply_text(response)
            response = news_item
        else:
            response += news_item

    if response:
        await target.message.reply_text(response)


if __name__ == "__main__":
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("📰 Новости"), news_menu))
    app.add_handler(MessageHandler(filters.Regex("🔹 Все Новости"), all_news))
    app.add_handler(MessageHandler(filters.Regex("🗂 Выбрать категорию"), select_category))
    app.add_handler(CallbackQueryHandler(handle_news_query, pattern="news_.*"))
    app.add_handler(CallbackQueryHandler(handle_category_selection, pattern="category_.*"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_input_handler))
    app.add_handler(CallbackQueryHandler(handle_period_selection, pattern="period_.*"))
    app.add_handler(MessageHandler(filters.Regex("🔍 Поиск по ключевому слову"), search_menu))


    print("Бот запущен...")
    app.run_polling()
