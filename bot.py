import json
import sqlite3
import uuid
import asyncio

from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = "7096864169:AAGtdUiagdPb9n1q9mDfQiZCzVsNBKAMFfk"
ADMIN_ID = 6376036011

# ================= DATABASE =================
conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_ids TEXT,
    code TEXT,
    file_type TEXT
)
""")
conn.commit()

# ================= MEMORY =================
album_jobs = {}

# ================= GENERATE CODE =================
def generate_code():
    return str(uuid.uuid4())[:8]

# ================= START COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        code = context.args[0]

        cursor.execute("SELECT file_ids, file_type FROM files WHERE code=?", (code,))
        result = cursor.fetchone()

        if result:
            file_ids, file_type = result
            file_ids = json.loads(file_ids)

            try:
                if len(file_ids) == 1:
                    file_id = file_ids[0]

                    if file_type == "photo":
                        await update.message.reply_photo(file_id)
                    elif file_type == "video":
                        await update.message.reply_video(file_id)
                    else:
                        await update.message.reply_document(file_id)

                else:
                    media = []
                    for f in file_ids:
                        if file_type == "photo":
                            media.append(InputMediaPhoto(f))
                        else:
                            media.append(InputMediaVideo(f))

                    await update.message.reply_media_group(media)

            except:
                await update.message.reply_text("❌ Error sending file")

        else:
            await update.message.reply_text("❌ File not found")

    else:
        await update.message.reply_text("Send me a file to save")

# ================= SAVE FILE =================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ❌ only admin
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not allowed to send message")
        return

    # ================= HANDLE ALBUM =================
    if update.message.media_group_id:
        media_group = update.message.media_group_id

        if media_group not in album_jobs:
            album_jobs[media_group] = {
                "files": [],
                "type": None
            }

        album = album_jobs[media_group]
        chat_id = update.effective_chat.id

        # add file
        if update.message.photo:
            album["files"].append(update.message.photo[-1].file_id)
            album["type"] = "photo"

        elif update.message.video:
            album["files"].append(update.message.video.file_id)
            album["type"] = "video"

        # cancel previous task
        if "task" in album:
            album["task"].cancel()

        # process after delay
        async def process_album():
            await asyncio.sleep(2)

            data = album_jobs.pop(media_group, None)
            if not data:
                return

            file_ids = data["files"]
            file_type = data["type"]

            code = "pl_" + generate_code()

            cursor.execute(
                "INSERT INTO files (file_ids, code, file_type) VALUES (?, ?, ?)",
                (json.dumps(file_ids), code, file_type)
            )
            conn.commit()

            link = f"https://t.me/Asian_maal_bot?start={code}"

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Album Saved!\n🔗 {link}"
            )

        album["task"] = asyncio.create_task(process_album())
        return

    # ================= SINGLE FILE =================
    file_ids = []
    file_type = None

    if update.message.document:
        file_ids = [update.message.document.file_id]
        file_type = "document"

    elif update.message.photo:
        file_ids = [update.message.photo[-1].file_id]
        file_type = "photo"

    elif update.message.video:
        file_ids = [update.message.video.file_id]
        file_type = "video"

    if file_ids:
        code = "pl_" + generate_code()

        cursor.execute(
            "INSERT INTO files (file_ids, code, file_type) VALUES (?, ?, ?)",
            (json.dumps(file_ids), code, file_type)
        )
        conn.commit()

        link = f"https://t.me/Asian_maal_bot?start={code}"

        await update.message.reply_text(f"✅ Saved!\n🔗 {link}")

# ================= RUN BOT =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL, save_file))

app.run_polling()



