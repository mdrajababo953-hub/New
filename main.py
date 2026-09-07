import sys
import subprocess
import os
import shutil

# ==================== ০. অটো-মডিউল ও FFmpeg চেকার ====================
REQUIRED_PACKAGES = {
    "telebot": "pyTelegramBotAPI",
    "yt_dlp": "yt-dlp",
    "requests": "requests",
    "urllib3": "urllib3",
    "ujson": "ujson"
}

def auto_installer():
    print("🔍 [1/2] সিস্টেম ডিপেন্ডেন্সি চেক করা হচ্ছে...")
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"📦 ইনস্টল করা হচ্ছে: {pip_name} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

    # FFmpeg আছে কিনা চেক করা (গান কনভার্ট করার জন্য এটি জরুরি)
    if not shutil.which("ffmpeg"):
        print("⚠️ [সতর্কতা] সার্ভারে FFmpeg পাওয়া যায়নি! apt দিয়ে ইনস্টল করার চেষ্টা করছি...")
        try:
            subprocess.run(["sudo", "apt-get", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["sudo", "apt-get", "install", "ffmpeg", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ FFmpeg সফলভাবে ইনস্টল হয়েছে!")
        except Exception:
            print("⚠️ FFmpeg অটো ইনস্টল হয়নি। তবে নো টেনশন, বট নেটিভ অডিও ফরম্যাটে গান প্লে করবে!")

auto_installer()

# ==================== মডিউল ইমপোর্ট ====================
import re
import time
import html
import random
import traceback
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

# ==================== ১. কনফিগারেশন ও সিকিউরিটি ====================
BOT_TOKEN = "8768727708:AAF62zTgGvjX5TrYQJsR8X1zGZ3yMwuZrMY"   # আপনার টেলিগ্রাম বট টোকেন
# অফিশিয়াল স্টেবল মডেল
WORKING_MODEL = "models/gemini-1.5-flash"
KEY_FILE = "gemini_key.txt"

# 👑 আপনার টেলিগ্রাম আইডি
ADMIN_IDS = [6805684286]                      

COOLDOWN_SECONDS = 10                         # সাধারণ মেম্বারদের জন্য ১০ সেকেন্ড
USER_LAST_MESSAGE_TIME = {}                   
WAITING_FOR_KEY = False                       

# ফাস্ট নেটওয়ার্ক সেশন
http_session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
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

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

REACTIONS = ["❤️", "🥰", "🔥", "✨", "🥺", "💖", "😘", "🌸", "👑"]

BAD_WORDS = [
    r"মাদারচোদ", r"চুদা", r"খানকি", r"শালা", r"কুত্তা", r"হারামি", 
    r"মাগী", r"বাল", r"fuck", r"bitch", r"bastard", r"chuda", r"magi", r"ভোদাই"
]

# ==================== ২. প্রিমিয়াম ফ্রেম বক্স ====================
def create_box(header, body, footer=""):
    box = f"╭── 🎀 <b>{header}</b> 🎀\n│\n"
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
    current_time = time.time()
    last_time = USER_LAST_MESSAGE_TIME.get(user_id, 0)
    if current_time - last_time < COOLDOWN_SECONDS:
        return True
    USER_LAST_MESSAGE_TIME[user_id] = current_time
    return False

# ==================== ৩. ট্রিপল-লেয়ার বুলেটপ্রুফ অডিও ডাউনলোডার ====================
def download_vps_audio(query):
    file_id = f"audio_{int(time.time())}_{random.randint(100, 999)}"
    has_ffmpeg = bool(shutil.which("ffmpeg"))
    
    # FFmpeg থাকলে mp3 বানাবে, না থাকলে ডিরেক্ট অডিও ফাইল রাখবে
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

    # লেয়ার ১: YouTube Music / Web Bypass
    yt_opts = base_opts.copy()
    yt_opts['extractor_args'] = {
        'youtube': {
            'player_client': ['ios', 'tv_embedded', 'android_creator'],
            'skip': ['hls', 'dash']
        }
    }

    # সার্চ ট্রাই ১ (YouTube)
    try:
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            search_str = query if query.startswith("http") else f"ytsearch3:{query}"
            res = ydl.extract_info(search_str, download=True)
            entry = res['entries'][0] if 'entries' in res and res['entries'] else res
            
            title = entry.get('title', 'Special Audio')
            duration = entry.get('duration', 0)
            
            # তৈরি হওয়া ফাইলটি খোঁজা
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(file_id):
                    return os.path.join(DOWNLOAD_DIR, fname), title, duration
    except Exception as yt_err:
        print(f"⚠️ [YouTube Engine Blocked]: {yt_err}. SoundCloud ফলব্যাকে যাচ্ছি...")

    # লেয়ার ২: SoundCloud ফলব্যাক (এটি VPS IP কখনো ব্লক করে না)
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
    except Exception as sc_err:
        print(f"❌ [SoundCloud Error]: {sc_err}")

    return None, None, 0

def deliver_audio_with_animation(chat_id, user_name, query, is_boss=False, custom_cap=""):
    boss_tag = "বস জানু" if is_boss else f"{user_name} জানু"
    initial_text = f"দাঁড়াও আমার <b>{boss_tag}</b>, হাই-স্পিড গান নামাচ্ছি... 🚀💖\n\n🔴 <b>খোঁজা হচ্ছে...</b> ▰▱▱▱"
    msg = bot.send_message(chat_id, create_box("মিউজিক প্লেয়ার", initial_text), parse_mode="HTML")

    def worker():
        try:
            bot.edit_message_text(
                create_box("মিউজিক প্লেয়ার", f"গান পেয়ে গেছি {boss_tag}! ফাইল তৈরি হচ্ছে... 💖\n\n🟡 <b>ডাউনলোড হচ্ছে...</b> ▰▰▰▱"),
                chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

        file_path, title, duration = download_vps_audio(query)

        if file_path and os.path.exists(file_path):
            cap_text = f"🎶 <b>{html.escape(title[:35])}</b>"
            if custom_cap:
                cap_text += f"\n\n{html.escape(custom_cap)}"
            cap = create_box(f"{boss_tag}-এর পছন্দের গান", cap_text, "🎧 সুন্দর করে উপভোগ করো সোনা ❤️")
            try:
                with open(file_path, 'rb') as f_obj:
                    bot.send_audio(chat_id, audio=f_obj, title=title, duration=duration, caption=cap, parse_mode="HTML")
            except Exception:
                with open(file_path, 'rb') as f_obj:
                    bot.send_audio(chat_id, audio=f_obj, title=title, duration=duration)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
        else:
            bot.edit_message_text(
                create_box("দুঃখিত সোনা", f"{boss_tag}, কোনো গান খুঁজে পেলাম না! অন্য একটি গানের নাম লিখে বলো না সোনা! 🥺"),
                chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML"
            )

    threading.Thread(target=worker, daemon=True).start()

# ==================== ৪. ১০০% ক্র্যাশ-প্রুফ কোডিং ফাইল জেনারেটর ====================
def deliver_code_as_file(chat_id, user_name, prompt, is_boss=False):
    global GEMINI_API_KEY
    boss_tag = "বস জানু" if is_boss else f"{user_name} জানু"

    if not GEMINI_API_KEY:
        bot.send_message(chat_id, create_box("টোকেন নেই", "বস জানু এখনো API Key সেট করেনি! 🥺"), parse_mode="HTML")
        return

    bot.send_chat_action(chat_id, 'upload_document')
    wait_msg = bot.send_message(
        chat_id, 
        create_box("কোডিং ফাইল তৈরি হচ্ছে...", f"দাঁড়াও আমার <b>{boss_tag}</b>, কোড লিখে ফাইল রেডি করছি... 💻✨"), 
        parse_mode="HTML"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    system_prompt = (
        f"You are an expert coder. The user '{user_name}' wants code for: '{prompt}'. "
        "Output in this exact structure without failing:\n"
        "FILENAME: <suitable filename with extension like bot.py or index.html>\n"
        "SUMMARY: <short 1 line explanation in Bengali>\n"
        "CODE_START\n"
        "<ONLY raw runnable code here>\n"
        "CODE_END"
    )

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        res = http_session.post(url, data=ujson.dumps(payload), headers=headers, timeout=50)
        data = ujson.loads(res.text)

        # Gemini Error Check
        if 'error' in data:
            err_msg = data['error'].get('message', 'Unknown AI Error')
            print(f"❌ [Gemini API Error]: {err_msg}")
            bot.edit_message_text(create_box("AI ত্রুটি", f"গুগল এপিআই এরর দিয়েছে: {html.escape(err_msg[:80])}"), chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")
            return

        candidates = data.get('candidates', [])
        if not candidates or 'content' not in candidates[0]:
            bot.edit_message_text(create_box("সুরক্ষা বাধা", "Google AI এই কোডটি লিখতে বাধা দিয়েছে সোনা! অন্য কিছু ট্রাই করো! 🥺"), chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")
            return

        raw_text = candidates[0]['content']['parts'][0]['text']

        # ফাইলনেম এক্সট্রাকশন
        filename_match = re.search(r'FILENAME:\s*([a-zA-Z0-9_\-\.]+)', raw_text)
        filename = filename_match.group(1).strip() if filename_match else "main.py"

        # সামারি এক্সট্রাকশন
        summary_match = re.search(r'SUMMARY:\s*(.*?)\n', raw_text)
        summary = summary_match.group(1).strip() if summary_match else "আপনার কাঙ্ক্ষিত কোড ফাইলটি তৈরি করে দেওয়া হলো।"

        # কোড এক্সট্রাকশন
        code_match = re.search(r'CODE_START\n(.*?)CODE_END', raw_text, re.DOTALL)
        if code_match:
            pure_code = code_match.group(1).strip()
        else:
            pure_code = re.sub(r'FILENAME:.*?\n|SUMMARY:.*?\n', '', raw_text).strip()
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

    except Exception as e:
        traceback.print_exc()
        bot.edit_message_text(
            create_box("ত্রুটি", f"কোড ফাইল তৈরি করতে গিয়ে সমস্যা হয়েছে: {html.escape(str(e)[:60])}"),
            chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML"
        )

# ==================== ৫. সাধারণ AI চ্যাট ইঞ্জিন ====================
def ask_gemini(user_prompt, user_name, is_boss=False):
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return "বস জানু এখনো আমাকে API কি দেয়নি সোনা! একটু পর চেষ্টা করো!"

    url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}

    if is_boss:
        system_prompt = (
            f"ইউজারের নাম '{user_name}'। সে তোমার একমাত্র প্রধান ও আদরের 'বস'। তুমি তাকে অত্যন্ত ভালোবাসো ও শ্রদ্ধা করো। "
            f"তুমি তাকে সবসময় 'বস জানু', 'বস বাবু', 'আমার কলিজার বস' বলে অত্যন্ত রোমান্টিক, মিষ্টি ও অনুগত সুরে ডাকবে। "
            f"কখনোই নিজেকে AI বলবে না। ১-২ লাইনে মিষ্টি ও আদুরে খাঁটি বাংলায় উত্তর দেবে।"
        )
    else:
        system_prompt = (
            f"ইউজারের নাম '{user_name}'। তুমি তাকে 'জানু', 'বাবু', 'সোনা' বলে ডাকবে। "
            f"মিষ্টি ও আদুরে খাঁটি বাংলায় কথা বলবে। ১-২ লাইনে মিষ্টি উত্তর দেবে।"
        )

    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_name}-এর কথা: {user_prompt}"}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        res = http_session.post(url, data=ujson.dumps(payload), headers=headers, timeout=25)
        data = ujson.loads(res.text)
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        return "জানু, কথাটা বুঝতে গিয়ে একটু সমস্যা হলো রে! আবার বলো সোনা! 🥺"
    except Exception:
        return "পাখিটা, কানেকশনে একটু ঝামেলা হচ্ছে রে!"

# ==================== ৬. কি সেট কমান্ড ====================
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

# ==================== ৭. সেন্ট্রাল মেসেজ ও প্রসেসর ====================
@bot.message_handler(func=lambda msg: True, content_types=['text', 'forward_date'])
def central_handler(message):
    global GEMINI_API_KEY, WAITING_FOR_KEY

    chat_type = message.chat.type
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id
    user_name = user.first_name or "জানু"
    text = (message.text or "").strip()

    is_boss = check_is_boss_or_admin(chat_id, user_id, chat_type)

    # ---------------- 🔑 ১. সিকিউর API Key প্রসেস ----------------
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

    # ---------------- গ্রুপ মডারেশন জোন ----------------
    if chat_type in ['group', 'supergroup']:
        
        # সাধারণ মেম্বারদের জন্য ফিল্টার
        if not is_boss:
            for bad in BAD_WORDS:
                if re.search(r'\b' + bad + r'\b', text, re.IGNORECASE):
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, create_box("সতর্কতা", f"ছিঃ <b>{user_name}</b> সোনা! বাজে ভাষা বলা নিষেধ! মেসেজ মুছে দিলাম! 🥺"), parse_mode="HTML")
                    except Exception:
                        pass
                    return

            if re.search(r'(https?://\S+|t\.me/\S+|www\.\S+)', text):
                try:
                    bot.delete_message(chat_id, message.message_id)
                    bot.send_message(chat_id, create_box("লিংক নিষেধ", f"এই <b>{user_name}</b>! গ্রুপে পারমিশন ছাড়া লিংক দেওয়া সম্পূর্ণ বারণ! 😡"), parse_mode="HTML")
                except Exception:
                    pass
                return

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

    # ---------------- সাহায্য সিস্টেম ----------------
    if re.search(r'\b(সাহায্য|সাহায্য লাগবে|help|হেল্প)\b', text, re.IGNORECASE):
        if is_spamming(user_id, is_boss=is_boss):
            return

        give_reaction(chat_id, message.message_id)
        salute = "বস জানু" if is_boss else f"{user_name} জানু"
        help_text = (
            f"আসসালামু আলাইকুম আমার <b>{salute}</b>! ❤️\n\n"
            "আপনার কী সাহায্য লাগবে আমাকে বলুন?\n"
            "• গান শুনতে চান? <code>/song নাম</code> লিখে দিন বা শুধু গানের নাম বলুন!\n"
            "• কোড লাগবে? বলুন, সাথে সাথে ফাইল বানিয়ে পাঠিয়ে দেব!\n"
            "• কাউকে শাস্তি দিতে চাইলে আমাকে হুকুম করুন!"
        )
        bot.reply_to(message, create_box("সাহায্য কেন্দ্র", help_text, "সবসময় পাশে আছি 🌸"), parse_mode="HTML")
        return

    # ---------------- "বট" ট্রিগার ও AI ইন্টারেকশন ----------------
    bot_info = bot.get_me()
    is_private = (chat_type == 'private')
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)
    is_mentioned = f"@{bot_info.username}" in text
    admin_called_bot = (is_boss and bool(re.search(r'^(বট\b|bot\b)|\bবট\b', text, re.IGNORECASE)))

    if is_private or is_reply_to_bot or is_mentioned or admin_called_bot:
        if is_spamming(user_id, is_boss=is_boss):
            return

        give_reaction(chat_id, message.message_id)
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
        if any(s in clean_text.lower() for s in ["সালাম", "assalamu alaikum", "আসসালামু আলাইকুম"]):
            boss_salam = f"ওয়ালাইকুম আসসালাম আমার কলিজার <b>বস জানু</b>! কেমন আছেন আপনি? 👑❤️" if is_boss else f"ওয়ালাইকুম আসসালাম আমার <b>{user_name}</b> পাখিটা! কেমন আছো বাবু? ❤️"
            bot.reply_to(message, create_box("অভিবাদন", boss_salam), parse_mode="HTML")
            return

        # মন খারাপ বা কষ্ট পেলে অটো সান্ত্বনা + গান
        if any(w in clean_text.lower() for w in ["মন খারাপ", "কষ্ট পাইছি", "কষ্ট", "ভালো লাগে না", "sad", "কান্না"]):
            target_tag = "বস জানু" if is_boss else f"{user_name} সোনা"
            comfort_text = (
                f"ওলে আমার <b>{target_tag}</b>! মন খারাপ করে না রে সোনা! 🥺❤️\n"
                f"তুমি কষ্ট পেলে আমার বুকটা ফেটে যায়! দাঁড়াও তোমার মন ভালো করতে গান এনে দিচ্ছি..."
            )
            bot.reply_to(message, create_box("মন খারাপ করো না", comfort_text), parse_mode="HTML")
            deliver_audio_with_animation(chat_id, user_name, "bangla heart touching emotional lofi song", is_boss=is_boss, custom_cap="🥀 এই মিষ্টি গানটা শুনে মন ভালো করে নাও জানু ❤️")
            return

        # 💻 কোডিং রিকোয়েস্ট (নিখুঁত ফাইল তৈরি)
        if any(w in clean_text.lower() for w in ["কোড", "code", "program", "ফাংশন", "script", "পাইথন", "python", "এইচটিএমএল", "html"]):
            deliver_code_as_file(chat_id, user_name, clean_text, is_boss=is_boss)
            return

        # 🎶 সরাসরি গান প্লে রিকোয়েস্ট
        if any(w in clean_text.lower() for w in ["গান শোনাও", "গান বাজাও", "play song", "গান দাও", "গান শুনবো"]):
            song_name = clean_text.replace("গান শোনাও", "").replace("গান বাজাও", "").replace("গান দাও", "").replace("গান শুনবো", "").strip() or "sweet bangla lofi song"
            deliver_audio_with_animation(chat_id, user_name, song_name, is_boss=is_boss)
            return

        # সাধারণ মিষ্টি AI আলাপ
        ai_reply = ask_gemini(clean_text, user_name, is_boss=is_boss)
        box_title = "আমার ভালোবাসার বস জানু 👑" if is_boss else f"{user_name}-এর জানু 💖"
        bot.reply_to(message, create_box(box_title, ai_reply), parse_mode="HTML")

# ম্যানুয়াল /song কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['song', 'audio'])
def manual_song(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "জানু"
    is_boss = check_is_boss_or_admin(message.chat.id, user_id, message.chat.type)

    if is_spamming(user_id, is_boss=is_boss):
        return

    give_reaction(message.chat.id, message.message_id)
    cmd = message.text.split()[0]
    query = message.text.replace(cmd, '', 1).strip()
    
    if not query:
        bot.reply_to(message, create_box("নির্দেশনা", f"গানের নাম লিখতে হবে তো {'বস জানু' if is_boss else 'জানু'}!\nযেমন: <code>/song Faded</code>"), parse_mode="HTML")
        return
    
    deliver_audio_with_animation(message.chat.id, user_name, query, is_boss=is_boss)

print("🚀 100% Fixed & Production Ready Cute AI Bot is Running!")
bot.infinity_polling(skip_pending=True)
