import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import aiohttp
print("✅ aiohttp version:", aiohttp.__version__)


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
    if len(context.args) < 2:
        await update.message.reply_text(
            "Folosește: /start_timer DD.MM.YYYY HH:MM\nExemplu: /start_timer 31.08.2025 18:00"
        )
        return

    date_str = context.args[0] + " " + context.args[1]

    try:
        target_dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        now = datetime.now()
        delta = target_dt - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            await update.message.reply_text("Data și ora trebuie să fie în viitor! 📅")
            return
    except ValueError:
        await update.message.reply_text(
            "Format invalid! Folosește: DD.MM.YYYY HH:MM\nExemplu: /start_timer 31.08.2025 18:00"
        )
        return

    msg = await update.message.reply_text(
        f"⏳ Timp rămas: {format_time_minutes(total_seconds)}"
    )

    for remaining in range(total_seconds - 60, -1, -60):
        await asyncio.sleep(60)
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=f"⏳ Timp rămas: {format_time_minutes(remaining)}"
            )
        except Exception as e:
            print(f"Eroare la edit: {e}")
            break

    try:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text="⏰ Timpul a expirat!"
        )
    except:
        pass

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start_timer", start_timer))

print("⏳ Botul rulează! Folosește: /start_timer DD.MM.YYYY HH:MM")
PORT = int(os.environ.get("PORT", 8443))
WEBHOOK_URL = f"https://dynamic-spontaneity-production-270c.up.railway.app/{TOKEN}"

app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=WEBHOOK_URL
)
