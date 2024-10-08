import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from colorama import Fore, Style, init
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName, User, Channel, Chat
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import UserStatusEmpty, UserStatusOnline, UserStatusOffline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
from telethon.tl.types import User, Channel
from telethon.tl.types import DocumentAttributeFilename
from dotenv import load_dotenv
from telethon.tl.types import MessageMediaPhoto
# import pytesseract
import io
from PIL import Image
import os
import json
import requests
import openai
from datetime import datetime, time, timedelta
import qrcode
import asyncio
import subprocess
import re
import random
from transformers import BlipProcessor, BlipForConditionalGeneration
# import whisper

# Initialize colorama
init(autoreset=True)

# Load biến môi trường từ tệp .env
load_dotenv()

# Thông tin đăng nhập cho tài khoản Telegram
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE_NUMBER')
target_user = os.getenv('TARGET_USER')
api_chatgpt = os.getenv('API_CHATGPT')


# Vẽ vời
max_daily_drawings = 2

# RESET LƯỢT VẼ
last_reset_date = None

# Biến tạm để lưu ID của người dùng hiện đang sử dụng lệnh /ve
current_user = None

# Hàng đợi để lưu trữ ID của người dùng đang chờ
queue = []

# Kiểm tra xem các biến môi trường có được nạp đúng không
print(f"\033[36mAPI ID: \033[33m{api_id}\033[0m")
print(f"\033[36mAPI Hash: \033[33m{api_hash}\033[0m")
print(f"\033[36mPhone Number: \033[33m{phone}\033[0m")
print(f"\033[36mTarget User: \033[33m{target_user}\033[0m")
print(f"\033[36mAPI GPT: \033[33m{api_chatgpt}\033[0m")

# Tạo client cho tài khoản trên máy tính
client = TelegramClient('kakalot5678', api_id, api_hash)

# Đường dẫn tới tệp JSON
settings_file = 'settings.json'
ve_usage_file = 've_usage.json'

# Hàm tải danh sách từ tệp JSON
def load_settings():
    try:
        with open(settings_file, 'r') as f:
            data = json.load(f)
            return data['excluded_users'], data['allowed_groups']
    except FileNotFoundError:
        return [], {}

def load_ve_usage():
    try:
        with open(ve_usage_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Hàm lưu danh sách vào tệp JSON
def save_settings(excluded_users, allowed_groups):
    with open(settings_file, 'w') as f:
        json.dump({'excluded_users': excluded_users, 'allowed_groups': allowed_groups}, f, indent=4)

def save_ve_usage(ve_usage):
    with open(ve_usage_file, 'w') as f:
        json.dump(ve_usage, f, indent=4)

# Tải danh sách loại trừ và nhóm được phép
excluded_users, allowed_groups = load_settings()
ve_usage = load_ve_usage()

# Rs lượt vẽ
def reset_daily_usage():
    global ve_usage, last_reset_date
    current_date = datetime.now().date()

    if last_reset_date is None or last_reset_date != current_date:
        # Reset tất cả các người dùng về số lượt mặc định mỗi ngày theo max_daily_drawings
        for user in ve_usage:
            ve_usage[user] = max(ve_usage.get(user, 0), 0)  # Đảm bảo không có số âm
        last_reset_date = current_date
        save_ve_usage(ve_usage)
        print(f"\033[1;32mLượt sử dụng lệnh /ve đã được reset cho ngày mới ({current_date}) về {max_daily_drawings}.\033[0m")
        
# -----------------------------------------------------------------------
# Biến lưu trữ thời gian bắt đầu và kết thúc mặc định
default_start_time = time(22, 30)  # 22:30
default_end_time = time(12, 0)     # 12:00

# Biến lưu trữ thời gian hiện tại cho start_time và end_time
start_time = default_start_time
end_time = default_end_time

# Hàm kiểm tra xem thời gian hiện tại có trong khoảng cho phép không
def is_within_allowed_hours():
    current_time = datetime.now().time()
    return start_time <= current_time or current_time <= end_time

# Lệnh /on: thiết lập thời gian hoạt động về mặc định
async def handle_on_command(sender_id, sender_name, sender_username):
    global start_time, end_time
    if sender_username == target_user:
        start_time = default_start_time
        end_time = default_end_time
        await client.send_message(target_user, "<b>Bot</b> đã được bật, thời gian hoạt động từ <b>12:00</b> đến <b>22:30</b>.", parse_mode='html')
        
        print(f"\033[1;32mBOT is back to work.\033[0m")
    else:
        await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
        # Gửi thông báo cho target_user
        await client.send_message(
            target_user, 
            f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name}</b> (@{sender_username}) đang lạm dụng lệnh <b>/on</b>. Tôi đã ngăn chặn thành công!", 
            parse_mode='html'
        )

# Lệnh /off: thiết lập thời gian hoạt động theo thời gian hiện tại
async def handle_off_command(sender_id, sender_name, sender_username):
    global start_time, end_time
    if sender_username == target_user:
        start_time = time.min  # Đặt giờ bắt đầu thành 00:00
        end_time = time.max  # Đặt giờ kết thúc thành 23:59:59
        await client.send_message(target_user, f"<b>Bot</b> hiện không bị giới hạn thời gian hoạt động.", parse_mode='html')
        
        print(f"{Fore.RED}BOT stops working.")
    else:
        await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
        # Gửi thông báo cho target_user
        await client.send_message(
            target_user, 
            f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name}</b> (@{sender_username}) đang lạm dụng lệnh <b>/off</b>. Tôi đã ngăn chặn thành công!", 
            parse_mode='html'
        )

# -----------------------------------------------------------------------
# Load the Whisper model
# whisper_model = whisper.load_model("medium")

# Biến toàn cục để lưu trạng thái lắng nghe
# is_listening = False
        
# Load model BLIP từ Hugging Face
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Hàm xử lý lệnh getpic
async def handle_getpic_command(event):
    if not event.message.media:
        await event.reply("Vui lòng gửi kèm một hình ảnh để tôi có thể tạo prompt cho bạn.")
        return

    # Tải ảnh từ tin nhắn
    photo_path = await event.message.download_media()
    image = Image.open(photo_path).convert("RGB")

    # Sử dụng BLIP để tạo prompt
    inputs = processor(images=image, return_tensors="pt")
    out = model.generate(**inputs)
    prompt = processor.decode(out[0], skip_special_tokens=True)
    
    # Gửi prompt tới người dùng
    await event.reply(f"Đây là prompt bạn có thể sử dụng: `{prompt}`")

    # Xóa ảnh sau khi đã xử lý xong
    try:
        os.remove(photo_path)
        print(f"File {photo_path} đã được xóa thành công.")
    except Exception as e:
        print(f"Không thể xóa file {photo_path}: {e}")
    
# Hàm xử lý lệnh được gọi bởi sự kiện
@client.on(events.NewMessage)
async def handle_command(event):
    # global is_listening  # Đảm bảo khai báo biến toàn cục trước khi sử dụng
    global bot_name
    
    sender = await event.get_sender()
    sender_id = sender.id
    
    # Kiểm tra loại người gửi: User, Channel hoặc Group
    if isinstance(sender, User):
        sender_name = f"{sender.first_name} {sender.last_name}".strip()
        sender_username = sender.username if sender.username else "Unknown"
    elif isinstance(sender, (Channel, Chat)):
        sender_name = sender.title
        sender_username = sender.username if sender.username else "Unknown"
    else:
        sender_name = "Unknown"
        sender_username = "Unknown"
    
    # Nếu lệnh là /on hoặc /off, xử lý đặc biệt
    if event.message.message == '/on':
        await handle_on_command(sender_id, sender_name, sender_username)
        return
    elif event.message.message == '/off':
        await handle_off_command(sender_id, sender_name, sender_username)
        return
    
    # Kiểm tra thời gian hoạt động trước khi xử lý lệnh
    if not is_within_allowed_hours() and not event.message.message.startswith((
        '/on', '/off', '/ve', '/xoa', '/clear', '/listuser', 
        '/adduser', '/showuser', '/deluser', '/listgroup', 
        '/addgroup', '/showgroup', '/delgroup', '/hat', 
        '/spam', '/checkve', '/addve', '/donate', '/sd', '/check', '/tuvi', '/getpic', '/getvoice', '/outvoice'
    )):
        print(f"{Fore.RED}Outside of active hours. Ignoring message.")
        return

    print(f"{Fore.GREEN}Detected a management command or within allowed hours. Processing command.")

    # Xử lý lệnh getpic
    if event.message.message.startswith('/getpic'):
        await handle_getpic_command(event)
        return
    
    # Xử lý lệnh vẽ
    if event.message.message.startswith('/ve '):
        reset_daily_usage()  # Reset nếu cần trước khi xử lý lệnh
        prompt = event.message.message[4:]
        user_usage = ve_usage.get(sender_username, max_daily_drawings)
        
        if sender_username == target_user or user_usage > 0:
            if sender_username != target_user:
                ve_usage[sender_username] = max(user_usage - 1, 0)  # Giảm số lượt và đảm bảo không âm
                save_ve_usage(ve_usage)

            await handle_ve_command(sender_id, sender_username, prompt, event)

        else:
            me = await client.get_me()
            bot_name = f"{me.first_name} {me.last_name or ''}".strip()
            await client.send_message(sender_id, f"Bạn đã sử dụng hết <b>{max_daily_drawings}</b> lượt vẽ hôm nay, vui lòng liên hệ <b>{bot_name}</b> để mở thêm.", parse_mode='html')
        return

    # Xử lý lệnh /donate
    if event.message.message == '/donate':
        print(f"{Fore.BLUE}Received /donate command.")
        
        # Xử lý tên người gửi để tránh hiển thị "None"
        first_name = sender.first_name or ""
        last_name = sender.last_name or ""
        sender_name_display = f"{first_name} {last_name}".strip()

        # Chỉ gửi thông báo cho target_user nếu người gửi không phải là target_user
        if sender_username != target_user:
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) vừa sử dụng lệnh <b>/DONATE!</b>", 
                parse_mode='html'
            )
            
        try:
            donate_message = (
                f"Chào <b>{sender_name_display}</b> nhé, sự đóng góp của bạn luôn tạo ra sức mạnh giúp mình thêm nhiều sáng tạo mới hơn.\n\n"
                "Đây là thông tin chuyển khoản của tôi\n"
                "STK: <b>9696 186 88888</b>\n"
                "TÊN TK: <b>DANG TUNG ANH</b>\n"
                "BANK: <b>MBBANK</b>\n"
                "Cảm ơn bạn đã sử dụng BOT by TAK\n\n"
            )

            qr_path = "catak_qr.png"  # Sử dụng ảnh QR có sẵn
        except Exception as e:
            print(f"{Fore.RED}Error creating message or loading QR image: {e}")
            await client.send_message(sender_id, "Xin lỗi, đã có lỗi xảy ra khi tải ảnh QR.")
            return
        
        try:
            await client.send_file(
                sender_id,
                qr_path,
                caption=donate_message,
                parse_mode='html',
                attributes=[DocumentAttributeFilename('catak_qr.png')]  # Đặt tên file
            )
        except Exception as e:
            print(f"{Fore.RED}Error sending message: {e}")
            await client.send_message(sender_id, "Xin lỗi, đã có lỗi xảy ra khi gửi tin nhắn donate.")
        return


    # Check lượt sử dụng vẽ
    if event.message.message == '/checkve':
        reset_daily_usage()  # Reset nếu cần trước khi kiểm tra lượt
        user_usage = ve_usage.get(sender_username, max_daily_drawings)

        if sender_username == target_user:
            await client.send_message(sender_id, "Bạn không giới hạn lượt sử dụng.")
        else:
            remaining_usage = max(user_usage, 0)  # Đảm bảo không có số âm
            await client.send_message(sender_id, f"Bạn còn <b>{remaining_usage}</b> lượt sử dụng.", parse_mode='html')
        return

    # Xử lý lệnh /addve @user {số lượt}
    if event.message.message.startswith('/addve '):
        if sender_username != target_user:
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()

            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/addve</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        parts = event.message.message.split()
        if len(parts) == 3:
            user_to_add = parts[1].lstrip('@')
            add_amount = int(parts[2])

            # Kiểm tra nếu người dùng đã có trong ve_usage, nếu không thì khởi tạo với giá trị max_daily_drawings
            if user_to_add not in ve_usage:
                ve_usage[user_to_add] = max_daily_drawings

            # Cộng thêm lượt sử dụng vào số lượt hiện tại
            ve_usage[user_to_add] = max(ve_usage[user_to_add] + add_amount, 0)  # Đảm bảo không bao giờ âm

            save_ve_usage(ve_usage)

            # Lấy thông tin người dùng được thêm lượt
            user_entity = await client.get_entity(user_to_add)
            user_first_name = user_entity.first_name or ""
            user_last_name = user_entity.last_name or ""
            name_display = f"{user_first_name} {user_last_name}".strip()

            me = await client.get_me()
            bot_name = f"{me.first_name} {me.last_name or ''}".strip()

            await client.send_message(sender_id, f"Bạn đã thêm <b>{add_amount}</b> lượt sử dụng lệnh <b>/ve</b> cho <b>{name_display}</b> (@{user_to_add}) thành công.", parse_mode='html')
            await client.send_message(user_to_add, f"Chào bạn <b>{bot_name}</b> vừa thêm cho bạn <b>{add_amount}</b> lượt sử dụng lệnh <b>/ve</b> để vẽ tranh rồi đó. Kiểm tra <b>/checkve</b> để xem số lượt bạn còn nhé!", parse_mode='html')
        return

    # Xử lý lệnh /hat {lyric} @user
    if event.message.message.startswith('/hat '):
        print(f"\033[33mReceived /hat command.\033[0m")

        if sender_username != target_user:
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()

            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user,
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/hat</b>. Tôi đã ngăn chặn thành công!",
                parse_mode='html'
            )
            return

        try:
            command_content = event.message.message[5:].strip()
            at_index = command_content.rfind('@')
            if at_index == -1:
                await client.send_message(target_user, "Cú pháp không đúng. Vui lòng sử dụng cú pháp: /hat {lyric} @user hoặc /hat {lyric} @id_nhóm")
                return

            lyric = command_content[:at_index].strip()
            recipient_identifier = command_content[at_index + 1:].strip()

            # Xác định nếu recipient_identifier là một ID nhóm hay username
            try:
                recipient_id = int(recipient_identifier)
                is_group = True
            except ValueError:
                recipient_id = None
                is_group = False

            if is_group:
                if str(recipient_id) not in allowed_groups:
                    await client.send_message(target_user, "ID nhóm không hợp lệ hoặc bạn không có quyền gửi tin nhắn vào nhóm.")
                    return
                
                chat = await client.get_entity(recipient_id)
                chat_title = chat.title

                sent_message = None
                full_message = ""

                lines = lyric.split('\n')
                for line in lines:
                    words = line.split()
                    current_message = ""

                    for word in words:
                        current_message += word + " "
                        updated_message = full_message + current_message.strip() + "\u200B"  # Thêm ký tự vô hình

                        if sent_message is None:
                            sent_message = await client.send_message(recipient_id, updated_message)
                        else:
                            await sent_message.edit(updated_message)

                        await asyncio.sleep(1.0)

                    full_message += current_message.strip() + "\n"
                    await asyncio.sleep(2)

                print(f"\033[32mSent text to group \033[1;33m{chat_title} (@{recipient_identifier})\033[0;32m successfully.\033[0m")
                await client.send_message(target_user, f"Đã gửi xong văn bản tới nhóm <b>{chat_title}</b> (@{recipient_identifier}).", parse_mode='html')

                # Xóa văn bản sau khi hoàn tất
                await sent_message.delete()

                # Gửi lại hình ảnh hoặc video (nếu có) sau khi văn bản bị xóa
                if event.message.media:
                    sent_file_message = await client.send_file(
                        recipient_id,
                        event.message.media,
                        caption=lyric
                    )

                    # Xóa tin nhắn chứa hình ảnh hoặc video sau 10 giây
                    await asyncio.sleep(15)
                    await sent_file_message.delete()

            else:
                recipient = await client.get_entity(recipient_identifier)
                if not recipient:
                    await client.send_message(target_user, "Không tìm thấy người dùng.")
                    return

                full_name = f"{recipient.first_name} {recipient.last_name or ''}".strip()

                sent_message = None
                full_message = ""

                lines = lyric.split('\n')
                for line in lines:
                    words = line.split()
                    current_message = ""

                    for word in words:
                        current_message += word + " "
                        updated_message = full_message + current_message.strip() + "\u200B"  # Thêm ký tự vô hình

                        if sent_message is None:
                            sent_message = await client.send_message(recipient.id, updated_message)
                        else:
                            await sent_message.edit(updated_message)

                        await asyncio.sleep(random.uniform(0.2, 1.0))

                    full_message += current_message.strip() + "\n"
                    await asyncio.sleep(2)

                print(f"\033[32mSent text to \033[1;33m@{recipient_identifier}\033[0;32m successfully.\033[0m")
                await client.send_message(target_user, f"Đã gửi xong văn bản tới <b>{full_name}</b> (@{recipient_identifier}).", parse_mode='html')

                # Xóa văn bản sau khi hoàn tất
                await sent_message.delete()

                # Gửi lại hình ảnh hoặc video (nếu có) sau khi văn bản bị xóa
                if event.message.media:
                    sent_file_message = await client.send_file(
                        recipient.id,
                        event.message.media,
                        caption=lyric
                    )

                    # Xóa tin nhắn chứa hình ảnh hoặc video sau 10 giây
                    await asyncio.sleep(15)
                    await sent_file_message.delete()

        except Exception as e:
            print(f"\033[31mError in /hat command: {e}\033[0m")
            await client.send_message(target_user, f"Có lỗi xảy ra khi thực hiện lệnh: {e}")
        return
    
    # Xử lý lệnh /xoa @user
    if event.message.message.startswith('/xoa '):
        print(f"{Fore.RED}Received /xoa command.")
        
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/xoa @</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        try:
            target_user_to_delete = event.message.message.split(' ')[1].lstrip('@')
            user_entity = await client.get_entity(target_user_to_delete)
            await client.delete_dialog(user_entity.id, revoke=True)

            full_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()

            print(f"\033[32mDeleted the entire chat with \033[1;31m@{target_user_to_delete}\033[0m.")
            await client.send_message(
                target_user, 
                f"Successfully deleted the conversation with <b>{full_name}</b> (@{target_user_to_delete}).", 
                parse_mode='html'
            )
        except Exception as e:
            print(f"\033[31mFailed to delete chat with \033[1;33m@{target_user_to_delete}\033[0;31m: {e}\033[0m")
        return

    # Xử lý lệnh /xoa
    if event.message.message == '/xoa':
        print(f"{Fore.RED}Received /xoa command to delete all messages.")
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/xoa</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        try:
            await client.delete_dialog(sender_username, revoke=True)
            print(f"\033[32mDeleted the entire chat with \033[1;31m{sender_username}\033[0;32m.\033[0m")
        except Exception as e:
            print(f"\033[31mFailed to delete chat with \033[1;33m{sender_username}\033[0;31m: \033[1;33m{e}\033[0m")
        return

    # Xử lý lệnh /clear @user
    if event.message.message.startswith('/clear '):
        print(f"{Fore.YELLOW}Received /clear command.")
        
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
        
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/clear @</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        target_user_to_clear = event.message.message.split(' ')[1].lstrip('@')
        
        try:
            user_entity = await client.get_entity(target_user_to_clear)
            full_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
            
            async for message in client.iter_messages(target_user_to_clear):
                await client.delete_messages(target_user_to_clear, message.id, revoke=False)
            
            print(f"\033[32mCleared the entire messenger with \033[1;31m{full_name}\033[0;32m.\033[0m")
            await client.send_message(
                target_user, 
                f"Successfully cleared the messenger with <b>{full_name}</b> (@{target_user_to_clear}).", 
                parse_mode='html'
            )
        except Exception as e:
            print(f"\033[31mFailed to clear messenger with \033[1;33m@{target_user_to_clear}\033[0;31m: {e}\033[0m")
        return

    # Xử lý lệnh /clear
    if event.message.message == '/clear':
        print(f"{Fore.YELLOW}Received /clear command to delete all messages.")
        if sender_username != target_user:
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Xử lý để loại bỏ "None"
            sender_first_name = sender.first_name or ""
            sender_last_name = sender.last_name or ""
            sender_name_display = f"{sender_first_name} {sender_last_name}".strip()

            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/clear</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        async for message in client.iter_messages(sender_username):
            await client.delete_messages(sender_username, message.id, revoke=False)
        return

    # Xử lý lệnh /spam @user
    if event.message.message.startswith('/spam '):
        print(f"{Fore.RED}Received /spam command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            
            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/spam</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        target_to_spam = event.message.message.split(' ')[1].lstrip('@')

        try:
            target_id = int(target_to_spam)
            is_group = True
        except ValueError:
            is_group = False

        try:
            # Sử dụng trực tiếp client.get_entity để lấy entity của người dùng hoặc nhóm
            if is_group:
                entity = await client.get_entity(target_id)
            else:
                entity = await client.get_entity(target_to_spam)

            if entity:
                sticker_set_name = 'ingusan'
                sticker_set_response = await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name=sticker_set_name), hash=0))

                if hasattr(sticker_set_response, 'documents'):
                    stickers = sticker_set_response.documents
                    stickers.reverse()  # Đảo ngược danh sách sticker để gửi từ dưới lên trên

                    for sticker in stickers:
                        try:
                            await client.send_file(entity.id, sticker, delay=0.01)
                        except Exception as e:
                            print(f"\033[31mFailed to send a sticker to \033[1;33m{target_to_spam}\033[0;31m: \033[1;33m{e}\033[0m")

                    # Lấy tên người dùng và username để gửi thông báo
                    user_name = f"{entity.first_name} {entity.last_name or ''}".strip()
                    user_username = entity.username
                    await client.send_message(target_user, f"Đã gửi sticker tới <b>{user_name} (@{user_username})</b> thành công.", parse_mode='html')

                    print(f"\033[32mSpammed \033[1;33m{target_to_spam}\033[0;32m with stickers.\033[0m")
                else:
                    print(f"{Fore.RED}No documents found in the sticker set.")
            else:
                print(f"\033[31mTarget \033[1;33m{target_to_spam}\033[0;31m is not a valid user or group.\033[0m")
        except Exception as e:
            print(f"{Fore.RED}Error occurred: {e}")

        return

    # Xử lý lệnh /delgroup <group_id>
    if event.message.message.startswith('/delgroup '):
        print(f"{Fore.RED}Received /delgroup command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/delgroup</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        try:
            # Loại bỏ ký tự "@" nếu có
            group_id_str = event.message.message.split(' ')[1].lstrip('@')
            group_id = int(group_id_str)  # Chuyển thành số nguyên
            
            group_id_str = str(group_id)
            if group_id_str in allowed_groups:
                group_name = allowed_groups[group_id_str]
                del allowed_groups[group_id_str]
                save_settings(excluded_users, allowed_groups)
                print(f"\033[32mRemoved group \033[1;33m{group_name}\033[0;32m (\033[1;33m{group_id}\033[0;32m) from allowed groups.\033[0m")
                await client.send_message(target_user, f"Đã xóa nhóm <b>{group_name}</b> (@{group_id}) thành công.", parse_mode='html')
            else:
                await client.send_message(target_user, f"Nhóm với ID <b>{group_id}</b> không có trong danh sách cho phép.", parse_mode='html')
        
        except ValueError:
            await client.send_message(target_user, "ID nhóm không hợp lệ. Vui lòng kiểm tra lại.")
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            await client.send_message(target_user, f"Đã xảy ra lỗi khi xóa nhóm. Vui lòng kiểm tra lại ID hoặc thử lại sau.")
        
        return
    
    # Xử lý lệnh /showgroup
    if event.message.message == '/showgroup':
        print(f"{Fore.BLUE}Received /showgroup command.")

        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/showgroup</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        group_list = [f"{idx + 1}. {group_name} (@{group_id})" for idx, (group_id, group_name) in enumerate(allowed_groups.items())]
        
        if group_list:
            message = "Danh sách nhóm:\n" + "\n".join(group_list)
        else:
            message = "Danh sách nhóm không có."
        
        await client.send_message(target_user, message)
        return
    
    # Xử lý lệnh /addgroup <group_id>
    if event.message.message.startswith('/addgroup '):
        print(f"{Fore.GREEN}Received /addgroup command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/addgroup</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        parts = event.message.message.split(' ', 2)
        
        if len(parts) >= 2:
            try:
                # Loại bỏ ký tự "@" nếu có
                group_id_str = parts[1].lstrip('@')
                group_id = int(group_id_str)  # Chuyển thành số nguyên

                entity = await client.get_entity(group_id)  # Lấy thông tin từ ID

                # Kiểm tra nếu ID là của một nhóm
                if isinstance(entity, (Chat, Channel)):
                    group_name = entity.title
                    allowed_groups[str(group_id)] = group_name
                    save_settings(excluded_users, allowed_groups)
                    print(f"\033[32mAdded group \033[1;33m{group_name}\033[0;32m (\033[1;33m{group_id}\033[0;32m) to allowed groups.\033[0m")
                    await client.send_message(target_user, f"Đã thêm nhóm <b>{group_name}</b> (@{group_id}) thành công.", parse_mode='html')
                else:
                    await client.send_message(target_user, f"ID (<b>{group_id}</b>) không phải là một nhóm hợp lệ.", parse_mode='html')
            
            except ValueError:
                await client.send_message(target_user, "ID nhóm không hợp lệ. Vui lòng kiểm tra lại.")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}")
                await client.send_message(target_user, f"Không thể tìm thấy nhóm với ID: {group_id}. Vui lòng kiểm tra lại.")
        
        return
    
    # Xử lý lệnh /listgroup
    if event.message.message == '/listgroup':
        print(f"{Fore.CYAN}Received /listgroup command.")

        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/listgroup</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        group_list = []
        message = "Danh sách nhóm:\n"
        max_message_length = 4096  # Giới hạn ký tự của một tin nhắn Telegram là 4096 ký tự

        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, (Chat, Channel)):
                group_entry = f"{len(group_list) + 1}. {entity.title} (@{entity.id})"
                
                # Kiểm tra nếu thêm nhóm này có vượt quá giới hạn ký tự không
                if len(message) + len(group_entry) + 1 > max_message_length:
                    await client.send_message(target_user, message)  # Gửi tin nhắn hiện tại
                    message = "Danh sách nhóm (tiếp tục):\n"  # Bắt đầu tin nhắn mới
                    
                group_list.append(group_entry)
                message += group_entry + "\n"

        if len(group_list) > 0:
            await client.send_message(target_user, message)  # Gửi tin nhắn cuối cùng
        else:
            await client.send_message(target_user, "Không có nhóm nào trong danh sách.")

        # Xóa toàn bộ lịch sử tin nhắn trong cuộc trò chuyện
        await client.delete_dialog(target_user)
        
        return
    
    # Xử lý lệnh /deluser @user
    if event.message.message.startswith('/deluser '):
        print(f"{Fore.RED}Received /deluser command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/deluser</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return
        
        # Proceed with removing the user from the excluded list
        user_to_include = event.message.message.split(' ')[1].lstrip('@')
        
        if user_to_include in excluded_users:
            excluded_users.remove(user_to_include)
            save_settings(excluded_users, allowed_groups)
            print(f"{Fore.GREEN}Removed {user_to_include} from excluded users.")
            
            # Lấy thông tin người dùng
            try:
                user_entity = await client.get_entity(user_to_include)
                user_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
            except Exception as e:
                print(f"{Fore.RED}Error retrieving user info: {e}")
                user_name = user_to_include  # Sử dụng username nếu không lấy được tên
            
            await client.send_message(target_user, f"Bạn đã xóa <b>{user_name}</b> (@{user_to_include}) ra khỏi danh sách loại trừ thành công.", parse_mode='html')
        else:
            await client.send_message(target_user, f"Người dùng (<b>@{user_to_include}</b>) không có trong danh sách loại trừ.", parse_mode='html')
        
        return

    # Xử lý lệnh /showuser
    if event.message.message == '/showuser':
        print(f"{Fore.CYAN}Received /showuser command.")

        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/showuser</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        user_list = []

        # Lấy tên đầy đủ và username của mỗi người dùng trong danh sách loại trừ
        for idx, user in enumerate(excluded_users):
            try:
                user_entity = await client.get_entity(user)
                user_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
                user_list.append(f"{idx + 1}. {user_name} (@{user})")
            except Exception as e:
                print(f"{Fore.RED}Error retrieving user info: {e}")
                user_list.append(f"{idx + 1}. @{user}")  # Trường hợp không lấy được thông tin người dùng
        
        if user_list:
            message = "Danh sách user:\n" + "\n".join(user_list)
        else:
            message = "Danh sách người dùng không có."
        
        await client.send_message(target_user, message)
        return

    # Xử lý lệnh /adduser @user
    if event.message.message.startswith('/adduser '):
        print(f"{Fore.GREEN}Received /adduser command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/adduser</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return
        
        # Proceed with adding the user to the excluded list
        user_to_exclude = event.message.message.split(' ')[1].lstrip('@')
        if user_to_exclude not in excluded_users:
            excluded_users.append(user_to_exclude)
            save_settings(excluded_users, allowed_groups)
            print(f"\033[32mAdded \033[1;33m{user_to_exclude}\033[0;32m to excluded users.\033[0m")
            
            # Lấy thông tin người dùng
            try:
                user_entity = await client.get_entity(user_to_exclude)
                user_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
            except Exception as e:
                print(f"{Fore.RED}Error retrieving user info: {e}")
                user_name = user_to_exclude  # Sử dụng username nếu không lấy được tên
            
            await client.send_message(target_user, f"Đã thêm <b>{user_name}</b> (@{user_to_exclude}) thành công vào danh sách loại trừ.", parse_mode='html')
        else:
            await client.send_message(target_user, f"Người dùng (<b>@{user_to_exclude}</b>) đã có trong danh sách loại trừ.", parse_mode='html')
        
        return

    # Xử lý lệnh /listuser
    if event.message.message == '/listuser':
        print(f"{Fore.CYAN}Received /listuser command.")

        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")

            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/listuser</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        user_list = []
        message = ""
        max_message_length = 4096  # Giới hạn ký tự của một tin nhắn Telegram là 4096 ký tự

        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, User) and not entity.bot:
                username = entity.username
                if username:
                    user_name = f"{entity.first_name} {entity.last_name or ''}".strip()
                    user_entry = f"{len(user_list) + 1}. {user_name} (@{username})"
                    
                    # Kiểm tra nếu thêm người dùng này có vượt quá giới hạn ký tự không
                    if len(message) + len(user_entry) + 1 > max_message_length:
                        await client.send_message(target_user, message)  # Gửi tin nhắn hiện tại
                        message = ""  # Bắt đầu tin nhắn mới
                    
                    user_list.append(user_entry)
                    message += user_entry + "\n"

        if message:
            await client.send_message(target_user, message)  # Gửi tin nhắn cuối cùng
        else:
            await client.send_message(target_user, "Không có người dùng nào trong danh sách.")

        # Xóa toàn bộ lịch sử tin nhắn trong cuộc trò chuyện
        await client.delete_dialog(target_user)

        return

    # Kiểm tra xem tin nhắn có phải là lệnh /check hay không
    if event.message.message.startswith('/check '):
        print(f"\033[34mReceived /check command.\033[0m")
        
        # Kiểm tra xem người gửi có phải là target_user không
        if sender_username != target_user:
            
            # Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/check</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        try:
            # Lấy username từ lệnh
            user_to_check = event.message.message.split(' ')[1].lstrip('@')
            
            # Lấy thông tin người dùng
            user_entity = await client.get_entity(user_to_check)
            full_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
            username = user_entity.username
            user_id = user_entity.id
            status = user_entity.status

            # Kiểm tra trạng thái online/offline
            if isinstance(status, UserStatusOnline):
                user_status = "Online"
            elif isinstance(status, UserStatusOffline):
                user_status = f"Offline (last seen {status.was_online})"
            elif isinstance(status, UserStatusRecently):
                user_status = "Recently Online"
            elif isinstance(status, UserStatusLastWeek):
                user_status = "Last seen within a week"
            elif isinstance(status, UserStatusLastMonth):
                user_status = "Last seen within a month"
            else:
                user_status = "Unknown"

            # Lấy thông tin chi tiết về người dùng
            full_user_info = await client(GetFullUserRequest(user_id))
            user_bio = full_user_info.full_user.about if hasattr(full_user_info.full_user, 'about') else "Không có"
            phone_number = full_user_info.full_user.phone if hasattr(full_user_info.full_user, 'phone') else "Không có"
            
            # Lấy ngày tháng năm sinh (nếu có)
            birth_date = full_user_info.full_user.birth_date if hasattr(full_user_info.full_user, 'birth_date') else "Không có"

            # In thông tin ra console
            print(f"\033[34mUser ID: \033[1;36m{user_id}\033[0m")
            print(f"\033[34mFull Name: \033[1;36m{full_name}\033[0m")
            print(f"\033[34mUsername: \033[1;36m@{username}\033[0m")
            print(f"\033[34mStatus: \033[1;36m{user_status}\033[0m")
            print(f"\033[34mBio: \033[1;36m{user_bio}\033[0m")
            print(f"\033[34mPhone Number: \033[1;36m{phone_number}\033[0m")
            print(f"\033[34mBirth Date: \033[1;36m{birth_date}\033[0m")

            # Gửi thông tin này đến target_user
            await client.send_message(
                target_user, 
                f"Thông tin người dùng:\n\n"
                f"ID: <code>{user_id}</code></b>\n"
                f"Tên đầy đủ: <b>{full_name}</b>\n"
                f"Username: <b>@{username}</b>\n"
                f"Trạng thái: <b>{user_status}</b>\n"
                f"Bio: <b>{user_bio}</b>\n"
                f"Số điện thoại: <code>{phone_number}</code>\n"
                f"Ngày sinh: <code>{birth_date}</code>\n",  # Thêm ngày tháng năm sinh
                parse_mode='html'
            )
            
        except Exception as e:
            print(f"\033[31mError retrieving user info: {e}\033[0m")
            await client.send_message(target_user, f"Không thể lấy thông tin người dùng: {e}")

        return

    
    # Show chức năng /sd
    if event.message.message == '/sd':
        print(f"{Fore.YELLOW}Received /sd command.")
        
        # Check if the command is issued by the target_user
        if sender_username != target_user:
            
            #Xử lý tên người gửi để tránh hiển thị "None"
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            sender_name_display = f"{first_name} {last_name}".strip()
            
            await client.send_message(sender_id, "Xin lỗi bạn không đủ quyền vận hành.")
            
            # Notify the target_user about the unauthorized attempt
            await client.send_message(
                target_user, 
                f"<b>THÔNG BÁO</b>\nNgười dùng <b>{sender_name_display}</b> (@{sender_username}) đang lạm dụng lệnh <b>/sd</b>. Tôi đã ngăn chặn thành công!", 
                parse_mode='html'
            )
            return

        sd_message = (
            "Chức năng hiện tại của BOT:\n\n"
            "1. <b>/xoa</b>: Xóa toàn bộ cuộc trò chuyện giữa bạn và bot từ cả hai phía.\n"
            "   <b>/xoa @user</b>: Xóa toàn bộ cuộc trò chuyện giữa bot và người dùng được chỉ định từ cả hai phía.\n\n"
            "2. <b>/clear</b>: Xóa toàn bộ lịch sử trò chuyện giữa bạn và bot từ phía bot.\n"
            "   <b>/clear @user</b>: Xóa toàn bộ lịch sử trò chuyện giữa bot và người dùng được chỉ định từ phía bot.\n\n"
            "3. <b>/adduser @user</b>: Thêm người dùng vào danh sách loại trừ, bot sẽ không tương tác với người dùng này.\n"
            "   <b>/deluser @user</b>: Xóa người dùng khỏi danh sách loại trừ.\n\n"
            "4. <b>/addgroup @id_group Tên nhóm</b>: Thêm nhóm vào danh sách cho phép, bot sẽ lắng nghe và tương tác trong nhóm này.\n"
            "   <b>/delgroup @id_group</b>: Xóa nhóm khỏi danh sách cho phép.\n\n"
            "5. <b>/listuser</b>: Hiển thị danh sách tất cả các người dùng mà bot có tương tác.\n"
            "   <b>/listgroup</b>: Hiển thị danh sách tất cả các nhóm mà bot tham gia.\n\n"
            "6. <b>/showuser</b>: Hiển thị danh sách các người dùng trong danh sách loại trừ.\n"
            "   <b>/showgroup</b>: Hiển thị danh sách các nhóm trong danh sách cho phép.\n\n"
            "7. <b>/on</b>: Bật bot và thiết lập thời gian hoạt động từ 12:00 đến 22:30.\n"
            "   <b>/off</b>: Tạm dừng bot và thiết lập thời gian hoạt động theo giờ hiện tại.\n\n"
            "8. <b>/ve {prompt}</b>: Tạo tranh dựa trên nội dung được cung cấp. Mỗi người dùng có số lượt vẽ giới hạn mỗi ngày. Nếu đã hết lượt, hãy liên hệ với TAK để mở thêm.\n\n"
            "9. <b>/hat {lyric} @user</b>: Gửi lyric tới người dùng, từng từ sẽ xuất hiện tuần tự như đang gõ chữ.\n\n"
            "10. <b>/spam @user</b>: Gửi một loạt sticker tới người dùng được chỉ định.\n\n"
            "Cảm ơn bạn đã sử dụng BOT by TAK."
        )
        
        await client.send_message(target_user, sd_message, parse_mode='html')
        return

    # Xử lý tin nhắn riêng tư
    if event.is_private:
        # Bỏ qua các tin nhắn do chính bot gửi đi
        if event.out:
            print(f"{Fore.CYAN}Tin nhắn của BOT bỏ qua")
            return

        # Lấy thông tin người gửi
        sender = await event.get_sender()

        if isinstance(sender, User):
            # Kiểm tra và ghép nối tên đầu tiên và tên họ nếu có
            first_name = sender.first_name if sender.first_name else ""
            last_name = sender.last_name if sender.last_name else ""
            sender_name = f"{first_name} {last_name}".strip()
            sender_username = sender.username if sender.username else "Unknown"
        else:
            # Xử lý khi sender là Channel hoặc Group
            sender_name = f"Channel or Group: {event.chat.title}"
            sender_username = event.chat.username if event.chat.username else "Unknown"

        # Kiểm tra nếu tin nhắn là reply
        if event.message.is_reply:
            reply_message = await event.message.get_reply_message()
            reply_text = reply_message.message

            # Tìm kiếm @user trong tin nhắn reply
            at_index = reply_text.rfind('@')
            if at_index != -1:
                user_mentioned = reply_text[at_index:].split()[0]  # Lấy username sau @
                # Sanitize the username
                user_mentioned = user_mentioned.strip().rstrip(")")

                if user_mentioned:
                    print(f"\033[32mDetected reply with mention of user \033[1;33m{user_mentioned}\033[0;32m.\033[0m")

                    try:
                        # Gửi lại nội dung của target_user đến @user hoặc file media nếu có
                        if event.message.media:
                            await client.send_file(
                                user_mentioned,
                                event.message.media,
                                caption=event.message.message if event.message.message else None
                            )
                        elif event.message.message:
                            await client.send_message(
                                user_mentioned,
                                event.message.message
                            )
                        else:
                            print(f"\033[31mError: The message cannot be empty unless a file is provided.\033[0m")
                            await client.send_message(target_user, f"Failed to send message to @{user_mentioned}: The message cannot be empty unless a file is provided.")
                    except ValueError as e:
                        print(f"\033[31mError sending message to {user_mentioned}: {e}\033[0m")
                        await client.send_message(target_user, f"Failed to send message to @{user_mentioned}: {e}")
                    return  # Kết thúc xử lý sau khi gửi tin nhắn
                else:
                    print(f"\033[31mNo valid user mentioned in the reply.\033[0m")

        # Tiếp tục xử lý phần còn lại của mã như trước...

        if event.message.media:
            print(f"\033[35m\033[1m{sender_name} \033[0;35m(@{sender.id}) vừa gửi một file.\033[0m")
        else:
            print(f"\033[35m\033[1m{sender_name} \033[0;35m(@{sender.id}) vừa gửi tin nhắn.\033[0m")

        # Kiểm tra danh sách loại trừ
        if sender_username in excluded_users:
            print(f"\033[31mUser \033[1;33m{sender_name}\033[0;31m (\033[1;33m{sender.id}\033[0;31m) is not allowed. Ignoring message.\033[0m")
            return  # Bỏ qua người dùng trong danh sách loại trừ, không thực hiện hành động nào

        # Xử lý tin nhắn từ target_user đến Kakalot5678
        if sender_username == target_user:
            print(f"{Fore.GREEN}Received message from target user.")

            # Kiểm tra xem tin nhắn có phải là một lệnh hay không
            if event.message.message.startswith('/'):
                print(f"{Fore.CYAN}Detected command, processing as a command.")
                await handle_command(event)
                return

            # Tách nội dung và ID nhóm hoặc user từ tin nhắn
            message_parts = event.message.message.rsplit(' ', 1)
            if len(message_parts) < 2 or not message_parts[1].startswith('@'):
                print(f"{Fore.RED}Invalid message format.")
                return  # Nếu tin nhắn không có @id nhóm hoặc @user, bỏ qua

            group_or_user_id_with_at = message_parts[1]
            group_or_user_id = group_or_user_id_with_at.lstrip('@')

            try:
                group_or_user_id = int(group_or_user_id)  # Chuyển đổi ID nhóm sang dạng số
                is_group = True
            except ValueError:
                is_group = False

            caption = message_parts[0]  # Phần chú thích (loại bỏ @user hoặc @id_nhóm)

            if is_group and str(group_or_user_id) in allowed_groups:
                print(f"\033[32mForwarding message to group \033[1;33m@{group_or_user_id}\033[0;32m.\033[0m")
                if event.message.media:
                    await client.send_file(group_or_user_id, event.message.media, caption=caption)
                else:
                    await client.send_message(group_or_user_id, caption)
            elif not is_group:
                print(f"\033[32mForwarding message to user \033[1;33m@{group_or_user_id}\033[0;32m.\033[0m")
                if group_or_user_id in excluded_users:
                    print(f"\033[31mUser \033[1;33m{group_or_user_id}\033[0;31m is not allowed. Ignoring message.\033[0m")
                    await client.send_message(sender_username, f"Xin lỗi <b>@{group_or_user_id}</b> này tôi sẽ không tương tác dưới bất kỳ hình thức nào. Cảm ơn!", parse_mode='html')
                else:
                    if event.message.media:
                        await client.send_file(group_or_user_id, event.message.media, caption=caption)
                    else:
                        await client.send_message(group_or_user_id, caption)
            else:
                print(f"\033[31mGroup \033[1;33m{group_or_user_id}\033[0;31m is not allowed. Ignoring message.\033[0m")
        else:
            print(f"\033[32mForwarding message to \033[1;36m{target_user}\033[0;32m.\033[0m")
            if event.message.media:
                await client.forward_messages(target_user, event.message)
            else:
                formatted_message = (
                    f"Người gửi: <b>{sender_name}</b> (@{sender_username})\n"
                    f"Nội dung: {event.message.message}"
                )
                await client.send_message(target_user, formatted_message, parse_mode='html')

    # Xử lý tin nhắn trong nhóm
    elif event.is_group:
        # Bỏ qua tin nhắn nếu do chính bot gửi đi
        if event.out:
            print(f"{Fore.CYAN}Message sent by the bot itself in group. Ignoring.")
            return

        chat = await event.get_chat()
        chat_id_str = str(chat.id)
        
        # Kiểm tra nếu nhóm được phép
        if chat_id_str in allowed_groups and chat.title == allowed_groups[chat_id_str]:
            sender = await event.get_sender()  # Lấy thông tin người gửi
            
            # Kiểm tra loại đối tượng người gửi
            if isinstance(sender, User):
                sender_name = sender.first_name
                sender_username = sender.username if sender.username else "N/A"
            else:
                sender_name = chat.title  # Sử dụng tên của nhóm hoặc kênh nếu người gửi là một Channel
                sender_username = "N/A"

            if event.message.media:
                print(f"\033[35m\033[1m{sender_name} \033[0;35m- {chat.title} - (\033[1;33m@{chat.id}\033[0;35m) vừa gửi một file.\033[0m")
                # Forward the media message
                await client.forward_messages(target_user, event.message)
                # Send a notification after forwarding the media
                await client.send_message(target_user, f"File đã được chuyển tiếp từ nhóm: {chat.title} ({chat.id})")
            else:
                print(f"\033[35m\033[1m{sender_name} \033[0;35m- {chat.title} - (\033[1;33m{chat.id}\033[0;35m) vừa gửi tin nhắn.\033[0m")
                # Rút gọn tên nhóm nếu dài hơn 50 ký tự
                truncated_chat_title = (chat.title[:47] + '...') if len(chat.title) > 50 else chat.title
                
                # Định dạng thông báo
                formatted_message = (
                    f"Nhóm: <b>{truncated_chat_title}</b> (@{chat.id})\n"
                    f"Tên: <b>{sender_name}</b> (@{sender_username})\n"
                    f"Nội dung: {event.message.message}"
                )
                # Gửi tin nhắn văn bản với định dạng mong muốn
                await client.send_message(target_user, formatted_message, parse_mode='html')
        else:
            print(f"\033[31mGroup \033[1;33m{chat.title} \033[31m({chat.id}) \033[31mis not allowed. Ignoring message.\033[0m")

# Hàm hỗ trợ lấy tên đầy đủ của người dùng
async def get_user_full_name(client, username):
    try:
        user_entity = await client.get_entity(username)
        return f"{user_entity.first_name} {user_entity.last_name or ''}".strip()
    except:
        return username

# Tối ưu hàng đợi
async def process_queue():
    global current_user, queue

    while queue:
        next_user_id, next_username, next_prompt, original_event = queue.pop(0)
        current_user = next_user_id

        # Lấy thông tin người dùng, bao gồm tên và họ
        user_entity = await client.get_entity(next_user_id)
        full_name = f"{user_entity.first_name} {user_entity.last_name or ''}".strip()

        # Gửi tin nhắn "Đang vẽ rồi, đợi một xí ✍️..." và giữ lại message_id
        creating_msg = await client.send_message(next_user_id, "Đang vẽ rồi, đợi một xí ✍️...")

        try:
            # Tạo nội dung đầy đủ với prompt
            full_prompt = (
                "<b>DALL-E 3</b> provides more <b>detailed</b> and <b>accurate</b> visual generations than DALL-E 2. "
                "This model is great for users looking for <b>high-definition</b> images with a variety of quality options. "
                f"Now generating: {next_prompt}"
            )

            # Gọi API DALL-E 3 để tạo tranh
            openai.api_key = api_chatgpt
            response = openai.Image.create(
                prompt=full_prompt,
                n=1,
                size="1024x1024",
                model="dall-e-3",
                quality="standard"
            )
            image_url = response['data'][0]['url']

            # Tải hình ảnh từ URL
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                image_data = image_response.content

                # Sử dụng io.BytesIO để lưu trữ ảnh trong bộ nhớ RAM
                image_io = io.BytesIO(image_data)
                image_io.name = f"temp_image_{next_user_id}.png"  # Đặt tên tệp tạm thời cho ảnh

                # Xóa tin nhắn "Đang vẽ rồi, đợi một xí ✍️..."
                await client.delete_messages(next_user_id, creating_msg.id)

                # Gửi hình ảnh đến người dùng dưới dạng reply vào tin nhắn gốc của lệnh /ve
                await client.send_file(
                    next_user_id,
                    image_io,
                    caption=f"Tranh của <b>{full_name}</b> vẽ xong rồi nè 💋",
                    parse_mode='html',
                    reply_to=original_event.message.id  # Trả lời tin nhắn gốc
                )

                print(f"Clear image in ram not save storage")
                # Giải phóng bộ nhớ
                image_io.close()

            else:
                await client.send_message(next_user_id, "Đã xảy ra một lỗi. Vui lòng kiểm tra lại nội dung muốn vẽ.")
        except Exception as e:
            print(f"Error generating image: {e}")
            await client.send_message(next_user_id, "Đã xảy ra một lỗi. Vui lòng kiểm tra lại nội dung muốn vẽ.")

        # Clear biến tạm sau khi hoàn thành
        current_user = None

        # Delay ngắn để tránh các vấn đề về tốc độ
        await asyncio.sleep(1)

# Check vẽ hàng đợi
async def handle_ve_command(sender_id, sender_username, prompt, event):
    global current_user, queue

    print(f"\033[1;32m{sender_username} (\033[1;33m@{sender_id}\033[0;32m) tham gia vẽ tranh\033[0m")
    print("\033[1;34mCheck hàng chờ...\033[0m")

    if current_user is None and not queue:
        # Không có người dùng hiện tại và không có hàng chờ
        current_user = sender_id
        print(f"\033[1;31mKhông có hàng chờ, gán id cho \033[1;32m{sender_username} (\033[1;33m@{sender_id}\033[0;32m)\033[0m")
        queue.append((sender_id, sender_username, prompt, event))  # Thêm event vào hàng đợi
        await process_queue()
    else:
        # Nếu có người đang xử lý hoặc có hàng chờ
        print(f"\033[1;34mHàng chờ hiện đang có \033[1;32m{current_user}\033[0m")
        queue.append((sender_id, sender_username, prompt, event))  # Thêm event vào hàng đợi
        print(f"\033[1;36mGửi thông báo cho \033[1;32m{sender_username} (\033[1;33m@{sender_id}\033[0;36m)\033[0m")
        waiting_msg = await client.send_message(sender_id, "Vui lòng chờ trong giây lát...")
        return

async def main():
    await client.start(phone=phone)

    @client.on(events.NewMessage)
    async def handler(event):
        global excluded_users, allowed_groups, ve_usage

        try:
            sender = await event.get_sender()
            if isinstance(sender, User):
                sender_username = sender.username
                sender_name = sender.first_name + ' ' + sender.last_name if sender.last_name else sender.first_name
                sender_id = sender.id
            elif isinstance(sender, Channel) or isinstance(sender, Chat):
                sender_username = sender.username
                sender_name = sender.title
                sender_id = sender.id
            else:
                sender_username = 'unknown'
                sender_name = 'unknown'
                sender_id = 'unknown'
        except Exception as e:
            print(f"\033[1;31mError retrieving sender: \033[0;33m{e}\033[0m")
            return   
        
    print("\033[1;32mBot is running...\033[0m")
    await client.run_until_disconnected()

try:
    with client:
        client.loop.run_until_complete(main())
except KeyboardInterrupt:
    print("\033[1;31mBot stopped manually.\033[0m")
