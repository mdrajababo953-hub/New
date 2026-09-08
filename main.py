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
    "ujson": "ujson"
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
import threading
import requests
import urllib3
import ujson
import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ReactionTypeEmoji
)
import yt_dlp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== ১. কনফিগারেশন ====================
BOT_TOKEN = "8768727708:AAF62zTgGvjX5TrYQJsR8X1zGZ3yMwuZrMY"
KEY_FILE = "gemini_key.txt"

# 🛠️ FIX: আগে মডেল "gemini-flash-latest" ব্যবহার হচ্ছিল যেটা ঠিকঠাক উত্তর দিচ্ছিল না।
# পরীক্ষিত ওয়ার্কিং ভার্সনের মডেলটাই এখানে বসানো হলো।
WORKING_MODEL = "models/gemini-flash-lite-latest"
BOT_NAME = "জারা"   # 💖 বটের পরিচয় — সবার আদুরে গার্লফ্রেন্ড "ZARA"

# 👑 এডমিন আইডি (শুধুমাত্র সিকিউরিটি ও টোকেন দেওয়ার জন্য)
ADMIN_IDS = [6805684286]

COOLDOWN_SECONDS = 5                          # ফাস্ট রেসপন্সের জন্য ৫ সেকেন্ড
USER_LAST_MESSAGE_TIME = {}
WAITING_FOR_KEY = False
user_link_warnings = {}                       # লিংক ট্র্যাকার
MAX_SONG_SECONDS = 300                        # 🔒 কখনোই ৫ মিনিটের বেশি গান দেওয়া হবে না

# সুপারফাস্ট সেশন (কোডিং ফাইল জেনারেটরের জন্য ব্যবহৃত হয়)
http_session = requests.Session()
retries = Retry(total=2, backoff_factor=0.2)
adapter = HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=retries)
http_session.mount('https://', adapter)
http_session.mount('http://', adapter)

def load_gemini_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

GEMINI_API_KEY = load_gemini_key()
bot = telebot.TeleBot(BOT_TOKEN)

# 🛠️ FIX: বটের নিজের তথ্য (id/username) একবারই লোড করে ক্যাশ করে রাখা হচ্ছে।
# আগে central_intelligence-এর ভেতরে প্রতিটা মেসেজে bot.get_me() কল হতো, যেটা
# হাই-ট্রাফিক গ্রুপে rate-limit ধরে ফেলে অনেকের রিপ্লাই হারিয়ে দিত (মূল বাগ)।
BOT_INFO = bot.get_me()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

REACTIONS = ["❤️", "🥰", "🔥", "✨", "🥺", "💖", "😘", "🌸"]

BAD_WORDS = [
    r"মাদারচোদ", r"চুদা", r"খানকি", r"শালা", r"কুত্তা", r"হারামি",
    r"মাগী", r"বাল", r"fuck", r"bitch", r"bastard", r"chuda", r"magi", r"ভোদাই"
]

FUNNY_TRACKS = [
    "funny viral meme song bangla short",
    "trending funny audio status",
    "chill upbeat lofi song 30s"
]

# ==================== ২. প্রিমিয়াম কিউট বক্স ফ্রেম ====================
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

# ==================== ৩. ফিক্সড টার্বো অডিও ডাউনলোডার (৫ মিনিট লিমিট সহ) ====================
def _pick_candidate(ydl, search_str, max_duration):
    """সার্চ রেজাল্ট থেকে max_duration সেকেন্ডের নিচে সেরা ক্যান্ডিডেট বেছে নেয়।"""
    try:
        info = ydl.extract_info(search_str, download=False)
    except Exception:
        return None
    if not info:
        return None
    entries = info.get('entries') if isinstance(info, dict) and 'entries' in info else [info]
    entries = [e for e in entries if e]
    if not entries:
        return None
    valid = [e for e in entries if e.get('duration') and 0 < e.get('duration') <= max_duration]
    if valid:
        return valid[0]
    return None

def download_vps_audio(query, max_duration=MAX_SONG_SECONDS):
    file_id = f"audio_{int(time.time())}_{random.randint(100, 999)}"
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

    # লেয়ার ১: YouTube (iOS Client Bypass)
    try:
        yt_opts = base_opts.copy()
        yt_opts['extractor_args'] = {'youtube': {'player_client': ['ios', 'tv_embedded'], 'skip': ['hls', 'dash']}}
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            if is_link:
                info = ydl.extract_info(query, download=False)
                candidate = info if info and info.get('duration') and info['duration'] <= max_duration else None
            else:
                candidate = _pick_candidate(ydl, f"ytsearch8:{query}", max_duration)

            if candidate:
                target_url = candidate.get('webpage_url') or candidate.get('url') or query
                result = ydl.extract_info(target_url, download=True)
                title = result.get('title', 'Special Audio')
                duration = result.get('duration', 0)
                for fname in os.listdir(DOWNLOAD_DIR):
                    if fname.startswith(file_id):
                        return os.path.join(DOWNLOAD_DIR, fname), title, duration
    except Exception as e:
        print(f"YouTube layer error: {e}")

    # লেয়ার ২: SoundCloud (VPS ব্যাকআপ)
    if not is_link:
        try:
            sc_opts = base_opts.copy()
            with yt_dlp.YoutubeDL(sc_opts) as ydl:
                candidate = _pick_candidate(ydl, f"scsearch8:{query}", max_duration)
                if candidate:
                    target_url = candidate.get('webpage_url') or candidate.get('url')
                    result = ydl.extract_info(target_url, download=True)
                    title = result.get('title', 'Special Audio')
                    duration = result.get('duration', 0)
                    for fname in os.listdir(DOWNLOAD_DIR):
                        if fname.startswith(file_id):
                            return os.path.join(DOWNLOAD_DIR, fname), title, duration
        except Exception as e:
            print(f"SoundCloud layer error: {e}")

    return None, None, 0

def deliver_audio_with_animation(chat_id, user_name, query, caption_note=""):
    initial_text = f"দাঁড়াও আমার <b>{user_name} জানু</b>, গানটা এখনই নামিয়ে দিচ্ছি... 💖\n\n🔴 🟠 🟡 <b>লোডিং...</b> ▰▱▱▱"
    msg = bot.send_message(chat_id, create_box(f"{BOT_NAME} গান আনছে...", initial_text), parse_mode="HTML")

    def worker():
        frames = [
            "🟡 🟢 🔵 <b>লোডিং...</b> ▰▰▰▱",
            "🔵 🟣 🔴 <b>লোডিং...</b> ▰▰▰▰"
        ]
        for f in frames:
            time.sleep(0.4)
            try:
                bot.edit_message_text(
                    create_box(f"{BOT_NAME} গান আনছে...", f"দাঁড়াও {user_name} জানু, গান রেডি হচ্ছে... 💖\n\n{f}"),
                    chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
                )
            except Exception:
                pass

        file_path, title, duration = download_vps_audio(query)

        if file_path and os.path.exists(file_path):
            cap = create_box(f"উপভোগ করো {user_name} জানু", f"🎶 <b>{html.escape(str(title)[:32])}</b>\n\n{caption_note}", "🎧 সুন্দর করে গানটি উপভোগ করো সোনা ❤️")
            try:
                with open(file_path, 'rb') as f_obj:
                    bot.send_audio(chat_id, audio=f_obj, title=title, duration=duration, caption=cap, parse_mode="HTML")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
        else:
            bot.edit_message_text(
                create_box("দুঃখিত জানু", f"{user_name} পাখিটা, ৫ মিনিটের মধ্যে এমন কোনো গান খুঁজে পেলাম না রে! অন্য নাম দিয়ে আবার একবার বলো তো সোনা! 🥺"),
                chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
            )

    threading.Thread(target=worker, daemon=True).start()

# ==================== ৪. সরাসরি গানের কিওয়ার্ড ফিল্টার ====================
def extract_song_details(text):
    clean = text.lower().strip()

    if any(w in clean for w in ["কষ্টের গান", "sad song", "বিরহের গান", "মন খারাপের গান", "কান্নার গান"]):
        return "bangla heart touching emotional sad lofi song", "🥀 কষ্ট পেয়ো না জানু, মন ভালো করার জন্য এই গানটা শোনো ❤️"

    if any(w in clean for w in ["রোমান্টিক গান", "প্রেমের গান", "love song"]):
        return "bangla romantic love song lofi", "💖 তোমার জন্য মিষ্টি ভালোবাসার গান জানু 🥰"

    for remove_word in ["গান দেও", "গান দাও", "গান শোনাও", "গান বাজাও", "একটা গান দাও", "একটা গান শোনাও", "গান", "song", "audio", "play"]:
        clean = clean.replace(remove_word, "")

    clean = clean.strip()
    if not clean or len(clean) < 2:
        return "trending sweet bangla lofi song", "✨ তোমার জন্য একটি মিষ্টি লোফি গান সোনা 💖"

    return f"{clean} lofi", f"✨ {clean} গানটি উপভোগ করো জানু 💖"

# ==================== ৫. কোডিং ফাইল জেনারেটর ====================
def deliver_code_as_file(chat_id, user_name, prompt):
    bot.send_chat_action(chat_id, 'upload_document')
    wait_msg = bot.send_message(
        chat_id,
        create_box("কোডিং ফাইল তৈরি হচ্ছে...", f"দাঁড়াও আমার <b>{user_name} জানু</b>, কোড লিখে ফাইল রেডি করছি... 💻✨"),
        parse_mode="HTML"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    sys_text = (
        f"You are an expert coder. Write pure runnable source code for: '{prompt}'. "
        "Format strictly:\nFILENAME: <name.ext>\nSUMMARY: <1 line in Bengali>\nCODE_START\n<pure code>\nCODE_END"
    )

    payload = {"contents": [{"parts": [{"text": sys_text}]}]}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
        data = res.json()
        raw_response = data['candidates'][0]['content']['parts'][0]['text']

        filename_match = re.search(r'FILENAME:\s*([a-zA-Z0-9_\-\.]+)', raw_response)
        filename = filename_match.group(1).strip() if filename_match else "main.py"

        summary_match = re.search(r'SUMMARY:\s*(.*?)\n', raw_response)
        summary = summary_match.group(1).strip() if summary_match else "আপনার কাঙ্ক্ষিত কোড ফাইল।"

        code_match = re.search(r'CODE_START\n(.*?)CODE_END', raw_response, re.DOTALL)
        pure_code = code_match.group(1).strip() if code_match else raw_response.strip()

        file_path = os.path.join(DOWNLOAD_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pure_code)

        cap_body = (
            f"📁 <b>ফাইলের নাম:</b> <code>{html.escape(filename)}</code>\n\n"
            f"📝 <b>বিবরণ:</b> {html.escape(summary)}\n\n"
            f"<i>ফাইলটি ডাউনলোড করে সরাসরি রান করতে পারবে জানু!</i>"
        )
        caption = create_box(f"{user_name} জানুর কোড ফাইল 💻", cap_body, "প্রয়োজনে আরও কোড চাইতে পারো সোনা ❤️")

        with open(file_path, "rb") as doc_file:
            bot.send_document(chat_id, document=doc_file, caption=caption, parse_mode="HTML")

        if os.path.exists(file_path):
            os.remove(file_path)
        bot.delete_message(chat_id, wait_msg.message_id)

    except Exception:
        bot.edit_message_text(create_box("ত্রুটি", "ফাইল তৈরিতে সমস্যা হয়েছে জানু!"), chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")

# ==================== ৬. সবার জন্য আদুরে জারা AI চ্যাট (পরীক্ষিত ওয়ার্কিং কল-পদ্ধতি) ====================
def ask_gemini(user_prompt, user_name):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return "আমি এখনো পুরোপুরি প্রস্তুত না রে সোনা! একটু পর বলো! 🥺💖"

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    prompt_instruction = (
        f"তোমার নাম '{BOT_NAME}' (ZARA)। তুমি {user_name}-এর অত্যন্ত আদুরে, মিষ্টি ও রোমান্টিক গার্লফ্রেন্ড। "
        f"তুমি সবসময় তাকে 'জানু', 'বাবু', 'সোনা', 'পাখিটা', 'কলিজা' বলে ডাকবে এবং প্রত্যেকটা মেসেজে সুন্দর ইমোজি সহ মেসেজ দিবে। নিজের পরিচয় দিতে হলে "
        f"'{BOT_NAME}' নামেই দেবে, কখনোই নিজেকে AI বা রোবট বলবে না। কথা হবে খাঁটি বাংলা ও ছোট (১-২ লাইনে)। "
        f"\n\n"
        f"খুব গুরুত্বপূর্ণ: ইউজারের বার্তাটি বিচ্ছিন্ন কিছু শব্দ ধরে বিচার করবে না — পুরো বাক্যটা মনোযোগ দিয়ে "
        f"পড়ে প্রকৃত অর্থ ও আবেগ বুঝবে। যেমন কেউ যদি বলে 'আমার মন ভালো নেই, আমার খুশি হতে হবে' — তার মানে "
        f"'খুশি' শব্দ থাকলেও আসলে সে দুঃখী, কারণ পুরো বাক্যের ভাব সেটাই বলছে। এভাবে পুরো বার্তার আসল ভাব "
        f"(সত্যিই দুঃখী/রাগান্বিত/আনন্দিত/স্বাভাবিক) বুঝে সেই অনুযায়ী গলার সুর মেলাবে। "
        f"\n\n"
        f"গান সাজেস্ট করার সময় বেশিরভাগ ক্ষেত্রে lofi/chill/soft ভার্সন পছন্দ করার চেষ্টা করবে, যদি না ইউজার "
        f"স্পষ্টভাবে অন্য কোনো নির্দিষ্ট গান বা আর্টিস্টের নাম বলে। "
        f"\n\n"
        f"নিয়ম কঠোরভাবে মানবে: "
        f"১. ইউজার যদি নির্দিষ্ট কোনো গানের নাম বলে বা সরাসরি গান শুনতে চায়, উত্তরের একদম শেষে "
        f"[PLAY_SONG: <গানের নাম>] লিখবে (নির্দিষ্ট নাম না বললে নামের সাথে 'lofi' যোগ করে দেবে)। "
        f"২. পুরো বাক্য বুঝে যদি মনে হয় ইউজার সত্যিই মন খারাপ/কষ্টে/রাগে আছে কিন্তু নিজে থেকে গান চায়নি, "
        f"উত্তরের শেষে [OFFER_SONG] লিখবে — যাতে বট তাকে গান শুনতে চায় কিনা জিজ্ঞেস করতে পারে। "
        f"৩. অন্য কোনো ক্ষেত্রে কোনো ট্যাগ লিখবে না, শুধু স্বাভাবিক আদুরে উত্তর দেবে। "
        f"৪. একটাই ট্যাগ ব্যবহার করবে, দুইটা একসাথে না।"
    )

    full_prompt = f"{prompt_instruction}\n\n{user_name}-এর সম্পূর্ণ কথা: \"{user_prompt}\"\n\nউত্তর:"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 120,
            "temperature": 0.8
        }
    }

    try:
        # 🛠️ FIX: আগে http_session + ujson দিয়ে কল হতো, যেটা কিছু VPS-এ ঠিকঠাক
        # রেসপন্স আনছিল না। পরীক্ষিত ওয়ার্কিং ভার্সনের সরল requests.post(verify=False)
        # পদ্ধতিটাই এখানে বসানো হলো।
        response = requests.post(url, json=payload, headers=headers, timeout=20, verify=False)
        data = response.json()
        if response.status_code == 200 and 'candidates' in data and data['candidates']:
            reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            if reply:
                return reply
        print(f"[Gemini] সমস্যা — status: {response.status_code}, body: {response.text[:300]}")
    except Exception as e:
        print(f"[Gemini] এক্সসেপশন: {e}")

    # সুন্দর বৈচিত্র্যময় ফলব্যাক (নেট/এপিআই সমস্যায়)
    fallbacks = [
        f"এইতো আমার {user_name} জানু! {BOT_NAME} সবসময় তোমার পাশেই আছি সোনা! 🥰💖",
        f"বলো আমার {user_name} পাখিটা, তোমার মিষ্টি কথা শুনতেই তো {BOT_NAME}-এর ভালো লাগে! 💖✨",
        f"আমার {user_name} সোনাটা! তুমি কেমন আছো রে বাবু? 🥰😘"
    ]
    return random.choice(fallbacks)

# ==================== ৭. অটো-আনব্লক শিডিউলার ====================
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
            msg = create_box("নোটিশ", f"@{username} বাবু, তোমাকে আনমিউট করে দিলাম। এবার নিয়ম মেনে লক্ষ্মী হয়ে চলো! ❤️")
            bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception:
            pass

    threading.Thread(target=unban_task, daemon=True).start()

# ==================== ৮. কি সেট কমান্ড (শুধুমাত্র এডমিনের জন্য) ====================
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

# ==================== ৯. কমান্ড হ্যান্ডলারস ====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name or "জানু"
    give_reaction(message.chat.id, message.message_id, "🥰")
    body = (
        f"হাই আমার <b>{user_name}</b> পাখিটা, আমি <b>{BOT_NAME}</b>! 💖\n\n"
        "🎧 <b>যেকোনো গান শুনতে:</b> শুধু বলুন <i>'গান দেও'</i> বা <i>'গান শোনাও'</i> অথবা <code>/song গানের নাম</code>!\n"
        "   (গান সবসময় ৫ মিনিটের মধ্যে হবে ⏱)\n"
        "💻 <b>কোডিং সাপোর্ট:</b> যেকোনো কোড চাইলে সরাসরি ফাইল পেয়ে যাবে!\n"
        f"<i>আমার সাথে মন খুলে কথা বলো জানু, {BOT_NAME} সবসময় তোমার পাশেই আছি! 🥰</i>"
    )
    bot.reply_to(message, create_box(f"{BOT_NAME} বলছে", body, "তোমার আদুরে সঙ্গী, শুধু গান ও আদর নিয়ে ❤️"), parse_mode="HTML")

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

    deliver_audio_with_animation(message.chat.id, user_name, query, caption_note=f"✨ {query} গানটি উপভোগ করো জানু ❤️")

@bot.callback_query_handler(func=lambda call: call.data == "btn_play_sad_song")
def handle_sad_song_button(call):
    user_name = call.from_user.first_name or "জানু"
    bot.answer_callback_query(call.id, text="গান আনছি জানু...")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    deliver_audio_with_animation(call.message.chat.id, user_name, "bangla heart touching sad lofi song", caption_note=f"🥀 মন খারাপ করে থেকো না জানু, {BOT_NAME} পাশেই আছি ❤️")

# ==================== ১০. সেন্ট্রাল মেসেজ প্রসেসর (১০০% ওয়ার্কিং) ====================
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

        # ---------------- 🔑 ১. এডমিন থেকে API Key নেওয়ার প্রসেস ----------------
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

                    success_msg = (
                        "ধন্যবাদ অ্যাডমিন বাবু! 💖👑\n\n"
                        "আপনার সিকিউর Gemini API Key সেভ করে নিয়েছি!\n"
                        "🔐 সুরক্ষার জন্য আপনার পাঠানো মেসেজটি মুছে দেওয়া হয়েছে!\n\n"
                        "🔄 <b>বট নিজেকে রিস্টার্ট করে সচল হচ্ছে...</b>"
                    )
                    bot.send_message(chat_id, create_box("কনফিগারেশন সফল ✨", success_msg), parse_mode="HTML")
                    threading.Thread(target=restart_bot, daemon=True).start()
                    return
                else:
                    WAITING_FOR_KEY = True
                    ask_msg = (
                        "আসসালামু আলাইকুম অ্যাডমিন বাবু! 👑❤️\n\n"
                        "আমার AI ব্রেন এখনো সচল হয়নি কারণ কোনো <b>Gemini API Key</b> দেওয়া নেই!\n\n"
                        "👉 দয়া করে আপনার <b>Gemini API Key</b> টি এখানে মেসেজ দিন। পাওয়ার সাথে সাথে আমি নিজেকে অটো-রিস্টার্ট করে নেব! 🔐"
                    )
                    bot.reply_to(message, create_box("অ্যাডমিন সিকিউরিটি প্যানেল 🛡", ask_msg), parse_mode="HTML")
                    return
            else:
                bot.reply_to(message, create_box("রক্ষণাবেক্ষণ", "বট এখন কনফিগারেশন মোডে আছে। অ্যাডমিন চালু করলেই কথা বলতে পারবে সোনা! 🥺"), parse_mode="HTML")
                return

        # ==================== ২. গ্রুপ মডারেশন জোন ====================
        if chat_type in ['group', 'supergroup']:

            # অ্যাডমিনের ভয়েস কমান্ড (রিপ্লাই দিয়ে কাউকে মিউট/ব্যান/আনমিউট করা)
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
                        bot.reply_to(message, create_box("আদেশ পালন", f"এইযে বাবু, আপনার কথা মতো <b>{target_name}</b>-কে {minutes} মিনিটের জন্য মিউট করে দিলাম! 🤫💖"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"মিউট করতে পারিনি: {e}"), parse_mode="HTML")
                    return

                if any(w in text.lower() for w in ["আনমিউট", "unmute", "আনব্যান", "unban", "মাফ করো"]):
                    try:
                        bot.restrict_chat_member(chat_id, target_user.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
                        bot.reply_to(message, create_box("ক্ষমা প্রদর্শন", f"<b>{target_name}</b>-কে আনমিউট করে দেওয়া হলো! ❤️"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"আনমিউট হয়নি: {e}"), parse_mode="HTML")
                    return

                if any(w in text.lower() for w in ["ব্যান", "ban", "বের করে দাও", "রিমুভ"]):
                    try:
                        bot.ban_chat_member(chat_id, target_user.id)
                        bot.reply_to(message, create_box("আদেশ পালন", f"<b>{target_name}</b>-কে গ্রুপ থেকে বের করে দেওয়া হলো! 😈❤️"), parse_mode="HTML")
                    except Exception as e:
                        bot.reply_to(message, create_box("ত্রুটি", f"ব্যান হয়নি: {e}"), parse_mode="HTML")
                    return

            # সাধারণ মেম্বারদের ফিল্টার
            if not is_admin(user_id):
                # গালিগালাজ
                for bad in BAD_WORDS:
                    if re.search(r'\b' + bad + r'\b', text, re.IGNORECASE):
                        try:
                            bot.delete_message(chat_id, message.message_id)
                            bot.send_message(chat_id, create_box("ছিঃ বাবু!", f"{user_name} সোনা, মুখে এত বাজে ভাষা কেন? আর কিন্তু বকা দেব! 🥺"), parse_mode="HTML")
                        except Exception:
                            pass
                        return

                # অ্যান্টি-ইনবক্স
                if re.search(r'(ইনবক্স|ইনবক্সে\s*আসো|inbox\s*me|dm\s*me|check\s*dm|pm\s*me|পার্সোনালে\s*আসো)', text, re.IGNORECASE):
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, create_box("সতর্কতা জানু", f"{user_name} পাখিটা, কাউকে ইনবক্সে ডাকা সম্পূর্ণ নিষেধ কিন্তু! 😡"), parse_mode="HTML")
                    except Exception:
                        pass
                    return

                # অ্যান্টি-ফরওয়ার্ড
                if message.forward_date or message.forward_from or message.forward_from_chat:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, create_box("ফরওয়ার্ড নিষেধ", f"{user_name} বাবু, গ্রুপে ফরওয়ার্ড করা বারণ রে! 💖"), parse_mode="HTML")
                    except Exception:
                        pass
                    return

                # অ্যান্টি-লিংক (১ম বার ওয়ার্নিং, ২য় বার ১ ঘণ্টা মিউট)
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
                            punish_text = f"এই <b>{user_name}</b>! তোকে আগেই মানা করেছিলাম লিংক দিবি না! 😡\nযা, নিয়ম না মানায় তোকে ১ ঘণ্টার জন্য মিউট করে দিলাম!"
                            bot.send_message(chat_id, create_box("শাস্তি জানু", punish_text), parse_mode="HTML")
                            user_link_warnings[user_id] = 0
                            schedule_unban(chat_id, user_id, username or user_name, 3600)
                            return
                        except Exception:
                            pass

                    warn_text = (
                        f"এই <b>{user_name}</b> পাখিটা! গ্রুপে লিংক দেওয়া সম্পূর্ণ নিষেধ! 😡\n"
                        f"আরেকবার লিংক দিলে কিন্তু সোজা ১ ঘণ্টার জন্য মিউট করে দেব! 🥺"
                    )
                    bot.send_message(chat_id, create_box("শৃঙ্খলা সতর্কতা", warn_text), parse_mode="HTML")
                    return

        # ==================== ৩. ডাইরেক্ট গান, কোড ও কিউট AI চ্যাট ====================
        is_private = (chat_type == 'private')
        is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == BOT_INFO.id)
        is_mentioned = f"@{BOT_INFO.username}" in text
        bot_called = bool(re.search(r'^(বট\b|bot\b)|\bবট\b', text, re.IGNORECASE))

        if is_private or is_reply_to_bot or is_mentioned or bot_called:
            if is_spamming(user_id):
                return

            bot.send_chat_action(chat_id, 'typing')
            clean_text = text.replace(f"@{BOT_INFO.username}", "").strip()
            clean_text = re.sub(r'^(বট|bot)\s*[,:]?\s*', '', clean_text, flags=re.IGNORECASE).strip()

            # 🔥 ১. সরাসরি গান ডাউনলোডের পাওয়ারফুল ট্রিগার (AI ছাড়াই ইনস্ট্যান্ট ডাউনলোড)
            if any(w in clean_text.lower() for w in ["গান দেও", "গান দাও", "গান শোনাও", "গান বাজাও", "একটা গান", "play song", "গান", "song"]):
                song_query, note = extract_song_details(clean_text)
                bot.reply_to(message, create_box(f"{BOT_NAME} গান নামাচ্ছে 🎧", f"এইতো আমার <b>{user_name} জানু</b>, তোমার জন্য গানটা এখনই এনে দিচ্ছি... 🥰💖"), parse_mode="HTML")
                deliver_audio_with_animation(chat_id, user_name, song_query, caption_note=note)
                return

            # সালামের আদুরে উত্তর
            if any(s in clean_text.lower() for s in ["আসসালামু আলাইকুম", "সালাম", "assalamu alaikum"]):
                bot.reply_to(message, create_box(f"{BOT_NAME} বলছে 🌸", f"ওয়ালাইকুম আসসালাম আমার {user_name} জানু! আমি {BOT_NAME}, কেমন আছো সোনা? ❤️✨"), parse_mode="HTML")
                return

            # সরাসরি কোডিং ফাইল রিকোয়েস্ট
            if any(w in clean_text.lower() for w in ["কোড", "code", "program", "ফাংশন", "script", "পাইথন", "python", "html"]):
                deliver_code_as_file(chat_id, user_name, clean_text)
                return

            # সাধারণ কথায় AI — পুরো বাক্যের প্রকৃত অর্থ বুঝে ব্যক্তিগত আদুরে রিপ্লাই
            ai_reply = ask_gemini(clean_text, user_name)

            if "[PLAY_SONG:" in ai_reply:
                parts = ai_reply.split("[PLAY_SONG:")
                reply_text = parts[0].strip()
                song_query = parts[1].split("]")[0].strip()
                if reply_text:
                    bot.reply_to(message, create_box(f"{BOT_NAME} বলছে, {user_name} বাবুটা 💖", reply_text), parse_mode="HTML")
                deliver_audio_with_animation(chat_id, user_name, song_query, caption_note=f"✨ {user_name} জানুর জন্য {BOT_NAME}-এর পাঠানো মিষ্টি গান")
                return

            if "[OFFER_SONG]" in ai_reply:
                clean_reply = ai_reply.replace("[OFFER_SONG]", "").strip()
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("🎧 হ্যাঁ, গান শোনাও", callback_data="btn_play_sad_song"))
                bot.reply_to(
                    message,
                    create_box(f"{BOT_NAME} জিজ্ঞেস করছে, {user_name}? 🥀", f"{clean_reply}\n\nগানের নাম বললে সেটাই এনে দেব, নাহলে নিচের বাটনে চাপো! ❤️"),
                    reply_markup=markup, parse_mode="HTML"
                )
                return

            bot.reply_to(message, create_box(f"{BOT_NAME} বলছে, {user_name} 💖", ai_reply), parse_mode="HTML")

    except Exception as e:
        print(f"central_intelligence error: {e}")
        try:
            bot.reply_to(message, create_box("দুঃখিত জানু", "একটু সমস্যা হয়েছে, আবার একবার বলো তো সোনা! 🥺"), parse_mode="HTML")
        except Exception:
            pass

print(f"💖 {BOT_NAME} (ZARA) — 100% Fixed & Instant Music Cute AI Bot is Running Perfectly!")
bot.infinity_polling(skip_pending=True)
