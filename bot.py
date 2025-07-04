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
app = Client("auto_renamer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# === UTILS ===

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


# === COMMAND HANDLERS ===

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("✅ Bot is alive and monitoring the source channel.")


@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message):
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    await msg.edit(f"🏓 Pong: `{(end - start) * 1000:.2f} ms`")


@app.on_message(filters.command("status") & filters.private)
async def status_command(client, message):
    await message.reply_text(
        f"**Bot Configuration:**\n"
        f"📤 Prefix: `{CUSTOM_PREFIX}`\n"
        f"📥 Source: `{SOURCE_CHANNEL}`\n"
        f"📤 Destination: `{DEST_CHANNEL}`\n"
        f"🖼 Thumbnail: `{THUMBNAIL_URL}`"
    )


@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    await message.reply_text(
        "**Commands:**\n"
        "/start - Check if bot is running\n"
        "/ping - Latency\n"
        "/status - Config info\n"
        "/help - Show this menu"
    )


@app.on_message(filters.private)
async def fallback(client, message):
    await message.reply_text("✅ Bot is online. Use /help to view commands.")


# === MAIN FILE HANDLER ===

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
        log_text = (
            f"✅ **File Processed**\n"
            f"📄 Renamed: `{new_name}`\n"
            f"📥 From: `{SOURCE_CHANNEL}`\n"
            f"📤 To: `{DEST_CHANNEL}`"
        )
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


# === CLEAN STARTUP ===

async def main():
    await app.start()
    try:
        await app.send_message(LOG_CHANNEL or OWNER_ID, "🚀 Bot Started and Monitoring Source Channel.")
    except Exception as e:
        print(f"Startup log failed: {e}")
    print("✅ Bot is running.")
    await asyncio.Event().wait()  # Keep bot alive forever


if __name__ == "__main__":
    asyncio.run(main())
