import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # Heroku Postgres

# Fus orar Moldova
MOLDOVA_TZ = pytz.timezone("Europe/Chisinau")

def format_time_minutes(total_seconds: int) -> str:
    days = total_seconds // 86400
    h, rem = divmod(total_seconds % 86400, 3600)
    m = rem // 60
    if days > 0:
        return f"{days} zile {h:02}h:{m:02}m"
    else:
        return f"{h:02}h:{m:02}m"

# Conexiune DB
def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def save_timer(chat_id, end_time):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                chat_id BIGINT PRIMARY KEY,
                end_time TIMESTAMP WITH TIME ZONE
            );
        """)
        cur.execute("""
            INSERT INTO timers (chat_id, end_time)
            VALUES (%s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET end_time = EXCLUDED.end_time;
        """, (chat_id, end_time))
        conn.commit()
    conn.close()

async def run_timer(context: ContextTypes.DEFAULT_TYPE, chat_id, target_dt):
    now = datetime.now(MOLDOVA_TZ)
    total_seconds = int((target_dt - now).total_seconds())

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ Timp rămas: {format_time_minutes(total_seconds)}"
    )

    for remaining in range(total_seconds - 60, -1, -60):
        await asyncio.sleep(60)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.message_id,
                text=f"⏳ Timp rămas: {format_time_minutes(remaining)}"
            )
        except Exception as e:
            print(f"Eroare la edit: {e}")
            break

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text="⏰ Timpul a expirat!"
        )
    except:
        pass

async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Folosește: /start_timer DD.MM.YYYY HH:MM\nExemplu: /start_timer 31.08.2025 18:00"
        )
        return

    date_str = context.args[0] + " " + context.args[1]

    try:
        target_dt = MOLDOVA_TZ.localize(datetime.strptime(date_str, "%d.%m.%Y %H:%M"))
        now = datetime.now(MOLDOVA_TZ)
        if target_dt <= now:
            await update.message.reply_text("Data și ora trebuie să fie în viitor! 📅")
            return
    except ValueError:
        await update.message.reply_text(
            "Format invalid! Folosește: DD.MM.YYYY HH:MM\nExemplu: /start_timer 31.08.2025 18:00"
        )
        return

    # Salvează în Postgres
    save_timer(update.effective_chat.id, target_dt.isoformat())

    # Pornește task-ul async separat
    asyncio.create_task(run_timer(context, update.effective_chat.id, target_dt))

# Restabilește timer-ele salvate la pornire
async def restore_timers(app):
    print("🔄 Restabilim timer-ele din DB...")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT chat_id, end_time FROM timers;")
        rows = cur.fetchall()
    conn.close()

    now = datetime.now(MOLDOVA_TZ)
    for row in rows:
        end_time = row['end_time'].astimezone(MOLDOVA_TZ)
        delta = end_time - now
        total_seconds = int(delta.total_seconds())
        if total_seconds > 0:
            asyncio.create_task(run_timer(app.bot, row['chat_id'], end_time))
        else:
            print(f"⏰ Timer expirat pentru chat_id {row['chat_id']} - ignorat.")

# Inițializează botul
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start_timer", start_timer))
app.post_init = restore_timers  # Rulează la pornire

print("⏳ Botul rulează cu POLLING! Timer-ele sunt salvate în Postgres și revin automat.")
app.run_polling()

