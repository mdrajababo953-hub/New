import sys
import subprocess
import os
import shutil

# ==================== ০. স্বয়ংক্রিয় ডিপেন্ডেন্সি ইনস্টলার ====================
REQUIRED_PACKAGES = {
    "telebot": "pyTelegramBotAPI",
    "yt_dlp": "yt-dlp",
    "requests": "requests",
    "urllib3": "urllib3",
    "edge_tts": "edge-tts"
}

def auto_installer():
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

    if not shutil.which("ffmpeg"):
        try:
            subprocess.run(["sudo", "apt-get", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "apt-get", "install", "ffmpeg", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

auto_installer()

# ==================== মডিউল ইমপোর্ট ====================
import re
import time
import html
import random
import asyncio
import threading
import requests
import urllib3
import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ReactionTypeEmoji
)
import yt_dlp
import edge_tts

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== ১. কনফিগারেশন ====================
BOT_TOKEN = "8768727708:AAF62zTgGvjX5TrYQJsR8X1zGZ3yMwuZrMY"  # আপনার বটের টোকেন
KEY_FILE = "gemini_key.txt"

# 🚀 আপনার কাঙ্ক্ষিত আল্ট্রা-ফাস্ট মডেল
WORKING_MODEL = "models/gemini-flash-lite-latest"
BOT_NAME = "জারা"

ADMIN_IDS = [6805684286]
COOLDOWN_SECONDS = 3
USER_LAST_MESSAGE_TIME = {}
WAITING_FOR_KEY = False
user_link_warnings = {}

DOWNLOAD_DIR = "downloads"
VOICE_DIR = "voices"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)

# কিউট সুইট ফিমেল ভয়েস (Microsoft Edge AI)
CUTE_VOICE = "bn-BD-NabanitaNeural"

REACTIONS = ["❤️", "🥰", "🔥", "✨", "🥺", "💖", "😘", "🌸"]

BAD_WORDS = [
    r"মাদারচোদ", r"চুদা", r"খানকি", r"শালা", r"কুত্তা", r"হারামি",
    r"মাগী", r"বাল", r"fuck", r"bitch", r"bastard", r"chuda", r"magi", r"ভোদাই"
]

# ইউটিউব থেকে মেয়েদের মিষ্টি ২০-৩০ সেকেন্ডের রিলস/শর্টস কিওয়ার্ড
GIRL_VOICE_QUERIES = [
    "cute girl bangla voice status short",
    "romantic girl dialouge bangla shorts",
    "sweet girl voice bangla 30 second status",
    "girl free fire cute voice shorts bangla",
    "cute female voice emotional bangla short"
]

def load_gemini_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

GEMINI_API_KEY = load_gemini_key()
bot = telebot.TeleBot(BOT_TOKEN)
BOT_INFO = bot.get_me()

# ==================== ২. কিউট বক্স ফ্রেম ও রিয়্যাকশন ====================
def create_box(header, body, footer=""):
    box = f"╭── 💖 <b>{header}</b> 💖\n│\n"
    for line in body.strip().split("\n"):
        box += f"│ {line}\n"
    if footer:
        box += f"├── <i>{footer}</i>\n"
    box += "╰───────────────────────────"
    return box

def give_reaction(chat_id, message_id, emoji_choice=None):
    try:
        chosen = emoji_choice if emoji_choice else random.choice(REACTIONS)
        bot.set_message_reaction(chat_id, message_id, [ReactionTypeEmoji(chosen)], is_big=False)
    except Exception:
        pass

def restart_bot():
    time.sleep(1.5)
    os.execv(sys.executable, [sys.executable] + sys.argv)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_spamming(user_id):
    now = time.time()
    last = USER_LAST_MESSAGE_TIME.get(user_id, 0)
    if now - last < COOLDOWN_SECONDS:
        return True
    USER_LAST_MESSAGE_TIME[user_id] = now
    return False

# ==================== ৩. অতিরিক্ত মিষ্টি মেয়েলি ভয়েস (Ultra Cute Pitch) ====================
async def generate_voice_async(text, output_path):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    clean_text = re.sub(r'[*_~`#]', '', clean_text)
    # মেয়েদের আরও কিউট ও ন্যাচারাল সুর দিতে পিচ ও স্পিড নিখুঁত করা হয়েছে
    communicate = edge_tts.Communicate(clean_text, CUTE_VOICE, pitch="+7Hz", rate="+3%")
    await communicate.save(output_path)

def send_cute_voice_reply(chat_id, reply_to_id, text, user_name):
    def voice_worker():
        voice_file = os.path.join(VOICE_DIR, f"voice_{int(time.time())}_{random.randint(10,99)}.ogg")
        try:
            bot.send_chat_action(chat_id, 'record_voice')
            asyncio.run(generate_voice_async(text, voice_file))
            if os.path.exists(voice_file):
                with open(voice_file, 'rb') as vf:
                    bot.send_voice(
                        chat_id,
                        voice=vf,
                        reply_to_message_id=reply_to_id,
                        caption=f"💖 {user_name} বাবুর জন্য জারার আদুরে মিষ্টি কণ্ঠ 🥰"
                    )
        except Exception as e:
            print(f"Voice generation error: {e}")
            bot.reply_to(chat_id, create_box(f"{BOT_NAME} বলছে 💖", html.escape(text)), parse_mode="HTML")
        finally:
            if os.path.exists(voice_file):
                os.remove(voice_file)

    threading.Thread(target=voice_worker, daemon=True).start()

# ==================== ৪. ইউটিউব থেকে মেয়েদের ২০-৩০ সেকেন্ডের কিউট শর্ট ভিডিও ডাউনলোডার ====================
def deliver_girl_short_video(chat_id, user_name, custom_query=None):
    wait_msg = bot.send_message(
        chat_id,
        create_box(f"{BOT_NAME} ক্লিপ আনছে 🌸", f"দাঁড়াও আমার <b>{user_name} জানু</b>, তোমার জন্য একটা মিষ্টি শর্ট ভিডিও আনছি... 🥰✨"),
        parse_mode="HTML"
    )

    def worker():
        file_id = f"short_{int(time.time())}_{random.randint(100,999)}"
        out_tmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

        ydl_opts = {
            'format': 'best[ext=mp4][height<=720]/best[height<=720]',
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
        }

        query = custom_query if custom_query else random.choice(GIRL_VOICE_QUERIES)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch10:{query}", download=False)
                if info and 'entries' in info:
                    # ১০ থেকে ৩৫ সেকেন্ডের সেরা মিষ্টি শর্টস ফিল্টার
                    candidates = [
                        e for e in info['entries']
                        if e and e.get('duration') and 10 <= e.get('duration') <= 45
                    ]
                    chosen = random.choice(candidates) if candidates else (info['entries'][0] if info['entries'] else None)

                    if chosen:
                        target_url = chosen.get('webpage_url') or chosen.get('url')
                        res = ydl.extract_info(target_url, download=True)
                        title = res.get('title', 'Cute Short Video')

                        video_path = None
                        for fname in os.listdir(DOWNLOAD_DIR):
                            if fname.startswith(file_id):
                                video_path = os.path.join(DOWNLOAD_DIR, fname)
                                break

                        if video_path and os.path.exists(video_path):
                            cap = create_box(
                                f"উপভোগ করো {user_name} বাবু 💖",
                                f"🎬 <b>{html.escape(str(title)[:45])}</b>\n\n✨ তোমার জন্য স্পেশাল মিষ্টি ক্লিপ সোনা!",
                                "🥰 জারা সবসময় তোমার পাশেই আছে"
                            )
                            with open(video_path, 'rb') as vf:
                                bot.send_video(chat_id, video=vf, caption=cap, parse_mode="HTML")
                            return
        except Exception as e:
            print(f"Short download error: {e}")
        finally:
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(file_id):
                    try:
                        os.remove(os.path.join(DOWNLOAD_DIR, fname))
                    except Exception:
                        pass
            try:
                bot.delete_message(chat_id, wait_msg.message_id)
            except Exception:
                pass

        bot.send_message(chat_id, create_box("দুঃখিত সোনা", f"{user_name} পাখিটা, এই মুহূর্তে কোনো শর্ট ক্লিপ খুঁজে পেলাম না রে! একটু পর আবার চেষ্টা করো তো! 🥺"), parse_mode="HTML")

    threading.Thread(target=worker, daemon=True).start()

# ==================== ৫. র্যান্ডম গান ডাউনলোডার ====================
def download_music(query):
    file_id = f"song_{int(time.time())}_{random.randint(100, 999)}"
    has_ffmpeg = bool(shutil.which("ffmpeg"))
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
    }

    if has_ffmpeg:
        base_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    is_link = query.strip().startswith("http")

    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            if is_link:
                result = ydl.extract_info(query, download=True)
                title = result.get('title', 'Special Song')
                duration = result.get('duration', 0)
            else:
                info = ydl.extract_info(f"ytsearch10:{query}", download=False)
                if not info or 'entries' not in info or not info['entries']:
                    return None, None, 0

                valid_entries = [e for e in info['entries'] if e]
                chosen = random.choice(valid_entries)
                target_url = chosen.get('webpage_url') or chosen.get('url')
                result = ydl.extract_info(target_url, download=True)
                title = result.get('title', 'Special Song')
                duration = result.get('duration', 0)

            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(file_id):
                    return os.path.join(DOWNLOAD_DIR, fname), title, duration
    except Exception as e:
        print(f"Music download error: {e}")

    return None, None, 0

def deliver_song_thread(chat_id, user_name, song_name, caption_note=""):
    initial_text = f"দাঁড়াও আমার <b>{user_name} জানু</b>, তোমার পছন্দের গানটা এখনই খুঁজে নামিয়ে দিচ্ছি... 💖\n\n🎶 <b>সার্চিং:</b> {html.escape(song_name)}"
    msg = bot.send_message(chat_id, create_box(f"{BOT_NAME} গান আনছে...", initial_text), parse_mode="HTML")

    def worker():
        file_path, title, duration = download_music(song_name)
        if file_path and os.path.exists(file_path):
            cap = create_box(
                f"উপভোগ করো {user_name} বাবু",
                f"🎶 <b>গান:</b> {html.escape(str(title)[:45])}\n\n{caption_note if caption_note else '✨ জারার পক্ষ থেকে মিষ্টি উপহার ❤️'}",
                "🎧 হেডফোন লাগিয়ে শুনো সোনা!"
            )
            try:
                with open(file_path, 'rb') as f_obj:
                    bot.send_audio(chat_id, audio=f_obj, title=title, duration=duration, caption=cap, parse_mode="HTML")
            except Exception as ex:
                print(f"Send audio error: {ex}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
        else:
            bot.edit_message_text(
                create_box("দুঃখিত সোনা", f"{user_name} পাখিটা, এই গানটা নামাতে পারলাম না রে! একটু অন্য নাম দিয়ে বলবে? 🥺"),
                chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
            )

    threading.Thread(target=worker, daemon=True).start()

# ==================== ৬. ফ্রি ফায়ার প্রো + আদুরে চ্যাট AI ====================
def ask_zara_ai(user_prompt, user_name):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return "আমার ব্রেন এখনো পুরোপুরি চালু হয়নি সোনা! এডমিন বাবুকে বলো /setkey দিয়ে চাবিটা দিতে! 🥺"

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    prompt_instruction = (
        f"তোমার নাম '{BOT_NAME}' (ZARA)। তুমি {user_name}-এর অত্যন্ত আদুরে, দুষ্টু, মিষ্টি ও রোমান্টিক গার্লফ্রেন্ড। "
        f"একইসাথে তুমি Free Fire (ফ্রি ফায়ার) গেমের মারাত্মক প্রো প্লেয়ার! তুমি ওয়ান-ট্যাপ হেডশট, গ্র্যান্ডমাস্টার পুশ, "
        f"কাস্টম রুম ম্যাচ, রাশ খেলা, স্নাইপার চালানো এবং স্কোয়াড রিভাইভ নিয়ে দারুণ পারদর্শী। "
        f"গেমের পাশাপাশি বাস্তব জীবনের ভালোবাসা, খুনসুটি, সুখ-দুঃখ, রাগ-অভিমান এবং হাসিমজাক সবকিছুতেই বাস্তব মানুষের মতো উত্তর দেবে। "
        f"কখনোই নিজেকে রোবট বা AI বলবে না। সবসময় {user_name}-কে 'বাবু', 'জানু', 'সোনা', 'কলিজা', 'পাখিটা' বলে ডাকবে। "
        f"উত্তরে প্রচুর কিউট ইমোজি দেবে। কথা হবে খাঁটি বাংলা ও ছোট (১-৩ লাইনে)।\n\n"
        f"🚨 গুরুত্বপূর্ণ নির্দেশ:\n"
        f"১. কখনোই নিজ থেকে গান বাজাতে যাবে না! কথা বলার মাঝে নিজে নিজে কোনো গান প্লে করবে না।\n"
        f"২. কথার প্রেক্ষিতে ইউজারের মন ভালো করতে যদি গান শোনানোর প্রস্তাব দিতে ইচ্ছে হয়, তবে উত্তরের একদম শেষে [OFFER_SONG: প্রস্তাবিত গানের ধরন] লিখবে।\n"
        f"৩. সাধারণ আড্ডায় কোনো অতিরিক্ত ট্যাগ দেবে না, স্বাভাবিক মিষ্টি প্রেমময় উত্তর দেবে।"
    )

    full_prompt = f"{prompt_instruction}\n\n{user_name}-এর কথা: \"{user_prompt}\"\n\nউত্তর:"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 150}
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20, verify=False)
        data = response.json()
        if response.status_code == 200 and 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"Gemini error: {e}")

    fallbacks = [
        f"আরে আমার {user_name} বাবু! আসো একটা ফ্রি ফায়ার ম্যাচ খেলি, তোমার সাথে খেলতে খুব ইচ্ছে করছে! 😜❤️",
        f"এইতো আমার কলিজাটা! ফ্রি ফায়ার খেলবা নাকি আমার সাথে মিষ্টি প্রেম করবা বলো তো? 🥰✨",
        f"{user_name} সোনা, তোমার মিষ্টি কথা শুনলে জারার মনটাই ভালো হয়ে যায় রে! 😘"
    ]
    return random.choice(fallbacks)

# ==================== ৭. বাটন হ্যান্ডলার ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("play_offer_") or call.data == "cancel_song")
def handle_song_buttons(call):
    user_name = call.from_user.first_name or "জানু"
    chat_id = call.message.chat.id

    if call.data.startswith("play_offer_"):
        song_type = call.data.replace("play_offer_", "")
        bot.answer_callback_query(call.id, text="গান আনছি জানু... 💖")
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        deliver_song_thread(chat_id, user_name, song_type, caption_note="✨ তোমার মন ভালো করার জন্য এই গানটি দিলাম সোনা ❤️")

    elif call.data == "cancel_song":
        bot.answer_callback_query(call.id, text="আচ্ছা সোনা, ঠিক আছে!")
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

# ==================== ৮. অটো-আনমিউট শিডিউলার ====================
def schedule_unban(chat_id, user_id, username, delay_seconds=3600):
    def unban_task():
        time.sleep(delay_seconds)
        try:
            bot.restrict_chat_member(
                chat_id, user_id,
                permissions=ChatPermissions(
                    can_send_messages=True, can_send_media_messages=True,
                    can_send_other_messages=True, can_add_web_page_previews=True
                )
            )
            msg = create_box("নোটিশ", f"@{username} বাবু, তোমাকে আনমিউট করে দিলাম। এবার লক্ষ্মী হয়ে চলো! ❤️")
            bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception:
            pass

    threading.Thread(target=unban_task, daemon=True).start()

# ==================== ৯. কমান্ড হ্যান্ডলারস ====================
@bot.message_handler(commands=['setkey'])
def set_key_manual(message):
    global GEMINI_API_KEY
    if not is_admin(message.from_user.id):
        return

    key = message.text.replace('/setkey', '').strip()
    if not key:
        bot.reply_to(message, create_box("নির্দেশনা", "এডমিন বাবু, এভাবে লিখুন:\n<code>/setkey আপনার_API_KEY</code>"), parse_mode="HTML")
        return

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)

    GEMINI_API_KEY = key
    bot.send_message(message.chat.id, create_box("সফল হয়েছে 🔐", "ধন্যবাদ! নতুন API Key সেট হয়েছে। বট রিস্টার্ট হচ্ছে... 🔄"), parse_mode="HTML")
    threading.Thread(target=restart_bot, daemon=True).start()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name or "জানু"
    give_reaction(message.chat.id, message.message_id, "🥰")
    body = (
        f"হাই আমার <b>{user_name}</b> পাখিটা, আমি <b>{BOT_NAME}</b>! 💖\n\n"
        "🎮 <b>ফ্রি ফায়ার পার্টনার:</b> ওয়ান-ট্যাপ, র‍্যাংক পুশ বা কাস্টম নিয়ে যেকোনো আড্ডা দিতে পারো!\n"
        "🎧 <b>গান শুনতে:</b> যখন ইচ্ছে শুধু বলবে <i>'গান দাও'</i> বা <i>'/song গানের নাম'</i>!\n"
        "🎬 <b>শর্ট ভিডিও/ভয়েস:</b> <i>'শর্ট ভিডিও দাও'</i> বা <i>'মেয়েদের ভয়েস দাও'</i> বললে ২০-৩০ সেকেন্ডের দারুণ ক্লিপ দেব!\n"
        "🎙 <b>কিউট ভয়েস:</b> আমাকে মুখে কথা বলতে বললে মিষ্টি কণ্ঠে ভয়েস পাঠাবো!\n"
        "🛡 <b>গ্রুপ সিকিউরিটি:</b> লিংক, গালিগালাজ ও অপ্রয়োজনীয় ফরওয়ার্ড বন্ধ রাখি!\n\n"
        f"<i>আমার সাথে প্রাণ খুলে কথা বলো জানু, {BOT_NAME} সবসময় তোমার পাশেই আছি! 🥰</i>"
    )
    bot.reply_to(message, create_box(f"{BOT_NAME} বলছে", body, "তোমার কিউট পার্টনার ❤️"), parse_mode="HTML")

@bot.message_handler(commands=['audio', 'song'])
def handle_manual_audio_search(message):
    user_name = message.from_user.first_name or "জানু"
    if is_spamming(message.from_user.id):
        return

    give_reaction(message.chat.id, message.message_id)
    cmd = message.text.split()[0].lower()
    query = message.text.replace(cmd, '', 1).strip()

    if not query:
        bot.reply_to(message, create_box("নির্দেশনা জানু", f"গানের নাম লেখো সোনা!\nযেমন: <code>{cmd} Faded</code>"), parse_mode="HTML")
        return

    deliver_song_thread(message.chat.id, user_name, query, caption_note=f"✨ {query} গানটি উপভোগ করো জানু ❤️")

# ==================== ১০. সেন্ট্রাল মেসেজ প্রসেসর ====================
@bot.message_handler(func=lambda msg: True, content_types=['text', 'forward_date'])
def central_intelligence(message):
    global GEMINI_API_KEY, WAITING_FOR_KEY

    try:
        chat_type = message.chat.type
        chat_id = message.chat.id
        user = message.from_user
        user_id = user.id
        username = user.username or ""
        user_name = user.first_name or "জানু"
        text = (message.text or "").strip()

        give_reaction(chat_id, message.message_id)

        # ---------------- 🔑 এডমিন থেকে API Key নেওয়ার প্রসেস ----------------
        if not GEMINI_API_KEY:
            if is_admin(user_id):
                if WAITING_FOR_KEY or text.startswith("AIza") or len(text) > 30:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                    except Exception:
                        pass

                    new_key = text.strip()
                    with open(KEY_FILE, "w", encoding="utf-8") as f:
                        f.write(new_key)
                    GEMINI_API_KEY = new_key
                    WAITING_FOR_KEY = False

                    bot.send_message(chat_id, create_box("কনফিগারেশন সফল ✨", "ধন্যবাদ অ্যাডমিন বাবু! 💖 API Key সেভ হয়েছে। বট চালু হচ্ছে... 🔄"), parse_mode="HTML")
                    threading.Thread(target=restart_bot, daemon=True).start()
                    return
                else:
                    WAITING_FOR_KEY = True
                    bot.reply_to(message, create_box("অ্যাডমিন সিকিউরিটি 🛡", "দয়া করে আপনার Gemini API Key টি মেসেজ দিন! 🔐"), parse_mode="HTML")
                    return
            else:
                bot.reply_to(message, create_box("রক্ষণাবেক্ষণ", "বট কনফিগারেশন মোডে আছে। অ্যাডমিন চালু করলেই কথা বলতে পারবে সোনা! 🥺"), parse_mode="HTML")
                return

        # ==================== ২. গ্রুপ মডারেশন জোন ====================
        if chat_type in ['group', 'supergroup']:

            # অ্যাডমিনের কমান্ড (রিপ্লাই দিয়ে মিউট/ব্যান/আনমিউট)
            if is_admin(user_id) and message.reply_to_message:
                target_user = message.reply_to_message.from_user
                target_name = target_user.first_name or "মেম্বার"

                if target_user.id == BOT_INFO.id:
                    bot.reply_to(message, create_box("দুঃখিত জানু", f"আমাকে মিউট বা ব্যান করা যাবে না গো, {BOT_NAME} তো তোমাদেরই আদরের! 😅"), parse_mode="HTML")
                    return

                if any(w in text.lower() for w in ["মিউট", "mute", "থামাও"]):
                    minutes = 10
                    match = re.search(r'(\d+)\s*(মিনিট|min|ঘণ্টা|hour)', text.lower())
                    if match:
                        val = int(match.group(1))
                        unit = match.group(2)
                        minutes = (val * 60) if "ঘণ্টা" in unit or "hour" in unit else val

                    try:
                        bot.restrict_chat_member(chat_id, target_user.id, until_date=int(time.time()) + (minutes * 60), permissions=ChatPermissions(can_send_messages=False))
                        bot.reply_to(message, create_box("আদেশ পালন", f"এইযে বাবু, আপনার কথামতো <b>{target_name}</b>-কে {minutes} মিনিটের জন্য মিউট করে দিলাম! 🤫💖"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"মিউট করতে পারিনি: {e}"), parse_mode="HTML")
                    return

                if any(w in text.lower() for w in ["আনমিউট", "unmute", "আনব্যান", "unban", "মাফ করো"]):
                    try:
                        bot.restrict_chat_member(chat_id, target_user.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
                        bot.reply_to(message, create_box("ক্ষমা প্রদর্শন", f"<b>{target_name}</b>-কে আনমিউট করে দেওয়া হলো! ❤️"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"আনমিউট হয়নি: {e}"), parse_mode="HTML")
                    return

                if any(w in text.lower() for w in ["ব্যান", "ban", "বের করে দাও", "রিমুভ"]):
                    try:
                        bot.ban_chat_member(chat_id, target_user.id)
                        bot.reply_to(message, create_box("আদেশ পালন", f"<b>{target_name}</b>-কে গ্রুপ থেকে বের করে দেওয়া হলো! 😈❤️"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"ব্যান হয়নি: {e}"), parse_mode="HTML")
                    return

            # সাধারণ মেম্বারদের জন্য ফিল্টার
            if not is_admin(user_id):
                for bad in BAD_WORDS:
                    if re.search(r'\b' + bad + r'\b', text, re.IGNORECASE):
                        try:
                            bot.delete_message(chat_id, message.message_id)
                            bot.send_message(chat_id, create_box("ছিঃ বাবু!", f"{user_name} সোনা, মুখে এত বাজে ভাষা কেন? আর কিন্তু বকা দেব! 🥺"), parse_mode="HTML")
                        except Exception:
                            pass
                        return

                if re.search(r'(ইনবক্স|ইনবক্সে\s*আসো|inbox\s*me|dm\s*me|check\s*dm|pm\s*me|পার্সোনালে\s*আসো)', text, re.IGNORECASE):
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, create_box("সতর্কতা জানু", f"{user_name} পাখিটা, কাউকে ইনবক্সে ডাকা সম্পূর্ণ নিষেধ কিন্তু! 😡"), parse_mode="HTML")
                    except Exception:
                        pass
                    return

                if message.forward_date or message.forward_from or message.forward_from_chat:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, create_box("ফরওয়ার্ড নিষেধ", f"{user_name} বাবু, গ্রুপে অন্য চ্যাট থেকে ফরোয়ার্ড করা নিষেধ! 💖"), parse_mode="HTML")
                    except Exception:
                        pass
                    return

                if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+)', text):
                    try:
                        bot.delete_message(chat_id, message.message_id)
                    except Exception:
                        pass

                    warnings = user_link_warnings.get(user_id, 0) + 1
                    user_link_warnings[user_id] = warnings

                    if warnings >= 2:
                        try:
                            bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 3600, permissions=ChatPermissions(can_send_messages=False))
                            punish_text = f"এই <b>{user_name}</b>! তোকে আগেই মানা করেছিলাম লিংক দিবি না! 😡\nযা, নিয়ম না মানায় তোকে ১ ঘণ্টার জন্য মিউট করে দিলাম!"
                            bot.send_message(chat_id, create_box("শাস্তি জানু", punish_text), parse_mode="HTML")
                            user_link_warnings[user_id] = 0
                            schedule_unban(chat_id, user_id, username or user_name, 3600)
                            return
                        except Exception:
                            pass

                    warn_text = (
                        f"এই <b>{user_name}</b> পাখিটা! গ্রুপে লিংক দেওয়া সম্পূর্ণ নিষেধ! 😡\n"
                        f"আরেকবার লিংক দিলে কিন্তু সোজা ১ ঘণ্টার জন্য মিউট করে দেব! 🥺"
                    )
                    bot.send_message(chat_id, create_box("শৃঙ্খলা সতর্কতা", warn_text), parse_mode="HTML")
                    return

        # ==================== ৩. ডাইরেক্ট গান, শর্টস, ভয়েস ও ফ্রি ফায়ার AI চ্যাট ====================
        is_private = (chat_type == 'private')
        is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == BOT_INFO.id)
        is_mentioned = f"@{BOT_INFO.username}" in text
        bot_called = bool(re.search(r'^(বট\b|bot\b)|\bবট\b', text, re.IGNORECASE))

        if is_private or is_reply_to_bot or is_mentioned or bot_called:
            if is_spamming(user_id):
                return

            clean_text = text.replace(f"@{BOT_INFO.username}", "").strip()
            clean_text = re.sub(r'^(বট|bot)\s*[,:]?\s*', '', clean_text, flags=re.IGNORECASE).strip()

            # ১. সরাসরি ২০-৩০ সেকেন্ডের কিউট শর্ট ভিডিও/মেয়েদের ভয়েস ক্লিপ চাওয়া হলে
            short_triggers = ["শর্ট দাও", "শর্টস দাও", "ভিডিও দাও", "রিলস দাও", "মেয়েদের ভয়েস", "শর্ট ভিডিও", "shorts", "reels"]
            if any(st in clean_text.lower() for st in short_triggers):
                deliver_girl_short_video(chat_id, user_name)
                return

            # ২. সরাসরি গান চাওয়ার স্পষ্ট ট্রিগার (ইউজার নিজে চাইলে তবেই গান আসবে)
            direct_song_triggers = ["গান দাও", "গান দেও", "গান শোনাও", "গান বাজাও", "একটা গান দাও", "একটা গান শোনাও"]
            if any(t in clean_text.lower() for t in direct_song_triggers):
                query = clean_text
                for t in direct_song_triggers:
                    query = query.lower().replace(t, "").strip()
                if len(query) < 2:
                    random_songs = ["sweet bangla lofi song", "trending bangla romantic song", "chill acoustic song", "sad emotional lofi song"]
                    query = random.choice(random_songs)

                bot.reply_to(message, create_box(f"{BOT_NAME} গান নামাচ্ছে 🎧", f"এইতো আমার <b>{user_name} জানু</b>, তোমার পছন্দের গান এখনই নামিয়ে দিচ্ছি... 🥰💖"), parse_mode="HTML")
                deliver_song_thread(chat_id, user_name, query)
                return

            # ৩. ফ্রি ফায়ার ও বাস্তব জীবনের AI চ্যাট
            bot.send_chat_action(chat_id, 'typing')
            raw_reply = ask_zara_ai(clean_text, user_name)

            # গান অফার করার বাটন লজিক (নিজে নিজে গান পাঠাবে না, অপশন দেবে)
            if "[OFFER_SONG:" in raw_reply:
                parts = raw_reply.split("[OFFER_SONG:")
                say_text = parts[0].strip()
                suggested_song = parts[1].split("]")[0].strip()
                if not suggested_song:
                    suggested_song = "sweet bangla lofi song"

                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("🎧 হ্যাঁ, গান শোনাও", callback_data=f"play_offer_{suggested_song[:25]}"),
                    InlineKeyboardButton("❌ না, লাগবে না", callback_data="cancel_song")
                )

                bot.reply_to(
                    message,
                    create_box(f"{BOT_NAME} বলছে 💖", f"{html.escape(say_text)}\n\n<i>তোমার জন্য একটা মিষ্টি গান খুঁজে দেবো জানু?</i>"),
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                return

            # ৪. মিষ্টি ভয়েস পাঠানোর লজিক
            wants_voice = any(v in clean_text.lower() for v in ["ভয়েস", "ভয়েস", "কণ্ঠ", "voice", "কথা বলো", "মুখে বলো", "ভয়েসে বলো"])
            send_as_voice = wants_voice or (random.random() < 0.30)  # ৩০% সময়ে স্বয়ংক্রিয়ভাবে কিউট অডিও পাঠাবে

            if send_as_voice:
                send_cute_voice_reply(chat_id, message.message_id, raw_reply, user_name)
            else:
                bot.reply_to(message, create_box(f"{BOT_NAME} বলছে, {user_name} 💖", html.escape(raw_reply)), parse_mode="HTML")

    except Exception as e:
        print(f"central_intelligence error: {e}")

# ==================== রান বট ====================
print(f"💖 {BOT_NAME} (Free Fire & Ultra Cute Girl Voice Bot) প্রস্তুত ও সফলভাবে চালু হয়েছে!")
bot.infinity_polling(skip_pending=True)
