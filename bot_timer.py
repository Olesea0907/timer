import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")  

def format_time_minutes(total_seconds: int) -> str:
    days = total_seconds // 86400
    h, rem = divmod(total_seconds % 86400, 3600)
    m = rem // 60
    if days > 0:
        return f"{days} zile {h:02}h:{m:02}m"
    else:
        return f"{h:02}h:{m:02}m"

async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Rămâne la fel codul tău
    pass  # codul tău complet aici

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start_timer", start_timer))

print("⏳ Botul rulează! Folosește: /start_timer DD.MM.YYYY HH:MM")

app.run_polling()
