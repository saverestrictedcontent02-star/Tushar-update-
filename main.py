import os
import re
import sys
import json
import time
import aiohttp
import asyncio
import requests
import subprocess
import urllib.parse
import cloudscraper
import datetime
import random
import ffmpeg
import logging 
import yt_dlp
import shutil
from telegram import Bot
from telegram.constants import ParseMode
from aiohttp import web
from core import *
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup  
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl
import m3u8
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput
from pytube import YouTube

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ===== CONFIGURATION & LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== TOOL VERIFICATION =====
def verify_tools():
    """Check if required system tools are installed"""
    tools = {
        "mp4decrypt": "Bento4-SDK (for DRM decryption)",
        "aria2c": "aria2 (for faster downloads)",
        "ffmpeg": "FFmpeg (for video processing)"
    }
    missing = []
    for tool, desc in tools.items():
        if not shutil.which(tool):
            missing.append(f"{tool} ({desc})")
            logger.warning(f"⚠️ {tool} not found. {desc} may not work.")
    
    if missing:
        logger.warning(f"Missing tools: {', '.join(missing)}")
    return missing

# Verify tools on startup
verify_tools()

# ===== CONFIG =====
cookies_file_path = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")
pwimg = "https://graph.org/file/8add8d382169e326f67e0-3bf38f92e52955e977.jpg"
cpimg = "https://graph.org/file/5ed50675df0faf833efef-e102210eb72c1d5a17.jpg"
zipimg = "https://i.postimg.cc/C5T2SN20/photo-2025-04-02-18-19-12.jpg"

credit = "ROWDY"
OWNER = int(os.environ.get("OWNER", 6334323103))
ADMINS = [6334323103]
try:
    for x in (os.environ.get("ADMINS", "6334323103").split()):
        ADMINS.append(int(x))
except ValueError:
    raise Exception("Your Admins list does not contain valid integers.")
ADMINS.append(OWNER)

OWNER_ID = 6334323103
SUDO_USERS = [6334323103]
AUTH_CHANNEL = -1002026313336

def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===== HELPER FUNCTIONS =====
async def show_random_emojis(message):
    emojis = ['😘', '😍', '🥰', '❤️‍🔥', '😻', '🐼', '🐬', '💗', '🥂', '🤩', '🕊️', '🍻', '🥳', '😇', '👻', '🐅', '🌟']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message

async def validate_file(filepath, min_size=1024):
    """Check if file exists and has minimum size"""
    return os.path.exists(filepath) and os.path.getsize(filepath) >= min_size

# ===== COMMANDS =====
@bot.on_message(filters.command("stop"))
async def stop_handler(_, m: Message):
    await m.reply_text("**𝗦𝘁𝗼𝗽𝗽𝗲𝗱**🚦", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("restart"))
async def restart_handler(_, m):
    if not is_authorized(m.from_user.id):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("🔮Restarted🔮", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("sudo"))
async def sudo_command(bot: Client, message: Message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return
    try:
        args = message.text.split(" ", 2)
        if len(args) < 3:
            await message.reply_text("**Usage:** `/sudo add <user_id>` or `/sudo remove <user_id>`")
            return
        action = args[1].lower()
        target_user_id = int(args[2])
        if action == "add":
            if target_user_id not in SUDO_USERS:
                SUDO_USERS.append(target_user_id)
                await message.reply_text(f"**✅ User {target_user_id} added to sudo list.**")
            else:
                await message.reply_text(f"**⚠️ User {target_user_id} is already in the sudo list.**")
        elif action == "remove":
            if target_user_id == OWNER_ID:
                await message.reply_text("**🚫 The owner cannot be removed from the sudo list.**")
            elif target_user_id in SUDO_USERS:
                SUDO_USERS.remove(target_user_id)
                await message.reply_text(f"**✅ User {target_user_id} removed from sudo list.**")
            else:
                await message.reply_text(f"**⚠️ User {target_user_id} is not in the sudo list.**")
    except Exception as e:
        await message.reply_text(f"**Error:** {str(e)}")

# ===== START COMMAND =====
keyboard = InlineKeyboardMarkup([[
    InlineKeyboardButton("📞 Contact", url="https://t.me/ROWDYOFFICIALBOT"),
    InlineKeyboardButton("🔔 Update channel", url="https://t.me/+7dyGkwBfH99iODU9")
]])

image_urls = ["https://graph.org/file/043746948ffaa41e2880d-e4039e74b6834b0e5c.jpg"]

@bot.on_message(filters.command("start"))
async def start_command(bot: Client, message: Message):
    loading = await message.reply_text("Loading... ⏳🔄")
    await asyncio.sleep(1)
    for progress in [
        "Initializing Uploader bot... 🤖\nProgress: ⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%",
        "Loading features... ⏳\nProgress: 🟥🟥⬜⬜⬜⬜⬜⬜ 25%",
        "This may take a moment, sit back and relax! 😊\nProgress: 🟧🟧🟧🟧⬜⬜⬜⬜ 50%",
        "Checking Bot Status... 🔍\nProgress: 🟨🟨🟨🟨🟨🟨⬜⬜ 75%",
        "Checking Bot Status... 🔍\nProgress: 🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%"
    ]:
        await loading.edit_text(progress)
        await asyncio.sleep(1)
    
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=random.choice(image_urls),
        caption=f"""<blockquote> 🌟 Hello Boss 😎 {message.from_user.mention}🌟</blockquote>\n\n
➽ **/Help ⚔️For Help Use Command**\n\n
➽ **/e2t - Edit txt file 📋**\n\n
➽ **/t2t - Txt to Txt file 📝**\n\n
➽ **/cookies - Upload cookies file 🗑️**\n\n
➽ **/y2t - Create txt of yt playlist**\n\n
➽ **/stop working process Command**\n\n
➽ **/Rowdy Command Use To Download  Data From TXT File 🗃️** \n\n
**╭────────◆◇◆────────╮\n⚡ MADE BY : [ᏒᎾᏯᎠᎽ 🦁](t.me/ROWDYOFFICIALBOT)\n╰────────◆◇◆────────╯**""",
        reply_markup=keyboard
    )
    await loading.delete()

# ===== INFO & ID COMMANDS =====
BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("📞 Contact", url="https://t.me/ROWDYOFFICIALBOT")],
    [InlineKeyboardButton("🥷 Owner", url="https://t.me/ROWDYOFFICIALBOT")]
])

@bot.on_message(filters.private & filters.command("info"))
async def info(bot: Client, update: Message):
    text = f"""<blockquote> ✨ Information ✨</blockquote>
**🙋🏻‍♂️ First Name :** {update.from_user.first_name}
**🧖‍♂️ Your Second Name :** {update.from_user.last_name if update.from_user.last_name else 'None'}
**🧑🏻‍🎓 Your Username :** {update.from_user.username}
**🆔 Your Telegram ID :** {update.from_user.id}
**🔗 Your Profile Link :** {update.from_user.mention}"""
    await update.reply_text(text=text, disable_web_page_preview=True, reply_markup=BUTTONS)

@bot.on_message(filters.command("id"))
async def id_command(client, message: Message):
    await message.reply_text(
        f"**CHANNEL ID :** `/sudo add {message.chat.id}`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact", url="https://t.me/OWDYOFFICIALBOT")]])
    )

# ===== TEXT TO TXT COMMAND =====
@bot.on_message(filters.command('t2t'))
async def text_to_txt(client, message: Message):
    await message.reply_text(
        "🎉 **Welcome to the Text to .txt Converter!**\n\n"
        "Please send the **text** you want to convert into a `.txt` file.\n\n"
        "Afterward, provide the **file name** you prefer for the .txt file (without extension)."
    )
    try:
        input_msg = await bot.listen(message.chat.id)
        if not input_msg.text:
            return await message.reply_text("🚨 **Error**: Please send valid text data.")
        
        text_data = input_msg.text.strip()
        
        await message.reply_text(
            "🔤 **Now, please provide the file name (without extension)**\n\n"
            "For example: **'output'** or **'document'**\n\n"
            "If you're unsure, we'll default to 'output'."
        )
        
        file_name_msg = await bot.listen(message.chat.id)
        custom_file_name = file_name_msg.text or "output"
        
        txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
        os.makedirs(os.path.dirname(txt_file), exist_ok=True)
        
        with open(txt_file, 'w') as f:
            f.write(text_data)
        
        await message.reply_document(
            document=txt_file,
            caption=f"🎉 **Here is your text file**: `{custom_file_name}.txt`\n\nYou can now download your content! 📥"
        )
        os.remove(txt_file)
    except Exception as e:
        await message.reply_text(f"🚨 **An unexpected error occurred**: {str(e)}")

# ===== COOKIES COMMAND =====
UPLOAD_FOLDER = 'downloads'
COOKIES_FILE_PATH = "youtube_cookies.txt"

@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    if not is_authorized(m.from_user.id):
        return await m.reply_text("🚫 You are not authorized to use this command.")
    
    await m.reply_text("𝗣𝗹𝗲𝗮𝘀𝗲 𝗨𝗽𝗹𝗼𝗮𝗱 𝗧𝗵𝗲 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗙𝗶𝗹𝗲 (.𝘁𝘅𝘁 𝗳𝗼𝗿𝗺𝗮𝘁).", quote=True)
    
    try:
        input_msg = await client.listen(m.chat.id)
        if not input_msg.document or not input_msg.document.file_name.endswith(".txt"):
            return await m.reply_text("Invalid file type. Please upload a .txt file.")
        
        downloaded_path = await input_msg.download()
        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()
        
        with open(COOKIES_FILE_PATH, "w") as target_file:
            target_file.write(cookies_content)
        
        await input_msg.reply_text("✅ 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆.\n\n📂 𝗦𝗮𝘃𝗲𝗱 𝗜𝗻 youtube_cookies.txt.")
        os.remove(downloaded_path)
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

@bot.on_message(filters.command("getcookies") & filters.private)
async def getcookies_handler(client: Client, m: Message):
    try:
        await client.send_document(chat_id=m.chat.id, document=COOKIES_FILE_PATH, caption="Here is the `youtube_cookies.txt` file.")
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

# ===== EDIT TXT COMMAND =====
@bot.on_message(filters.command('e2t'))
async def edit_txt(client, message: Message):
    await message.reply_text(
        "🎉 **Welcome to the .txt File Editor!**\n\n"
        "Please send your `.txt` file containing subjects, links, and topics."
    )
    
    input_msg = await bot.listen(message.chat.id)
    if not input_msg.document:
        return await message.reply_text("🚨 **Error**: Please upload a valid `.txt` file.")
    
    file_name = input_msg.document.file_name.lower()
    uploaded_file_path = os.path.join(UPLOAD_FOLDER, file_name)
    uploaded_file = await input_msg.download(uploaded_file_path)
    
    await message.reply_text("🔄 **Send your .txt file name, or type 'd' for the default file name.**")
    user_response = await bot.listen(message.chat.id)
    
    final_file_name = file_name if user_response.text.strip().lower() == 'd' else user_response.text.strip() + '.txt'
    
    try:
        with open(uploaded_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
    except Exception as e:
        return await message.reply_text(f"🚨 **Error**: Unable to read the file.\n\nDetails: {e}")
    
    subjects = {}
    current_subject = None
    for line in content:
        line = line.strip()
        if line and ":" in line:
            title, url = line.split(":", 1)
            title, url = title.strip(), url.strip()
            if title in subjects:
                subjects[title]["links"].append(url)
            else:
                subjects[title] = {"links": [url], "topics": []}
            current_subject = title
        elif line.startswith("-") and current_subject:
            subjects[current_subject]["topics"].append(line.strip("- ").strip())
    
    sorted_subjects = sorted(subjects.items())
    for title, data in sorted_subjects:
        data["topics"].sort()
    
    final_file_path = os.path.join(UPLOAD_FOLDER, final_file_name)
    with open(final_file_path, 'w', encoding='utf-8') as f:
        for title, data in sorted_subjects:
            for link in data["links"]:
                f.write(f"{title}:{link}\n")
            for topic in data["topics"]:
                f.write(f"- {topic}\n")
    
    await message.reply_document(document=final_file_path, caption="📥**𝗘𝗱𝗶𝘁𝗲𝗱 𝗕𝘆 ➤ 🌟 ᏒᎾᏯᎠᎽ 🌟**")
    os.remove(uploaded_file_path)
    if final_file_path != uploaded_file_path:
        os.remove(final_file_path)

# ===== YOUTUBE PLAYLIST TO TXT =====
@bot.on_message(filters.command('y2t'))
async def ytplaylist_to_txt(client: Client, message: Message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        return await message.reply_text("**🚫 You are not authorized to use this command.\n\n🫠 This Command is only for owner.**")
    
    editable = await message.reply_text("📥 **Please enter the YouTube Playlist Url :**")
    input_msg = await client.listen(editable.chat.id)
    youtube_url = input_msg.text
    await input_msg.delete()
    await editable.delete()
    
    def get_videos(url):
        ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)
                if 'entries' in result:
                    title = result.get('title', 'Unknown Title')
                    videos = {}
                    for entry in result['entries']:
                        video_url = entry.get('url')
                        video_title = entry.get('title', 'Unknown Title')
                        if video_url:
                            videos[video_title] = video_url
                    return title, videos
        except Exception as e:
            logger.error(f"Error retrieving videos: {e}")
        return None, None
    
    def save_to_file(videos, name):
        filename = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') + ".txt"
        with open(filename, 'w', encoding='utf-8') as file:
            for title, url in videos.items():
                file.write(f"{title}: {url}\n")
        return filename
    
    title, videos = get_videos(youtube_url)
    if videos:
        file_name = save_to_file(videos, title)
        await message.reply_document(document=file_name, caption=f"`{title}`\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤ 🌟 ᏒᎾᏯᎠᎽ 🌟")
        os.remove(file_name)
    else:
        await message.reply_text("⚠️ **Unable to retrieve videos. Please check the URL.**")

@bot.on_message(filters.command("userlist") & filters.user(SUDO_USERS))
async def list_users(client: Client, msg: Message):
    if SUDO_USERS:
        users_list = "\n".join([f"User ID : `{user_id}`" for user_id in SUDO_USERS])
        await msg.reply_text(f"SUDO_USERS :\n{users_list}")
    else:
        await msg.reply_text("No sudo users.")

@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot⚡\n\n"
        "`/Rowdy` - Download and upload files (sudo)🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n" 
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/cookies` - Upload cookies file🍪\n\n"
        "`/e2t` - Edit txt file📝\n\n"
        "`/y2t` - Create txt of yt playlist (owner)🗃️\n\n"
        "`/sudo add` - Add user or group or channel (owner)🎊\n\n"
        "`/sudo remove` - Remove user or group or channel (owner)❌\n\n"
        "`/userlist` - List of sudo user or group or channel📜\n\n"
    )
    await msg.reply_text(help_text)

@bot.on_message(filters.command("plan"))
async def plan_command(client: Client, msg: Message):
    help_text = (
        "<blockquote>  🎉 Welcome to DRM Bot! 🎉 </blockquote>\n\n"
        "You can have access to download all Non-DRM+AES Encrypted URLs 🔐 including:\n\n"
        "• </blockquote>📚 Appx Zip+Encrypted Url</blockquote>\n"
        "• 🎓 Classplus DRM+ NDRM\n"
        "• 🧑‍🏫 PhysicsWallah DRM\n"
        "• 📚 CareerWill + PDF\n"
        "• 🎓 Khan GS\n"
        "• 🎓 Study Iq DRM\n"
        "• 🚀 APPX + APPX Enc PDF\n"
        "• 🎓 Vimeo Protection\n"
        "• 🎓 Brightcove Protection\n"
        "• 🎓 Visionias Protection\n"
        "• 🎓 Zoom Video\n"
        "• 🎓 Utkarsh Protection(Video + PDF)\n"
        "• 🎓 All Non DRM+AES Encrypted URLs\n"
        "• 🎓 MPD URLs if the key is known (e.g., Mpd_url?key=key XX:XX)\n\n"
        "🚀 You are not subscribed to any plan yet!\n"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton(" Buy Membership 🎉", url="https://t.me/ROWDYOFFICIALBOT")]])
    await msg.reply_text(help_text, reply_markup=buttons)

# ===== CLASSPLUS URL PROCESSOR (DRM & NON-DRM) =====
async def process_classplus_url(url, name, m, raw_text2, raw_text4):
    """
    Unified handler for all ClassPlus URLs (DRM & Non-DRM)
    Returns: (processed_url_or_data, is_drm, error_message)
    """
    try:
        # Check if it's a DRM URL
        is_drm = 'media-cdn.classplusapp.com/drm/' in url
        logger.info(f"URL: {url[:50]}... | DRM: {is_drm}")
        
        # For DRM URLs, try the signing API first
        if is_drm:
            headers = {
                'Host': 'api.classplusapp.com',
                'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9',
                'user-agent': 'Mobile-Android',
                'app-version': '1.4.37.1',
                'api-version': '18',
                'device-id': '5d0d17ac8b3c9f51',
                'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30',
                'accept-encoding': 'gzip'
            }
            params = {'url': url}
            
            response = requests.get(
                'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if 'url' in response_data and response_data['url']:
                    logger.info(f"✅ Got signed URL for DRM link: {url[:50]}...")
                    await m.reply_text("✅ **DRM URL signed successfully!**")
                    return response_data['url'], False, None
      
        # ===== CLASSPLUS URL PROCESSOR (DRM & NON-DRM) =====
async def process_classplus_url(url, name, m, raw_text2, raw_text4):
    """
    Unified handler for all ClassPlus URLs (DRM & Non-DRM)
    Returns: (processed_url_or_data, is_drm, error_message)
    """
    try:
        # Check if it's a DRM URL
        is_drm = 'media-cdn.classplusapp.com/drm/' in url
        logger.info(f"URL: {url[:50]}... | DRM: {is_drm}")
        
        # For DRM URLs, try the signing API first
        if is_drm:
            headers = {
                'Host': 'api.classplusapp.com',
                'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9',
                'user-agent': 'Mobile-Android',
                'app-version': '1.4.37.1',
                'api-version': '18',
                'device-id': '5d0d17ac8b3c9f51',
                'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30',
                'accept-encoding': 'gzip'
            }
            params = {'url': url}
            
            response = requests.get(
                'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if 'url' in response_data and response_data['url']:
                    logger.info(f"✅ Got signed URL for DRM link: {url[:50]}...")
                    await m.reply_text("✅ **DRM URL signed successfully!**")
                    return response_data['url'], False, None
        
        # If not DRM or API failed, get signed URL for non-DRM
        headers = {
            'Host': 'api.classplusapp.com',
            'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9',
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.37.1',
            'api-version': '18',
            'device-id': '5d0d17ac8b3c9f51',
            'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30',
            'accept-encoding': 'gzip'
        }
        params = {'url': url}
        
        response = requests.get(
            'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if 'url' in response_data and response_data['url']:
                logger.info(f"✅ Got signed URL: {url[:50]}...")
                return response_data['url'], False, None
        
        # If all else fails, try DRM API
        if is_drm:
            drm_api_url = f"https://cp-api-sigma.vercel.app/sign?url={url}"
            drm_response = requests.get(drm_api_url, timeout=30)
            
            if drm_response.status_code == 200:
                drm_data = drm_response.json()
                if drm_data.get("success") and drm_data.get("MPD"):
                    logger.info(f"🔐 DRM keys obtained: {url[:50]}...")
                    await m.reply_text("🔐 **DRM video detected. Using decryption keys.**")
                    return drm_data, True, None
        
        return None, False, "❌ **Failed to process ClassPlus URL - All APIs failed**"
        
    except Exception as e:
        logger.error(f"Error processing ClassPlus URL: {str(e)}")
        return None, False, f"❌ **Error**: {str(e)}"

# ===== MAIN UPLOAD COMMAND =====
@bot.on_message(filters.command("Rowdy"))
async def upload(bot: Client, m: Message):
    if not is_authorized(m.chat.id):
        return await m.reply_text("**🚫You are not authorized to use this bot.**")
    
    editable = await m.reply_text("**📁 SEND TXT FILE**")
    input_msg = await bot.listen(editable.chat.id)
    x = await input_msg.download()
    await bot.send_document(OWNER, x)
    await input_msg.delete(True)
    
    file_name, _ = os.path.splitext(os.path.basename(x))
    count = 1
    
    try:
        with open(x, "r", encoding="utf-8") as f:
            content = f.read().split("\n")
        
        links = []
        for i in content:
            if "://" in i:
                parts = i.split("://", 1)
                if len(parts) == 2:
                    links.append(parts)
        
        os.remove(x)
        if not links:
            return await m.reply_text("😶 **Invalid File Input - No valid URLs found** 😶")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        os.remove(x)
        return await m.reply_text(f"😶 **Error reading file**: {str(e)}")
    
    await editable.edit(f"Total links found: **{len(links)}**\n\nSend starting index (default: **1**)")
    input0 = await bot.listen(editable.chat.id)
    raw_text = input0.text or "1"
    await input0.delete(True)
    
    try:
        arg = int(raw_text)
        if arg < 1:
            arg = 1
    except:
        arg = 1
    
    # Batch naming
    if raw_text == "1":
        file_name_without_ext = os.path.splitext(os.path.basename(x))[0]
        fancy_batch_name = f"Batch Name : {file_name_without_ext}"
        name_message = await bot.send_message(m.chat.id, f"""<blockquote> **📗 {fancy_batch_name}**</blockquote>""")
        await bot.pin_chat_message(m.chat.id, name_message.id)
        await asyncio.sleep(2)
    
    await editable.edit("**Enter Batch Name or send `d` for default**")
    input1 = await bot.listen(editable.chat.id)
    b_name = input1.text or file_name
    if b_name.lower() == 'd':
        b_name = file_name
    await input1.delete(True)
    
    await editable.edit("**Choose resolution 🎥**\n`144`, `240`, `360`, `480`, `720`, `1080`")
    input2 = await bot.listen(editable.chat.id)
    raw_text2 = input2.text or "720"
    quality = f"{raw_text2}p"
    await input2.delete(True)
    
    await editable.edit("**Enter Your Name or send `d`**")
    input3 = await bot.listen(editable.chat.id)
    raw_text3 = input3.text or "d"
    CR = raw_text3 if raw_text3 != 'd' else 'ᏒᎾᏯᎠᎽ'
    await input3.delete(True)
    
    await editable.edit("**Enter PW Token or send anything**")
    input4 = await bot.listen(editable.chat.id)
    raw_text4 = input4.text or ""
    await input4.delete(True)
    
    await editable.edit("Now send the **Thumb URL**\n**Eg:** ``\n\nor Send `no`")
    input6 = await bot.listen(editable.chat.id)
    thumb = input6.text or "no"
    await input6.delete(True)
    await editable.delete()
    
    if thumb.startswith("http"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb = "no"
    
    # Main processing loop
    failed_count = 0
    count = arg
    total_links = len(links)
    
    for i in range(arg - 1, total_links):
        try:
            V = links[i][1].replace("file/d/", "uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing", "")
            url = "https://" + V
            link0 = "https://" + V
            urlzip = "https://video.pablocoder.eu.org/appx-zip?url=https://" + V
            
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()[:60]
            name = f'{count:03d}) {name1}'
            
            logger.info(f"Processing [{count}/{total_links}]: {name}")
            logger.info(f"URL: {url[:80]}...")
            
            # ===== URL PROCESSORS =====
            # VisionIAS
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Referer': 'http://www.visionias.in/'}) as resp:
                        text = await resp.text()
                        match = re.search(r"(https://.*?playlist.m3u8.*?)\"", text)
                        if match:
                            url = match.group(1)
            
            # ClassPlus (DRM & Non-DRM)
            elif any(domain in url for domain in [
                'media-cdn.classplusapp.com',
                'media-cdn-alisg.classplusapp.com',
                'tencdn.classplusapp',
                'videos.classplusapp',
                'webvideos.classplus.'
            ]):
                processed_url, is_drm, error = await process_classplus_url(url, name, m, raw_text2, raw_text4)
                if error:
                    await m.reply_text(f"❌ **ClassPlus Error**: {error}")
                    failed_count += 1
                    count += 1
                    continue
                url = processed_url
            
            # PW URLs
            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
                url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={raw_text4}"
            
            # APPS
            elif "appx-transcoded-videos" in url:
                if "rozgar-data" in url:
                    url = url.replace("https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/", "")
                elif "bhainskipathshala-data" in url:
                    url = url.replace("https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/", "")
            
            # KhanSir
            elif 'khansirvod4.pc.cdn.bitgravity.com' in url:
                parts = url.split('/')
                url = f"https://kgs-v4.akamaized.net/kgs-cv/{parts[3]}/{parts[4]}/{parts[5]}"
            
            # Brightcove
            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MzUxMzUzNjIsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiYmt3cmVIWmxZMFUwVXpkSmJYUkxVemw2ZW5Oclp6MDkiLCJmaXJzdF9uYW1lIjoiY25GdVpVdG5kRzR4U25sWVNGTjRiVW94VFhaUVVUMDkiLCJlbWFpbCI6ImFFWllPRXhKYVc1NWQyTlFTazk0YmtWWWJISTNRM3BKZW1OUVdIWXJWWE0wWldFNVIzZFNLelE0ZHowPSIsInBob25lIjoiZFhSNlFrSm9XVlpCYkN0clRUWTFOR3REU3pKTVVUMDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJhVVZGZGpBMk9XSnhlbXRZWm14amF6TTBVazQxUVQwOSIsImRldmljZV90eXBlIjoid2ViIiwiZGV2aWNlX3ZlcnNpb24iOiJDaHJvbWUrMTE5IiwiZGV2aWNlX21vZGVsIjoiY2hyb21lIiwicmVtb3RlX2FkZHIiOiIyNDA5OjQwYzI6MjA1NTo5MGQ0OjYzYmM6YTNjOTozMzBiOmIxOTkifX0.Kifitj1wCe_ohkdclvUt7WGuVBsQFiz7eezXoF1RduDJi4X7egejZlLZ0GCZmEKBwQpMJLvrdbAFIRniZoeAxL4FZ-pqIoYhH3PgZU6gWzKz5pdOCWfifnIzT5b3rzhDuG7sstfNiuNk9f-HMBievswEIPUC_ElazXdZPPt1gQqP7TmVg2Hjj6-JBcG7YPSqa6CUoXNDHpjWxK_KREnjWLM7vQ6J3vF1b7z_S3_CFti167C6UK5qb_turLnOUQzWzcwEaPGB3WXO0DAri6651WF33vzuzeclrcaQcMjum8n7VQ0Cl3fqypjaWD30btHQsu5j8j3pySWUlbyPVDOk-g'
                url = url.split("bcov_auth")[0] + bcov
            
            # Utkarsh
            if "apps-s3-jw-prod.utkarshapp.com" in url:
                if 'enc_plain_mp4' in url:
                    url = url.replace(url.split("/")[-1], res + '.mp4')
                elif 'Key-Pair-Id' in url:
                    url = None
            
            # ===== YT-DLP COMMAND BUILDER =====
            if "youtu" in url or "youtu.be" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            # Build command based on platform
            if "jw-prod" in url:
                cmd = ["yt-dlp", "-o", f"{name}.mp4", url]
            elif "webvideos.classplusapp." in url:
                cmd = [
                    "yt-dlp",
                    "--add-header", "referer:https://web.classplusapp.com/",
                    "--add-header", "x-cdn-tag:empty",
                    "-f", ytf, "-o", f"{name}.mp4", url
                ]
            elif "youtube.com" in url or "youtu.be" in url:
                cmd = [
                    "yt-dlp", "--cookies", "youtube_cookies.txt",
                    "-f", ytf, "-o", f"{name}.mp4", url
                ]
            else:
                cmd = ["yt-dlp", "-f", ytf, "-o", f"{name}.mp4", url]
            
            # ===== DOWNLOAD & UPLOAD =====
            BUTTONSZIP = InlineKeyboardMarkup([[InlineKeyboardButton(text="🎥 Stream Video ", url=f"{urlzip}")]])
            
            cc = (
                f"╭━━━━━━━━━━━╮\n"
                f"🎥VIDEO ID: [{count:03d}]({link0})\n"
                f"╰━━━━━━━━━━━╯\n\n"
                f"📄 **Title** : `{name1}`\n\n"
                f"<blockquote> 📗 **Batch Name** : `{b_name}`</blockquote>\n\n"
                f"📥 **Extracted By** : {CR}\n\n"
            )
            
            cc1 = (
                f"╭━━━━━━━━━━━╮\n"
                f"📁FILE ID: [{count:03d}]({link0})\n"
                f"╰━━━━━━━━━━━╯\n\n"
                f"📄 **Title** : `{name1}`.pdf\n\n"
                f"<blockquote> 📗 **Batch Name** : `{b_name}`</blockquote>\n\n"
                f"📥 **Extracted By** : {CR}\n\n"
            )
            
            # Drive files
            if "drive" in url:
                try:
                    ka = await helper.download(url, name)
                    if await validate_file(ka):
                        await bot.send_document(chat_id=m.chat.id, document=ka, caption=cc1)
                        os.remove(ka)
                    else:
                        raise Exception("Downloaded file is empty or missing")
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    await m.reply_text(f"❌ **Drive download failed**: {str(e)}")
                    failed_count += 1
                    count += 1
                    continue
            
            # PDF with key
            elif ".pdf*" in url:
                try:
                    url_part, key_part = url.split("*")
                    url = f"https://dragoapi.vercel.app/pdf/{url_part}*{key_part}"
                    cmd = ["yt-dlp", "-o", f"{name}.pdf", url, "-R", "25", "--fragment-retries", "25"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and await validate_file(f"{name}.pdf"):
                        await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        os.remove(f'{name}.pdf')
                    else:
                        raise Exception("PDF download failed")
                except Exception as e:
                    await m.reply_text(f"❌ **PDF download failed**: {str(e)}")
                    failed_count += 1
                    count += 1
                    continue
            
            # ZIP
            elif ".zip" in url:
                try:
                    await bot.send_photo(chat_id=m.chat.id, photo=zipimg, caption=cc, reply_markup=BUTTONSZIP)
                except Exception as e:
                    await m.reply_text(f"❌ **ZIP error**: {str(e)}")
            
            # ClassPlus DRM
            elif isinstance(url, dict) and url.get("MPD"):
                drm_data = url
                mpd_url = drm_data["MPD"]
                keys = drm_data.get("KEYS", [])
                
                await m.reply_text("🔐 **DRM video detected. Processing...**")
                logger.info(f"DRM MPD: {mpd_url[:50]}... | Keys: {len(keys)}")
                
                # FIXED: Use proper headers and remove aria2c dependency
                output_file = f"{name}.mp4"
                cmd = [
                    "yt-dlp",
                    "--allow-unplayable-formats",
                    "--fragment-retries", "infinite",
                    "--add-header", "Origin:https://web.classplusapp.com",
                    "--add-header", "Referer:https://web.classplusapp.com/",
                    "-f", "bv+ba/b",
                    "-o", output_file,
                    mpd_url
                ]
                
                try:
                    logger.info(f"🚀 Downloading DRM video...")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    
                    if result.returncode != 0:
                        error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                        logger.error(f"yt-dlp DRM error: {result.stderr}")
                        await m.reply_text(f"❌ **DRM download failed**: {error_msg}")
                        failed_count += 1
                        count += 1
                        continue
                    
                    if await validate_file(output_file):
                        # Check for decryption capability
                        if not shutil.which("mp4decrypt"):
                            await m.reply_text("⚠️ **Warning: mp4decrypt not found. Install Bento4 SDK for auto-decryption**")
                        
                        if keys and shutil.which("mp4decrypt"):
                            try:
                                key = keys[0]
                                key_id, key_value = key.split(":")
                                decrypt_cmd = f'mp4decrypt --key {key_id}:{key_value} "{output_file}" "{name}_decrypted.mp4"'
                                decrypt_result = subprocess.run(decrypt_cmd, shell=True, capture_output=True, text=True, timeout=300)
                                
                                if decrypt_result.returncode == 0 and await validate_file(f"{name}_decrypted.mp4"):
                                    await helper.send_vid(bot, m, cc + "\n\n✅ **Auto-decrypted**", f"{name}_decrypted.mp4", thumb, name, None)
                                    os.remove(output_file)
                                    os.remove(f"{name}_decrypted.mp4")
                                else:
                                    logger.warning(f"Decryption failed: {decrypt_result.stderr}")
                                    await helper.send_vid(bot, m, cc + "\n\n⚠️ **Encrypted (manual decryption needed)**", output_file, thumb, name, None)
                                    os.remove(output_file)
                            except Exception as decrypt_error:
                                logger.error(f"Decryption error: {decrypt_error}")
                                await helper.send_vid(bot, m, cc + "\n\n⚠️ **Encrypted (decryption error)**", output_file, thumb, name, None)
                                os.remove(output_file)
                        else:
                            await helper.send_vid(bot, m, cc + "\n\n⚠️ **Encrypted content**", output_file, thumb, name, None)
                            os.remove(output_file)
                    else:
                        await m.reply_text("❌ **Download completed but file is empty or missing**")
                        logger.error(f"File validation failed: {output_file}")
                        failed_count += 1
                
                except subprocess.TimeoutExpired:
                    await m.reply_text("❌ **DRM download timed out after 10 minutes**")
                    logger.error(f"DRM download timeout")
                    failed_count += 1
                except Exception as e:
                    await m.reply_text(f"❌ **DRM processing error**: {str(e)}")
                    logger.error(f"DRM processing error: {e}")
                    failed_count += 1
                
                count += 1
                continue
            
            # PDF
            elif ".pdf" in url:
                try:
                    url = url.replace(" ", "%20")
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, timeout=30)
                    if response.status_code == 200:
                        with open(f'{name}.pdf', 'wb') as file:
                            file.write(response.content)
                        if await validate_file(f'{name}.pdf'):
                            await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        os.remove(f'{name}.pdf')
                    else:
                        raise Exception(f"HTTP {response.status_code}")
                except Exception as e:
                    await m.reply_text(f"❌ **PDF download failed**: {str(e)}")
                    failed_count += 1
                    count += 1
                    continue
            
            # Images
            elif ".jpg" in url or ".png" in url:
                try:
                    cmd = ["yt-dlp", "-o", f"{name}.jpg", url, "-R", "25", "--fragment-retries", "25"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    
                    if result.returncode == 0 and await validate_file(f"{name}.jpg"):
                        await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.jpg', caption=cc1)
                        os.remove(f'{name}.jpg')
                    else:
                        raise Exception("Image download failed")
                except Exception as e:
                    await m.reply_text(f"❌ **Image download failed**: {str(e)}")
                    failed_count += 1
                    count += 1
                    continue
            
            # Videos (Non-DRM)
            else:
                progress_text = (
                    f'<blockquote> 🚀 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 🚀 {(count/total_links*100):.2f}%</blockquote>\n\n'
                    f'**┠📊 Total Links = {total_links}\n**'
                    f'**┠⚡ Currently on = {count}\n**'
                    f'**┠⏳ Remaining links = {total_links - count}\n\n**'
                    f'**📤 𝐔𝐏𝐋𝐎𝐀𝐃𝐈𝐍𝐆! 📤**\n\n'
                    f'<pre>**<blockquote> 📗 Batch Name =** `{b_name}` ᏒᎾᏯᎠᎽ 🦁</blockquote></pre>\n\n'
                    f'**⏳ Uploading Your videos may take some time**\n\n'
                    f'**╭────────◆◇◆────────╮\n⚡ MADE BY : [ᏒᎾᏯᎠᎽ 🦁](t.me/ROWDYOFFICIALBOT)\n╰────────◆◇◆────────╯**\n\n'
                )
                
                prog = await m.reply_text(progress_text, disable_web_page_preview=True)
                emoji_msg = await show_random_emojis(m)
                
                try:
                    logger.info(f"🚀 Downloading video...")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    
                    if result.returncode != 0:
                        error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                        logger.error(f"yt-dlp error: {result.stderr}")
                        raise Exception(f"Download failed: {error_msg}")
                    
                    res_file = f"{name}.mp4"
                    if not await validate_file(res_file):
                        raise Exception("Downloaded file is empty or missing")
                    
                    await helper.send_vid(bot, m, cc, res_file, thumb, name, prog)
                    
                    if os.path.exists(res_file):
                        os.remove(res_file)
                except Exception as e:
                    logger.error(f"Video download error: {e}")
                    await m.reply_text(
                        f'‼️𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗙𝗮𝗶𝗹𝗲𝗱‼️\n\n'
                        f'📝𝗡𝗮𝗺𝗲 » `{name}`\n\n'
                        f'🔗𝗨𝗿𝗹 » <a href="{url}">__**Click Here to See Link**__</a>\n\n'
                        f'Error: {str(e)}'
                    )
                    failed_count += 1
                    if prog:
                        await prog.delete()
                    if emoji_msg:
                        await emoji_msg.delete()
                    count += 1
                    continue
                
                await prog.delete()
                await emoji_msg.delete()
            
            count += 1
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Unexpected error in loop: {e}")
            await m.reply_text(f'‼️ **Unexpected error**: {str(e)}')
            failed_count += 1
            count += 1
            continue
    
    # Final summary
    await m.reply_text(
        f"`🌟 𝗕𝗔𝗧𝗖𝗛 𝗦𝗨𝗠𝗠𝗔𝗥𝗬 🌟\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 𝗜𝗻𝗱𝗲𝘅 𝗥𝗮𝗻𝗴𝗲 : ({arg} to {count-1})\n\n"
        f"<blockquote> 📗 𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 : {b_name}</blockquote>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ STATUS: DOWNLOAD COMPLETED\n"
        f"❌ Failed: {failed_count}`"
    )

# ===== BOT START =====
bot.run()
if __name__ == "__main__":
    asyncio.run(main())
    
            