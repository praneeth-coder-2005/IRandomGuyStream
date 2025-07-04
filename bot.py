import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from settings import API_ID, API_HASH, BOT_TOKEN, SOURCE_CHANNEL, DEST_CHANNEL, CUSTOM_PREFIX, THUMBNAIL_URL


app = Client("auto_renamer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def human_readable(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024


async def progress_bar(current, total, message, stage):
    percent = current * 100 / total
    bar = f"[{'=' * int(percent / 5)}{' ' * (20 - int(percent / 5))}]"
    await message.edit_text(f"**{stage}**\n{bar} {percent:.2f}%\n\n{human_readable(current)} of {human_readable(total)}")


def download_thumbnail(url: str) -> str:
    response = requests.get(url)
    filename = "temp_thumb.jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename


@app.on_message(filters.channel & filters.chat(SOURCE_CHANNEL) & (filters.video | filters.document))
async def handle_file(client: Client, message: Message):
    media = message.video or message.document
    original_name = media.file_name or f"file_{int(time.time())}"
    file_ext = os.path.splitext(original_name)[1]
    new_name = f"{CUSTOM_PREFIX}{int(time.time())}{file_ext}"

    progress_msg = await message.reply_text("📥 Starting download...")

    download_path = await app.download_media(
        message=message,
        file_name=new_name,
        progress=progress_bar,
        progress_args=(progress_msg, "Downloading")
    )

    await progress_msg.edit_text("✅ Download complete.\n📤 Uploading...")

    thumb_path = download_thumbnail(THUMBNAIL_URL)

    sent_msg = await app.send_document(
        chat_id=DEST_CHANNEL,
        document=download_path,
        file_name=new_name,
        thumb=thumb_path,
        caption=f"`{new_name}`",
        progress=progress_bar,
        progress_args=(progress_msg, "Uploading")
    )

    await progress_msg.edit_text("✅ Upload complete. Cleaning up...")
    os.remove(download_path)
    os.remove(thumb_path)
    await message.delete()
    await progress_msg.delete()

app.run()
