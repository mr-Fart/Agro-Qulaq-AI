Tractor Engine Diagnostic Bot
============================

Telegram-бот для диагностики двигателя трактора по звуку.

Функции:
- /start — приветствие
- Голосовое сообщение — анализ звука + диагноз
- /database — показать базу поломок

Файлы:
- tg_bot.py — основной скрипт
- sounddefbase.xlsx — база симптомов и поломок

Установка:
1. git clone <repo>
2. pip install -r requirements.txt
3. В tg_bot.py укажите TELEGRAM_TOKEN и GEMINI_API_KEY
4. python tg_bot.py

Зависимости: python-telegram-bot, google-generativeai, pandas, openpyxl

Лицензия: MIT