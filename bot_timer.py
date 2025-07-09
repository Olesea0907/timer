import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

# 🔑 Token Telegram și Postgres din variabile de mediu
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# 🕓 Fus orar Moldova
MOLDOVA_TZ = pytz.timezone("Europe/Chisinau")

# 🔢 Format afișare timp
def format_time_minutes(total_seconds: int) -> str:
    days = total_seconds // 86400
    h, rem = divmod(total_seconds % 86400, 3600)
    m = rem // 60
    if days > 0:
        return f"{days} zile {h:02}h:{m:02}m"
    else:
        return f"{h:02}h:{m:02}m"

# 🔗 Conexiune Postgres
def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# 💾 Salvează timer-ul (cu message_id!)
def save_timer(chat_id, end_time, message_id):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                chat_id BIGINT PRIMARY KEY,
                end_time TIMESTAMPTZ,
                message_id BIGINT
            );
        """)
        cur.execute("""
            INSERT INTO timers (chat_id, end_time, message_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE
            SET end_time = EXCLUDED.end_time, message_id = EXCLUDED.message_id;
        """, (chat_id, end_time, message_id))
        conn.commit()
    conn.close()

# 🟢 Pornește un timer NOU
async def run_timer(context: ContextTypes.DEFAULT_TYPE, chat_id, target_dt):
    now = datetime.now(MOLDOVA_TZ)
    total_seconds = int((target_dt - now).total_seconds())

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ Timp rămas: {format_time_minutes(total_seconds)}"
    )
    print(f"[run_timer] Mesaj nou: {msg.message_id}")  # ✅ CORESPUNZĂTOR AICI!

    # Salvează în DB cu noul message_id
    save_timer(chat_id, target_dt.isoformat(), msg.message_id)

    for remaining in range(total_seconds - 60, -1, -60):
        await asyncio.sleep(60)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.message_id,
                text=f"⏳ Timp rămas: {format_time_minutes(remaining)}"
            )
        except Exception as e:
            print(f"[run_timer] Eroare la edit: {e}")
            break

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text="⏰ Timpul a expirat!"
        )
    except:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ Timpul a expirat!"
        )

# ♻️ Repornește timer-ul existent (la restart) - fallback robust
async def resume_timer(bot, chat_id, target_dt, message_id):
    now = datetime.now(MOLDOVA_TZ)
    total_seconds = int((target_dt - now).total_seconds())

    msg_id = message_id  # începem cu mesajul vechi

    for remaining in range(total_seconds - 60, -1, -60):
        await asyncio.sleep(60)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"⏳ Timp rămas: {format_time_minutes(remaining)}"
            )
        except Exception as e:
            print(f"[resume_timer] Eroare la edit: {e}")
            # Fallback: trimite mesaj nou
            new_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"⏳ Timp rămas: {format_time_minutes(remaining)}"
            )
            msg_id = new_msg.message_id
            print(f"[resume_timer] Fallback: mesaj nou trimis cu ID {msg_id}")
            save_timer(chat_id, target_dt.isoformat(), msg_id)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text="⏰ Timpul a expirat!"
        )
    except:
        await bot.send_message(
            chat_id=chat_id,
            text="⏰ Timpul a expirat!"
        )

# 🗓️ Handler /start_timer
async def start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Folosește: /start_timer DD.MM.YYYY HH:MM\n"
            "Exemplu: /start_timer 31.08.2025 18:00"
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
            "Format invalid! Folosește: DD.MM.YYYY HH:MM\n"
            "Exemplu: /start_timer 31.08.2025 18:00"
        )
        return

    asyncio.create_task(run_timer(context, update.effective_chat.id, target_dt))

# 🔄 Restore la pornire
async def restore_timers(app):
    print("🔄 Restabilim timer-ele din DB...")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT chat_id, end_time, message_id FROM timers;")
        rows = cur.fetchall()
    conn.close()

    now = datetime.now(MOLDOVA_TZ)
    for row in rows:
        end_time = row['end_time'].astimezone(MOLDOVA_TZ)
        if (end_time - now).total_seconds() > 0:
            print(f"🔄 Repornesc timer pentru chat {row['chat_id']}")
            asyncio.create_task(resume_timer(app.bot, row['chat_id'], end_time, row['message_id']))
        else:
            print(f"⏰ Timer expirat pentru chat {row['chat_id']} - ignorat.")

# 🚀 Bootstrap bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start_timer", start_timer))
app.post_init = restore_timers

print("✅ Botul rulează cu POLLING! Timer-ele sunt salvate în Postgres și revin automat la restart.")
app.run_polling()
