import os
import time
import sys
import requests
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from settings import (
    API_ID, API_HASH, BOT_TOKEN,
    SOURCE_CHANNEL, DEST_CHANNEL,
    CUSTOM_PREFIX, THUMBNAIL_URL,
    OWNER_ID, LOG_CHANNEL
)

logging.basicConfig(level=logging.INFO)

app = Client(
    "auto_renamer_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ===== Utilities =====

def human_readable(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

async def progress_bar(current, total, message, stage):
    percent = current * 100 / total
    bar = f"[{'=' * int(percent / 5)}{' ' * (20 - int(percent / 5))}]"
    await message.edit_text(
        f"**{stage}**\n{bar} {percent:.2f}%\n\n"
        f"{human_readable(current)} of {human_readable(total)}"
    )

def download_thumbnail(url: str) -> str:
    response = requests.get(url)
    filename = "temp_thumb.jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

# ===== Private Command Handlers =====

@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start_cmd(client, message):
    await message.reply_text("✅ Bot is alive and monitoring the source channel.")

@app.on_message(filters.command("ping") & filters.user(OWNER_ID))
async def ping_cmd(client, message):
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    await msg.edit(f"🏓 Pong: `{(end - start) * 1000:.2f} ms`")

@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_cmd(client, message):
    await message.reply_text(
        f"**Config:**\n"
        f"Prefix: `{CUSTOM_PREFIX}`\n"
        f"Source: `{SOURCE_CHANNEL}`\n"
        f"Dest: `{DEST_CHANNEL}`\n"
        f"Thumb URL: `{THUMBNAIL_URL}`"
    )

@app.on_message(filters.command("help") & filters.user(OWNER_ID))
async def help_cmd(client, message):
    await message.reply_text(
        "**Commands:**\n"
        "/start - Check status\n"
        "/ping - Check ping\n"
        "/status - Show config\n"
        "/help - Show help"
    )

@app.on_message(filters.user(OWNER_ID))
async def fallback(client, message):
    await message.reply_text("✅ I received your message.")

# ===== Channel Media Processor =====

@app.on_message(filters.channel & filters.chat(SOURCE_CHANNEL) & (filters.video | filters.document))
async def handle_file(client: Client, message: Message):
    media = message.video or message.document
    original_name = media.file_name or f"file_{int(time.time())}"
    file_ext = os.path.splitext(original_name)[1]
    new_name = f"{CUSTOM_PREFIX}{int(time.time())}{file_ext}"

    progress_msg = await message.reply_text("📥 Downloading...")

    download_path = await app.download_media(
        message=message,
        file_name=new_name,
        progress=progress_bar,
        progress_args=(progress_msg, "Downloading")
    )

    await progress_msg.edit_text("📤 Uploading...")

    thumb_path = download_thumbnail(THUMBNAIL_URL)

    try:
        await app.send_document(
            chat_id=DEST_CHANNEL,
            document=download_path,
            file_name=new_name,
            thumb=thumb_path,
            caption=f"`{new_name}`",
            progress=progress_bar,
            progress_args=(progress_msg, "Uploading")
        )
        log_text = f"✅ Uploaded: `{new_name}`"
    except Exception as e:
        log_text = f"❌ Upload failed: `{str(e)}`"

    os.remove(download_path)
    os.remove(thumb_path)
    await message.delete()
    await progress_msg.delete()

    try:
        await app.send_message(LOG_CHANNEL or OWNER_ID, log_text)
    except:
        pass

# ===== Startup =====

async def main():
    await app.start()
    try:
        await app.send_message(LOG_CHANNEL or OWNER_ID, "🚀 Bot Started and Monitoring Source Channel.")
    except Exception as e:
        print(f"[Startup log failed]: {e}")
    print("✅ Bot is running.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
