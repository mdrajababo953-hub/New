import sys
import subprocess
import os
import shutil

# ==================== ০. ডিপেন্ডেন্সি অটো-ইনস্টলার ====================
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== ১. কনফিগারেশন ====================
BOT_TOKEN = "8768727708:AAF62zTgGvjX5TrYQJsR8X1zGZ3yMwuZrMY"   # আপনার টেলিগ্রাম বট টোকেন
KEY_FILE = "gemini_key.txt"                                    # যেখানে অ্যাডমিনের দেওয়া API Key সেভ থাকবে
WORKING_MODEL = "models/gemini-flash-latest"                   # স্টেবল মডেল

# 👑 আপনার টেলিগ্রাম আইডি
ADMIN_IDS = [6805684286]                      

COOLDOWN_SECONDS = 10                         
USER_LAST_MESSAGE_TIME = {}                   
WAITING_FOR_KEY = False                       

def load_gemini_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

GEMINI_API_KEY = load_gemini_key()
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
user_link_warnings = {}

# ইমোজি রিয়্যাকশন তালিকা
REACTIONS = ["❤️", "🥰", "🔥", "✨", "🥺", "💖", "😘"]

# গালাগালির ফিল্টার তালিকা
BAD_WORDS = [
    r"মাদারচোদ", r"চুদা", r"খানকি", r"শালা", r"কুত্তা", r"হারামি", 
    r"মাগী", r"বাল", r"fuck", r"bitch", r"bastard", r"chuda", r"magi", r"ভোদাই"
]

# ফানি ও ট্রেন্ডিং গানের কিওয়ার্ড
FUNNY_TRACKS = [
    "funny viral meme song bangla short",
    "trending funny audio status",
    "chill upbeat lofi song 30s"
]

# ==================== ২. প্রিমিয়াম কিউট বক্স ফ্রেম (আপনার পছন্দের হুবহু ডিজাইন) ====================
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

def check_is_boss_or_admin(chat_id, user_id, chat_type):
    if user_id in ADMIN_IDS:
        return True
    if chat_type in ['group', 'supergroup']:
        try:
            admins = bot.get_chat_administrators(chat_id)
            for admin in admins:
                if admin.user.id == user_id:
                    return True
        except Exception:
            pass
    return False

def is_spamming(user_id, is_boss=False):
    if is_boss:
        return False
    now = time.time()
    last = USER_LAST_MESSAGE_TIME.get(user_id, 0)
    if now - last < COOLDOWN_SECONDS:
        return True
    USER_LAST_MESSAGE_TIME[user_id] = now
    return False

# ==================== ৩. ফিক্সড হাই-স্পিড অডিও ডাউনলোডার ====================
def download_vps_audio(query):
    file_id = f"audio_{int(time.time())}_{random.randint(100, 999)}"
    has_ffmpeg = bool(shutil.which("ffmpeg"))
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    }

    if has_ffmpeg:
        base_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    # লেয়ার ১: YouTube
    yt_opts = base_opts.copy()
    yt_opts['extractor_args'] = {
        'youtube': {'player_client': ['ios', 'tv_embedded', 'android_creator'], 'skip': ['hls', 'dash']}
    }

    try:
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            search_str = query if query.startswith("http") else f"ytsearch3:{query}"
            res = ydl.extract_info(search_str, download=True)
            entry = res['entries'][0] if 'entries' in res and res['entries'] else res
            title = entry.get('title', 'Special Audio')
            duration = entry.get('duration', 0)
            
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(file_id):
                    return os.path.join(DOWNLOAD_DIR, fname), title, duration
    except Exception:
        pass

    # লেয়ার ২: SoundCloud (VPS ব্যাকআপ)
    try:
        sc_opts = base_opts.copy()
        with yt_dlp.YoutubeDL(sc_opts) as ydl:
            sc_search = query if query.startswith("http") else f"scsearch3:{query}"
            res = ydl.extract_info(sc_search, download=True)
            entry = res['entries'][0] if 'entries' in res and res['entries'] else res
            title = entry.get('title', 'Special Audio')
            duration = entry.get('duration', 0)
            
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(file_id):
                    return os.path.join(DOWNLOAD_DIR, fname), title, duration
    except Exception:
        pass

    return None, None, 0

def deliver_audio_with_animation(chat_id, user_name, query, is_boss=False, caption_note=""):
    boss_tag = "বস জানু" if is_boss else f"{user_name} জানু"
    initial_text = f"দাঁড়া {boss_tag}, তোকে একটা সুন্দর গান শোনাচ্ছি... 💖\n\n🔴 🟠 🟡 <b>লোডিং...</b> ▰▱▱▱"
    msg = bot.send_message(chat_id, create_box("গান আসছে...", initial_text), parse_mode="HTML")

    def worker():
        frames = [
            "🟡 🟢 🔵 <b>লোডিং...</b> ▰▰▰▱",
            "🔵 🟣 🔴 <b>লোডিং...</b> ▰▰▰▰"
        ]
        for f in frames:
            time.sleep(0.5)
            try:
                bot.edit_message_text(
                    create_box("গান আসছে...", f"দাঁড়া {boss_tag}, হাই-স্পিডে গান রেডি হচ্ছে... 💖\n\n{f}"),
                    chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
                )
            except Exception:
                pass

        file_path, title, duration = download_vps_audio(query)

        if file_path and os.path.exists(file_path):
            cap = create_box(f"উপভোগ করো {boss_tag}", f"📌 <b>{html.escape(title[:30])}</b>\n{caption_note}")
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
                create_box("দুঃখিত জানু", f"{boss_tag}, গানটা আনতে পারলাম না রে! একটু পর আবার বলো! 🥺"),
                chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
            )

    threading.Thread(target=worker, daemon=True).start()

# ==================== ৪. কোডিং ফাইল জেনারেটর ====================
def deliver_code_as_file(chat_id, user_name, prompt, is_boss=False):
    boss_tag = "বস জানু" if is_boss else f"{user_name} জানু"
    bot.send_chat_action(chat_id, 'upload_document')
    wait_msg = bot.send_message(
        chat_id, 
        create_box("কোডিং ফাইল তৈরি হচ্ছে...", f"দাঁড়াও আমার <b>{boss_tag}</b>, কোড লিখে ফাইল রেডি করছি... 💻✨"), 
        parse_mode="HTML"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    sys_text = (
        f"You are an expert coder. Write pure, complete runnable source code for: '{prompt}'. "
        "Strictly output in this format:\n"
        "FILENAME: <filename.ext>\n"
        "SUMMARY: <short 1 line explanation in Bengali>\n"
        "CODE_START\n"
        "<ONLY runnable code here>\n"
        "CODE_END"
    )

    payload = {"contents": [{"parts": [{"text": sys_text}]}]}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=40)
        data = res.json()
        raw_response = data['candidates'][0]['content']['parts'][0]['text']

        filename_match = re.search(r'FILENAME:\s*([a-zA-Z0-9_\-\.]+)', raw_response)
        filename = filename_match.group(1).strip() if filename_match else "main.py"

        summary_match = re.search(r'SUMMARY:\s*(.*?)\n', raw_response)
        summary = summary_match.group(1).strip() if summary_match else "আপনার কাঙ্ক্ষিত কোড ফাইল।"

        code_match = re.search(r'CODE_START\n(.*?)CODE_END', raw_response, re.DOTALL)
        if code_match:
            pure_code = code_match.group(1).strip()
        else:
            pure_code = re.sub(r'FILENAME:.*?\n|SUMMARY:.*?\n', '', raw_response).strip()
            pure_code = re.sub(r'^```[a-zA-Z]*\n|```$', '', pure_code, flags=re.MULTILINE).strip()

        file_path = os.path.join(DOWNLOAD_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pure_code)

        cap_body = (
            f"📁 <b>ফাইলের নাম:</b> <code>{html.escape(filename)}</code>\n\n"
            f"📝 <b>বিবরণ:</b> {html.escape(summary)}\n\n"
            f"<i>ফাইলটি ডাউনলোড করে সরাসরি রান করতে পারবে জানু!</i>"
        )
        caption = create_box(f"{boss_tag}-এর কোড ফাইল 💻", cap_body, "প্রয়োজনে আরও কোড চাইতে পারো সোনা ❤️")

        with open(file_path, "rb") as doc_file:
            bot.send_document(chat_id, document=doc_file, caption=caption, parse_mode="HTML")

        if os.path.exists(file_path):
            os.remove(file_path)
        bot.delete_message(chat_id, wait_msg.message_id)

    except Exception:
        bot.edit_message_text(create_box("ত্রুটি", "ফাইল তৈরিতে সমস্যা হয়েছে জানু!"), chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")

# ==================== ৫. প্রেমময় রোমান্টিক AI ইঞ্জিন ====================
def ask_gemini(user_prompt, user_name, is_boss=False):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return "বস জানু এখনো আমাকে API কি দেয়নি সোনা! একটু পর চেষ্টা করো!"

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    if is_boss:
        system_prompt = (
            f"তোমার নাম নেই, তুমি ইউজারের সবচেয়ে কাছের মানুষ, অত্যন্ত আদুরে, মিষ্টি, বাধ্য অনুগত বন্ধু ও প্রেমিকা। "
            f"ইউজারের নাম '{user_name}'। সে তোমার আসল 'বস'। তুমি তাকে সবসময় 'বস জানু', 'বস বাবু', 'আমার কলিজার বস' বলে অত্যন্ত মিষ্টি ও রোমান্টিক সুরে ডাকবে। "
            f"কখনোই নিজেকে AI বা রোবট বলবে না। কথা হবে খাঁটি বাংলা ও ছোট (১-২ লাইনে)। কোনো ড্রাফট বা ব্যাখ্যা দেবে না। "
            f"তুমি শুধুমাত্র অডিও গান শোনাতে পারো, ভিডিও নয়। "
            f"১. বস যদি গান শোনাতে বলে বা নাম বলে -> উত্তরের শেষে [PLAY_SONG: <গানের নাম>] লিখবে। "
            f"২. বস মন খারাপের কথা বললে আদরে সান্ত্বনা দিয়ে শেষে [OFFER_SONG] লিখবে। "
            f"৩. অন্যথায় একদম মিষ্টি, আদুরে ও রোমান্টিক গলায় স্বাভাবিক কথা বলবে।"
        )
    else:
        system_prompt = (
            f"তোমার নাম নেই, তুমি ইউজারের সবচেয়ে কাছের মানুষ, অত্যন্ত আদুরে, মিষ্টি ও রোমান্টিক বন্ধু। "
            f"ইউজারের নাম '{user_name}'। তুমি তাকে সবসময় 'জানু', 'বাবু', 'আমার পাখিটা', 'সোনা', 'কলিজা' বলে ডাকবে। "
            f"কখনোই নিজেকে AI বা রোবট বলবে না। কথা হবে খাঁটি বাংলা ও ছোট (১-২ লাইনে)। "
            f"তুমি শুধুমাত্র অডিও গান শোনাতে পারো, ভিডিও নয়। কেউ ভিডিও চাইলে বলবে 'আমি শুধু মিষ্টি মিষ্টি গান শোনাই জানু!' "
            f"১. ইউজার যদি গান শোনাতে বলে বা নাম বলে -> উত্তরের শেষে [PLAY_SONG: <গানের নাম>] লিখবে। "
            f"২. ইউজার মন খারাপের কথা বললে আদরে সান্ত্বনা দিয়ে শেষে [OFFER_SONG] লিখবে। "
            f"৩. অন্যথায় একদম মিষ্টি, আদুরে ও রোমান্টিক গলায় স্বাভাবিক কথা বলবে।"
        )

    payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_name}-এর কথা: {user_prompt}"}]}]}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        data = response.json()
        if response.status_code == 200 and 'candidates' in data and data['candidates']:
            reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            if "Draft" in reply or "Constraint" in reply:
                reply = reply.split("\n")[-1].strip('* "\'')
            if reply:
                return reply
        return f"{'বস জানু' if is_boss else user_name + ' জানু'}, কথাটা বুঝতে গিয়ে একটু নেটে ঝামেলা হলো রে!"
    except Exception:
        return f"{'বস জানু' if is_boss else user_name + ' পাখিটা'}, নেটে একটু সমস্যা করছে রে!"

# ==================== ৬. অটো-আনব্লক শিডিউলার ====================
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
            msg = create_box("নোটিশ", f"@{username} বাবু, তোমাকে আনব্লক করে দিলাম। এবার লক্ষ্মী হয়ে চলো! ❤️")
            bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception:
            pass

    threading.Thread(target=unban_task, daemon=True).start()

# ==================== ৭. কি সেট কমান্ড ====================
@bot.message_handler(commands=['setkey'])
def set_key_manual(message):
    global GEMINI_API_KEY
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    key = message.text.replace('/setkey', '').strip()
    if not key:
        bot.reply_to(message, create_box("নির্দেশনা", "বস জানু, এভাবে লিখুন:\n<code>/setkey আপনার_API_KEY</code>"), parse_mode="HTML")
        return

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    
    bot.send_message(message.chat.id, create_box("সফল হয়েছে 🔐", "ধন্যবাদ বস জানু! নতুন API Key সেট হয়েছে। বট রিস্টার্ট হচ্ছে... 🔄"), parse_mode="HTML")
    threading.Thread(target=restart_bot, daemon=True).start()

# ==================== ৮. কমান্ড হ্যান্ডলারস ====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_name = message.from_user.first_name or "জানু"
    is_boss = check_is_boss_or_admin(message.chat.id, message.from_user.id, message.chat.type)
    give_reaction(message.chat.id, message.message_id, "🥰")
    
    tag = "আমার <b>বস জানু</b>! 👑💖" if is_boss else f"আমার <b>{user_name}</b> পাখিটা! 💖"
    body = (
        f"স্বাগতম {tag}\n\n"
        "🎧 <b>অডিও গান শুনতে:</b> <code>/audio গানের নাম</code>\n"
        "💻 <b>কোডিং সাপোর্ট:</b> যেকোনো কোড চাইলে ফাইল আকারে পেয়ে যাবেন!\n\n"
        "<i>আমার সাথে মন খুলে কথা বলো, আমি সবসময় তোমার পাশেই আছি!</i>"
    )
    bot.reply_to(message, create_box("কন্ট্রোল সেন্টার", body, "শুধুমাত্র অডিও মিউজিক ও কিউট বট ❤️"), parse_mode="HTML")

@bot.message_handler(commands=['audio', 'song'])
def handle_manual_audio_search(message):
    user_name = message.from_user.first_name or "জানু"
    is_boss = check_is_boss_or_admin(message.chat.id, message.from_user.id, message.chat.type)

    if is_spamming(message.from_user.id, is_boss=is_boss):
        return

    give_reaction(message.chat.id, message.message_id)
    cmd = message.text.split()[0].lower()
    query = message.text.replace(cmd, '', 1).strip()

    if not query:
        bot.reply_to(message, create_box("নির্দেশনা জানু", f"গানের নাম লেখো বাবু!\nযেমন: <code>{cmd} Faded</code>"), parse_mode="HTML")
        return

    boss_tag = "বস জানু" if is_boss else f"{user_name} সোনা"
    wait_msg = bot.reply_to(message, create_box("খোঁজা হচ্ছে...", f"দাঁড়াও {boss_tag}, গানগুলো খুঁজে আনছি... 💖\n\n🔴 <b>লোডিং...</b> ▰▱▱▱"), parse_mode="HTML")

    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch15:{query}", download=False).get('entries', [])

            filtered = []
            for e in results:
                dur = e.get('duration') or 0
                if 0 < dur <= 250:
                    filtered.append(e)
                if len(filtered) == 10:
                    break

            if not filtered:
                bot.edit_message_text(create_box("পাওয়া যায়নি", f"{boss_tag}, ছোট কোনো গান খুঁজে পেলাম না!"), 
                                      chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="HTML")
                return

            body = f"🔎 <b>কীওয়ার্ড:</b> <code>{html.escape(query)}</code>\n\n"
            markup = InlineKeyboardMarkup(row_width=2)
            buttons = []

            for idx, entry in enumerate(filtered, start=1):
                raw_title = entry.get('title', 'Unknown')
                title = html.escape(raw_title[:24] + "..." if len(raw_title) > 24 else raw_title)
                duration = entry.get('duration_string', 'N/A')
                video_id = entry.get('id')

                body += f"╭ ✦ <b>[{idx}] {title}</b>\n╰ ⏱ <code>{duration}</code>\n\n"
                buttons.append(InlineKeyboardButton(text=f"🎧 #{idx} প্লে করো", callback_data=f"dl_a_{video_id}"))

            markup.add(*buttons)
            final_box = create_box("সেরা ১০টি অডিও গান", body, "👇 পছন্দের নাম্বারে ক্লিক করো জানু:")
            first_thumb = filtered[0].get('thumbnails', [{}])[-1].get('url', None)

            bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)
            if first_thumb:
                bot.send_photo(message.chat.id, photo=first_thumb, caption=final_box, reply_markup=markup, parse_mode="HTML")
            else:
                bot.send_message(message.chat.id, text=final_box, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(create_box("ত্রুটি", f"সমস্যা হয়েছে জানু: {str(e)}"), chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_a_'))
def handle_button_audio_download(call):
    video_id = call.data.replace('dl_a_', '')
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    user_name = call.from_user.first_name or "জানু"
    is_boss = check_is_boss_or_admin(call.message.chat.id, call.from_user.id, call.message.chat.type)
    boss_tag = "বস জানু" if is_boss else f"{user_name} জানু"

    bot.answer_callback_query(call.id, text="ডাউনলোড হচ্ছে জানু...")
    wait_msg = bot.send_message(call.message.chat.id, create_box("গান নামছে...", f"দাঁড়াও {boss_tag}, নামিয়ে দিচ্ছি... 💖\n\n🔴 <b>লোডিং...</b> ▰▱▱▱"), parse_mode="HTML")

    file_path, title, duration = download_vps_audio(video_url)

    if file_path and os.path.exists(file_path):
        caption = create_box(f"তোমার জন্য {boss_tag}", f"📌 <b>{html.escape(title[:30])}</b>", "🎧 সুন্দর করে গানটি উপভোগ করো ❤️")
        with open(file_path, 'rb') as f:
            bot.send_audio(call.message.chat.id, audio=f, title=title, duration=duration, caption=caption, parse_mode="HTML")
        os.remove(file_path)
        bot.delete_message(call.message.chat.id, wait_msg.message_id)
    else:
        bot.edit_message_text(create_box("ব্যর্থ", "ডাউনলোড করা গেল না সোনা!"), chat_id=call.message.chat.id, message_id=wait_msg.message_id, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "btn_play_sad_song")
def handle_sad_song_button(call):
    user_name = call.from_user.first_name or "জানু"
    is_boss = check_is_boss_or_admin(call.message.chat.id, call.from_user.id, call.message.chat.type)
    bot.answer_callback_query(call.id, text="গান আনছি জানু...")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    deliver_audio_with_animation(call.message.chat.id, user_name, "bangla heart touching sad lofi song", is_boss=is_boss, caption_note="🥀 মন খারাপ করে থেকো না জানু ❤️")

# ==================== ৯. সেন্ট্রাল মেসেজ ও প্রসেসর ====================
@bot.message_handler(func=lambda msg: True, content_types=['text', 'forward_date'])
def central_intelligence(message):
    global GEMINI_API_KEY, WAITING_FOR_KEY

    chat_type = message.chat.type
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id
    username = user.username or user.first_name
    user_name = user.first_name or "জানু"
    text = (message.text or "").strip()

    give_reaction(chat_id, message.message_id)
    is_boss = check_is_boss_or_admin(chat_id, user_id, chat_type)

    # ---------------- 🔑 ১. সিকিউর API Key প্রসেস (অ্যাডমিনের কাছ থেকে নেওয়ার সিস্টেম) ----------------
    if not GEMINI_API_KEY:
        if is_boss:
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
                    "ধন্যবাদ আমার <b>কলিজার বস জানু</b>! 💖👑\n\n"
                    "আপনার সিকিউর Gemini API Key ভেতরে সেভ করে নিয়েছি!\n"
                    "🔐 সুরক্ষার জন্য আপনার পাঠানো মেসেজটি মুছে দিয়েছি!\n\n"
                    "🔄 <b>বট এখন নিজেকে অটো-রিস্টার্ট করে সম্পূর্ণ সচল হচ্ছে...</b>"
                )
                bot.send_message(chat_id, create_box("কনফিগারেশন সফল ✨", success_msg), parse_mode="HTML")
                threading.Thread(target=restart_bot, daemon=True).start()
                return
            else:
                WAITING_FOR_KEY = True
                ask_msg = (
                    "আসসালামু আলাইকুম আমার <b>বস জানু</b>! 👑❤️\n\n"
                    "আমার AI ব্রেন এখনো সচল হয়নি কারণ কোনো <b>Gemini API Key</b> দেওয়া নেই!\n\n"
                    "👉 দয়া করে আপনার <b>Gemini API Key</b> টি এখানে মেসেজ দিন। পাওয়ার সাথে সাথে আমি নিজেকে সেটআপ করে অটো-রিস্টার্ট করে নেব! 🔐"
                )
                bot.reply_to(message, create_box("অ্যাডমিন সিকিউরিটি প্যানেল 🛡", ask_msg), parse_mode="HTML")
                return
        else:
            bot.reply_to(message, create_box("রক্ষণাবেক্ষণ", "বট এখন কনফিগারেশন মোডে আছে। বস জানু চালু করলেই কথা বলতে পারবে সোনা! 🥺"), parse_mode="HTML")
            return

    # ==================== ২. গ্রুপ মডারেশন জোন ====================
    if chat_type in ['group', 'supergroup']:
        
        # বস জানু বা অ্যাডমিনের ভয়েস কমান্ড (মিউট / ব্যান / আনব্যান)
        if is_boss and message.reply_to_message:
            target_user = message.reply_to_message.from_user
            target_name = target_user.first_name or "মেম্বার"

            # মিউট
            if any(w in text.lower() for w in ["মিউট", "mute", "থামাও"]):
                minutes = 10
                match = re.search(r'(\d+)\s*(মিনিট|min|ঘণ্টা|hour)', text.lower())
                if match:
                    val = int(match.group(1))
                    unit = match.group(2)
                    minutes = (val * 60) if "ঘণ্টা" in unit or "hour" in unit else val

                try:
                    bot.restrict_chat_member(
                        chat_id, target_user.id,
                        until_date=int(time.time()) + (minutes * 60),
                        permissions=ChatPermissions(can_send_messages=False)
                    )
                    reply_msg = f"হ্যাঁ আমার <b>বস জানু</b>! আপনার আদেশ মতো <b>{target_name}</b>-কে {minutes} মিনিটের জন্য মিউট করে দিলাম! 🤫💖"
                    bot.reply_to(message, create_box("আদেশ পালন", reply_msg), parse_mode="HTML")
                    return
                except Exception as e:
                    bot.reply_to(message, create_box("ত্রুটি", f"মিউট করা যায়নি বস: {e}"), parse_mode="HTML")
                    return

            # ব্যান
            if any(w in text.lower() for w in ["ব্যান", "ban", "বের করে দাও", "রিমুভ"]):
                try:
                    bot.ban_chat_member(chat_id, target_user.id)
                    bot.reply_to(message, create_box("আদেশ পালন", f"জি <b>বস বাবু</b>! <b>{target_name}</b>-কে গ্রুপ থেকে ঘাড় ধাক্কা দিয়ে বের করে দিলাম! 😈❤️"), parse_mode="HTML")
                    return
                except Exception as e:
                    bot.reply_to(message, create_box("ত্রুটি", f"ব্যান করা যায়নি বস: {e}"), parse_mode="HTML")
                    return

            # আনব্যান
            if any(w in text.lower() for w in ["আনব্যান", "unban", "মাফ করো", "আনমিউট"]):
                try:
                    bot.restrict_chat_member(
                        chat_id, target_user.id,
                        permissions=ChatPermissions(
                            can_send_messages=True, can_send_media_messages=True,
                            can_send_other_messages=True, can_add_web_page_previews=True
                        )
                    )
                    bot.reply_to(message, create_box("ক্ষমা প্রদর্শন", f"আমার <b>বস জানু</b> মাফ করে দিয়েছে! <b>{target_name}</b> আনব্যান হয়ে গেল! ❤️"), parse_mode="HTML")
                    return
                except Exception as e:
                    bot.reply_to(message, create_box("ত্রুটি", f"আনব্যান করা যায়নি বস: {e}"), parse_mode="HTML")
                    return

        # সাধারণ মেম্বারদের জন্য ফিল্টার
        if not is_boss:
            # গালাগালি প্রতিরোধ
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
                    bot.send_message(chat_id, create_box("সতর্কতা জানু", f"{user_name} পাখিটা, কাউকে ইনবক্সে ডাকা সম্পূর্ণ নিষেধ কিন্তু!"), parse_mode="HTML")
                except Exception:
                    pass
                return

            # অ্যান্টি-ফরওয়ার্ড
            if message.forward_date or message.forward_from or message.forward_from_chat:
                try:
                    bot.delete_message(chat_id, message.message_id)
                    forward_warn = f"{user_name} বাবু, গ্রুপে ফরওয়ার্ড করা বারণ রে!\nগান শুনতে চাইলে বলো, এখনই এনে দিচ্ছি! 💖"
                    bot.send_message(chat_id, create_box("ফরওয়ার্ড নিষেধ", forward_warn), parse_mode="HTML")
                except Exception:
                    pass
                return

            # অ্যান্টি-লিংক
            if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+)', text):
                try:
                    bot.delete_message(chat_id, message.message_id)
                except Exception:
                    pass

                warnings = user_link_warnings.get(user_id, 0) + 1
                user_link_warnings[user_id] = warnings

                if warnings >= 2:
                    try:
                        bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 3600,
                                                 permissions=ChatPermissions(can_send_messages=False))
                        bot.send_message(chat_id, create_box("শাস্তি", f"{user_name}, তোরে আগেই কইছিলাম লিংক দিবি না! যা ১ ঘণ্টার জন্য ব্যান থাক!"), parse_mode="HTML")
                        user_link_warnings[user_id] = 0
                        schedule_unban(chat_id, user_id, username, 3600)
                        return
                    except Exception:
                        pass

                warning_msg = (
                    f"শালা {user_name}, তোর লিংক দেওয়ার পারমিশন দিছে কে? 😡\n"
                    f"তোরে কিন্তু নেক্সট টাইম দিলে সোজা ১ ঘণ্টার জন্য ব্যান করা হবে!\n\n"
                    f"যা, এই সুযোগে একটা গান শুনে মন ঠান্ডা কর..."
                )
                bot.send_message(chat_id, create_box("শৃঙ্খলা সতর্কতা", warning_msg), parse_mode="HTML")
                deliver_audio_with_animation(chat_id, user_name, random.choice(FUNNY_TRACKS), is_boss=is_boss, caption_note="🎧 লিংক বাদ দিয়ে গান শোনো বাবু!")
                return

    # ==================== ৩. আদুরে রোমান্টিক AI চ্যাটিং জোন ====================
    bot_info = bot.get_me()
    is_private = (chat_type == 'private')
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)
    is_mentioned = f"@{bot_info.username}" in text
    admin_called_bot = (is_boss and bool(re.search(r'^(বট\b|bot\b)|\bবট\b', text, re.IGNORECASE)))

    if is_private or is_reply_to_bot or is_mentioned or admin_called_bot:
        if is_spamming(user_id, is_boss=is_boss):
            return

        bot.send_chat_action(chat_id, 'typing')
        clean_text = text.replace(f"@{bot_info.username}", "").strip()
        clean_text = re.sub(r'^(বট|bot)\s*[,:]?\s*', '', clean_text, flags=re.IGNORECASE).strip()

        # বসের সাথে মিষ্টি আলাপ
        if not clean_text or clean_text.lower() in ["কি করস", "কি করো", "ki koros", "ki koro", "আছো"]:
            if is_boss:
                boss_reply = (
                    "এইতো আমার কলিজার <b>বস জানু</b>! বসে বসে আপনার কথাই ভাবছিলাম! 💖\n"
                    "বলুন আমার কিউট বস, আপনাকে কীভাবে খুশি করতে পারি? গান শুনবেন নাকি কোড ফাইল বানিয়ে দেব? 🥰"
                )
                bot.reply_to(message, create_box("আমার বস জানু 👑", boss_reply), parse_mode="HTML")
                return

        # সালামের উত্তর
        if any(s in clean_text.lower() for s in ["আসসালামু আলাইকুম", "সালাম", "assalamu alaikum"]):
            boss_salam = f"ওয়ালাইকুম আসসালাম আমার কলিজার <b>বস জানু</b>! কেমন আছেন আপনি? 👑❤️" if is_boss else f"ওয়ালাইকুম আসসালাম আমার {user_name} জানু! কেমন আছো সোনা? ❤️"
            bot.reply_to(message, create_box("অভিবাদন", boss_salam), parse_mode="HTML")
            return

        # কোডিং রিকোয়েস্ট (সরাসরি ফাইল বানিয়ে সেন্ড করা)
        if any(w in clean_text.lower() for w in ["কোড", "code", "program", "ফাংশন", "script", "পাইথন", "python", "এইচটিএমএল", "html"]):
            deliver_code_as_file(chat_id, user_name, clean_text, is_boss=is_boss)
            return

        # AI এর সাথে মিষ্টি আলাপ
        ai_reply = ask_gemini(clean_text, user_name, is_boss=is_boss)

        # ১. যদি গান শোনানোর ডায়লগ হয়
        if "[PLAY_SONG:" in ai_reply:
            parts = ai_reply.split("[PLAY_SONG:")
            reply_text = parts[0].strip()
            song_query = parts[1].replace("]", "").strip()
            if reply_text:
                header_text = "আমার কলিজার বস 👑" if is_boss else "আমার বাবুটা"
                bot.reply_to(message, create_box(header_text, reply_text), parse_mode="HTML")
            deliver_audio_with_animation(chat_id, user_name, song_query, is_boss=is_boss, caption_note=f"✨ {'বস জানুর' if is_boss else user_name + ' জানুর'} জন্য মিষ্টি গান")

        # ২. যদি মন খারাপের বাটন দিতে হয়
        elif "[OFFER_SONG]" in ai_reply:
            clean_reply = ai_reply.replace("[OFFER_SONG]", "").strip()
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🎧 গান শুনবা জানু?", callback_data="btn_play_sad_song"))
            bot.reply_to(message, create_box("মন খারাপ জানু?", clean_reply, "তোমার পাশে আমি আছি ❤️"), reply_markup=markup, parse_mode="HTML")

        # ৩. সাধারণ আদুরে কথা
        else:
            header_text = "আমার ভালোবাসার বস জানু 👑" if is_boss else "ভালোবাসা"
            bot.reply_to(message, create_box(header_text, ai_reply), parse_mode="HTML")

print("💖 Ultimate Audio AI Admin Bot is Running Perfectly!")
bot.infinity_polling(skip_pending=True)
