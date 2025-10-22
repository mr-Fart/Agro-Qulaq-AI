import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import google.generativeai as genai
import pandas as pd

# === 1. Настройки ===
TELEGRAM_TOKEN = "ENTER YOUR TG TOKEN"
GEMINI_API_KEY = "ENTER YOUR GEMINI API KEY"
DATABASE_FILE = "sounddefbase.xlsx"  # Путь к вашему файлу с базой данных

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# === 2. Загрузка базы данных ===
def load_database():
    """Загружает базу данных поломок из Excel файла"""
    try:
        df = pd.read_excel(DATABASE_FILE)
        # Предполагаем, что первый столбец - симптомы, второй - поломки
        df.columns = ['симптомы', 'поломка']
        return df
    except Exception as e:
        print(f"⚠️ Ошибка загрузки базы данных: {e}")
        return None

# Загружаем базу при старте
database = load_database()

def create_diagnosis_prompt(database_df):
    """Создает промпт с базой данных для Gemini"""
    if database_df is None or database_df.empty:
        return None
    
    # Формируем таблицу для промпта
    db_text = "База данных поломок двигателей тракторов:\n\n"
    for idx, row in database_df.iterrows():
        db_text += f"{idx+1}. Симптомы: {row['симптомы']}\n   Поломка: {row['поломка']}\n\n"
    
    prompt = f"""{db_text}

Ты — эксперт по диагностике двигателей сельскохозяйственной техники.
Проанализируй звуковой файл двигателя трактора и определи симптомы по звуку.

ВАЖНО: Используй ТОЛЬКО базу данных выше для определения поломки. 
Сопоставь выявленные симптомы с симптомами из базы данных и определи соответствующую поломку.

Верни результат строго по следующему шаблону:

Выявленные симптомы:
[Опиши что ты слышишь в звуке: стуки, шумы, неровная работа и т.д.]

Диагноз:
[Укажи поломку из базы данных, которая соответствует выявленным симптомам]

Рекомендации:
[Дай конкретные рекомендации по устранению на основе найденной поломки]

Если симптомы не соответствуют ни одной записи в базе данных, напиши:
**Диагноз:** Симптомы не найдены в базе данных. Рекомендуется консультация специалиста.

Отвечай кратко, по делу, на русском языке. Если в голосовом нет звука двигателя или это человек имитирует звук двигателя СООБЩИ ЧТО ЗВУК НЕ СООТВЕТСТВУЕТ
"""
    return prompt


# === 3. Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ База данных загружена" if database is not None else "⚠️ База данных не загружена"
    await update.message.reply_text(
        f"👋 Привет! Отправь голосовое сообщение 🚜 с работой двигателя трактора, "
        f"а я определю его состояние по базе данных.\n\n{status}"
    )


# === 4. Обработка голосового ===
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        await update.message.reply_text("⚠️ Отправь именно голосовое сообщение.")
        return

    if database is None:
        await update.message.reply_text(
            "❌ База данных не загружена. Проверьте файл база.xlsx"
        )
        return

    file = await context.bot.get_file(voice.file_id)
    ogg_path = tempfile.mktemp(suffix=".ogg")
    await file.download_to_drive(ogg_path)

    try:
        await update.message.reply_text("🎧 Анализирую звук по базе данных...")

        # Создаем промпт с базой данных
        diagnosis_prompt = create_diagnosis_prompt(database)
        
        if not diagnosis_prompt:
            await update.message.reply_text("❌ Ошибка формирования запроса")
            return

        # === Отправляем аудио в Gemini ===
        with open(ogg_path, "rb") as audio_file:
            audio_data = audio_file.read()
            
            response = model.generate_content([
                diagnosis_prompt,
                {
                    "mime_type": "audio/ogg",
                    "data": audio_data
                }
            ])

        result_text = response.text.strip()
        await update.message.reply_text(result_text)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при анализе: {e}")

    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)


# === 5. Команда для просмотра базы данных ===
async def show_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает содержимое базы данных"""
    if database is None:
        await update.message.reply_text("❌ База данных не загружена")
        return
    
    db_text = "📋 База данных поломок:\n\n"
    for idx, row in database.iterrows():
        db_text += f"{idx+1}. {row['симптомы']}\n   → {row['поломка']}\n\n"
    
    # Telegram ограничивает длину сообщений до 4096 символов
    if len(db_text) > 4000:
        db_text = db_text[:4000] + "\n\n... (база слишком большая, показана часть)"
    
    await update.message.reply_text(db_text)


# === 6. Запуск бота ===
def main():
    if database is None:
        print("⚠️ ВНИМАНИЕ: Не удалось загрузить базу данных!")
        print("Убедитесь, что файл 'база.xlsx' находится в той же папке")
    else:
        print(f"✅ База данных загружена: {len(database)} записей")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("database", show_database))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("✅ Бот запущен и готов к приёму голосовых сообщений...")
    app.run_polling()

if __name__ == "__main__":
    main()
