from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel, PeerUser, PeerChat, PeerChannel, InputStickerSetShortName
from telethon.tl.functions.messages import GetStickerSetRequest
from dotenv import load_dotenv
import os
import json
import asyncio
import time
from datetime import datetime, time as dt_time, timezone, timedelta

# Load biến môi trường từ tệp .env
load_dotenv()

# Thông tin đăng nhập cho tài khoản Telegram trên máy tính (Kakalot5678)
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE_NUMBER')
target_user = os.getenv('TARGET_USER')

# Kiểm tra xem các biến môi trường có được nạp đúng không
print(f"API ID: {api_id}")
print(f"API Hash: {api_hash}")
print(f"Phone Number: {phone}")
print(f"Target User: {target_user}")

# Tạo client cho tài khoản trên máy tính
client = TelegramClient('kakalot5678', api_id, api_hash)

# Đường dẫn tới tệp JSON
settings_file = 'settings.json'

# Hàm tải danh sách từ tệp JSON
def load_settings():
    try:
        with open(settings_file, 'r') as f:
            data = json.load(f)
            return data['excluded_users'], data['allowed_groups']
    except FileNotFoundError:
        return [], {}

# Hàm lưu danh sách vào tệp JSON
def save_settings(excluded_users, allowed_groups):
    with open(settings_file, 'w') as f:
        json.dump({'excluded_users': excluded_users, 'allowed_groups': allowed_groups}, f, indent=4)

# Tải danh sách loại trừ và nhóm được phép
excluded_users, allowed_groups = load_settings()

# Hàm kiểm tra nếu thời gian hiện tại trong khoảng thời gian cho phép
def is_within_time_range():
    now = datetime.now(timezone(timedelta(hours=7))).time()  # Giờ hiện tại theo múi giờ +7
    start_time = dt_time(22, 30)
    end_time = dt_time(12, 0)

    if start_time <= now or now <= end_time:
        return True
    return False

# Hàm gửi sticker
async def send_sticker(client, chat_id, sticker):
    try:
        await client.send_file(chat_id, sticker)
    except Exception as e:
        print(f"Failed to send sticker {sticker}: {e}")

# Hàm gửi các sticker theo thứ tự từ dưới lên trên
async def send_stickers(client, chat_id, stickers, delay):
    start_time = time.time()
    for sticker in reversed(stickers):
        await send_sticker(client, chat_id, sticker)
        await asyncio.sleep(delay)
    end_time = time.time()
    print(f"Sent {len(stickers)} stickers in {end_time - start_time} seconds")

# Hàm lấy thực thể từ username
async def get_entity_from_username(client, username):
    try:
        entity = await client.get_entity(username)
        return entity
    except Exception as e:
        print(f"Error: {e}")
        return None

async def clear_chat_with_user(user_id):
    async for message in client.iter_messages(user_id):
        await client.delete_messages(user_id, message.id, revoke=False)

async def main():
    await client.start(phone=phone)

    @client.on(events.NewMessage)
    async def handler(event):
        global excluded_users, allowed_groups

        try:
            sender = await event.get_sender()
            if isinstance(sender, User):
                sender_username = sender.username
                sender_name = sender.first_name + ' ' + sender.last_name if sender.last_name else sender.first_name
                sender_id = sender.id
            elif isinstance(sender, Channel):
                sender_username = sender.username
                sender_name = sender.title
                sender_id = sender.id
            else:
                sender_username = 'unknown'
                sender_name = 'unknown'
                sender_id = 'unknown'
        except Exception as e:
            print(f"Error retrieving sender: {e}")
            return

        # Bỏ qua các tin nhắn do chính bot gửi đi
        if event.out:
            print("Message sent by the bot itself. Ignoring.")
            return

        # Kiểm tra nếu trong khoảng thời gian cho phép và không phải là lệnh từ target_user
        if not is_within_time_range() and sender_username != target_user:
            print("Outside of active hours. Ignoring message.")
            return

        # Xử lý tin nhắn riêng tư
        if event.is_private:
            if event.message.media:
                print(f"{sender_name} ({sender_id}) vừa gửi một file.")
            else:
                print(f"{sender_name} ({sender_id}) vừa gửi tin nhắn.")
            
            # Kiểm tra danh sách loại trừ
            if sender_username in excluded_users:
                print(f"User {sender_name} ({sender_id}) is not allowed. Ignoring message.")
                return  # Bỏ qua người dùng trong danh sách loại trừ, không thực hiện hành động nào

            # Xử lý lệnh /xoa @user
            if event.message.message.startswith('/xoa '):
                print("Received /xoa command.")
                # Lấy tên người dùng cần xóa tin nhắn
                target_user_to_delete = event.message.message.split(' ')[1]
                if target_user_to_delete.startswith('@'):
                    # Xóa toàn bộ hội thoại với target_user từ cả hai phía
                    async for message in client.iter_messages(target_user_to_delete):
                        await client.delete_messages(target_user_to_delete, message.id, revoke=True)
                return

            # Xử lý lệnh /xoa
            if event.message.message == '/xoa':
                print("Received /xoa command to delete all messages.")
                # Xóa toàn bộ hội thoại với sender từ cả hai phía
                async for message in client.iter_messages(sender_username):
                    await client.delete_messages(sender_username, message.id, revoke=True)
                return

            # Xử lý lệnh /clear @user
            if event.message.message.startswith('/clear '):
                print("Received /clear command.")
                target_user_to_clear = event.message.message.split(' ')[1]
                if target_user_to_clear.startswith('@'):
                    target_user_to_clear = target_user_to_clear.lstrip('@')
                    async for message in client.iter_messages(target_user_to_clear):
                        await client.delete_messages(target_user_to_clear, message.id, revoke=False)
                return

            # Xử lý lệnh /clear
            if event.message.message == '/clear':
                print("Received /clear command to delete all messages.")
                async for message in client.iter_messages(sender_username):
                    await client.delete_messages(sender_username, message.id, revoke=False)
                return

            # Xử lý lệnh /adduser @user
            if event.message.message.startswith('/adduser '):
                print("Received /adduser command.")
                user_to_exclude = event.message.message.split(' ')[1].lstrip('@')
                if user_to_exclude not in excluded_users:
                    excluded_users.append(user_to_exclude)
                    save_settings(excluded_users, allowed_groups)
                    print(f"Added {user_to_exclude} to excluded users.")
                    await client.send_message(target_user, f"Đã thêm tên (@{user_to_exclude}) thành công.")
                return

            # Xử lý lệnh /deluser @user
            if event.message.message.startswith('/deluser '):
                print("Received /deluser command.")
                user_to_include = event.message.message.split(' ')[1].lstrip('@')
                if user_to_include in excluded_users:
                    excluded_users.remove(user_to_include)
                    save_settings(excluded_users, allowed_groups)
                    print(f"Removed {user_to_include} from excluded users.")
                    await client.send_message(target_user, f"Đã xóa tên (@{user_to_include}) thành công.")
                return

            # Xử lý lệnh /addgroup <group_id> <group_name>
            if event.message.message.startswith('/addgroup '):
                print("Received /addgroup command.")
                parts = event.message.message.split(' ', 3)
                if len(parts) >= 3:
                    group_id = int(parts[1])
                    group_name = ' '.join(parts[2:])
                    allowed_groups[str(group_id)] = group_name
                    save_settings(excluded_users, allowed_groups)
                    print(f"Added group {group_name} ({group_id}) to allowed groups.")
                    await client.send_message(target_user, f"Đã thêm nhóm ({group_name} - {group_id}) thành công.")
                return

            # Xử lý lệnh /delgroup <group_id>
            if event.message.message.startswith('/delgroup '):
                print("Received /delgroup command.")
                group_id = int(event.message.message.split(' ')[1])
                group_id_str = str(group_id)
                if group_id_str in allowed_groups:
                    group_name = allowed_groups[group_id_str]
                    del allowed_groups[group_id_str]
                    save_settings(excluded_users, allowed_groups)
                    print(f"Removed group {group_name} ({group_id}) from allowed groups.")
                    await client.send_message(target_user, f"Đã xóa nhóm ({group_name} - {group_id}) thành công.")
                return

            # Xử lý lệnh /listuser
            if event.message.message == '/listuser':
                print("Received /listuser command.")
                user_list = []
                async for dialog in client.iter_dialogs():
                    entity = dialog.entity
                    if isinstance(entity, User) and not entity.bot:
                        username = entity.username
                        if username:
                            user_list.append(f"Tên: {entity.first_name} {entity.last_name or ''} (@{username})")
                if user_list:
                    message = "\n".join(user_list)
                else:
                    message = "Không có người dùng nào trong danh sách."
                await client.send_message(target_user, message)
                await clear_chat_with_user(sender_id)
                return

            # Xử lý lệnh /showuser
            if event.message.message == '/showuser':
                print("Received /showuser command.")
                user_list = [f"{idx + 1}. Tên (@{user})" for idx, user in enumerate(excluded_users)]
                if user_list:
                    message = "\n".join(user_list)
                else:
                    message = "Danh sách người dùng không có."
                await client.send_message(target_user, message)
                await clear_chat_with_user(sender_id)
                return

            # Xử lý lệnh /showgroup
            if event.message.message == '/showgroup':
                print("Received /showgroup command.")
                group_list = [f"{idx + 1}. Tên nhóm: {group_name} (@{group_id})" for idx, (group_id, group_name) in enumerate(allowed_groups.items())]
                if group_list:
                    message = "\n".join(group_list)
                else:
                    message = "Danh sách nhóm không có."
                await client.send_message(target_user, message)
                await clear_chat_with_user(sender_id)
                return

            # Xử lý lệnh /listgroup
            if event.message.message == '/listgroup':
                print("Received /listgroup command.")
                group_list = []
                async for dialog in client.iter_dialogs():
                    entity = dialog.entity
                    if isinstance(entity, (Chat, Channel)):
                        group_list.append(f"Tên nhóm: {entity.title} (@{entity.id})")
                if group_list:
                    message = "\n".join(group_list)
                else:
                    message = "Không có nhóm nào trong danh sách."
                await client.send_message(target_user, message)
                await clear_chat_with_user(sender_id)
                return

            # Show chức năng /sd
            if event.message.message == '/sd':
                print("Received /sd command.")
                sd_message = (
                    "Đây là chức năng hiện tại của BOT\n"
                    "1. <b>/xoa</b> và <b>/xoa @user</b>: Xóa\n"
                    "2. <b>/clear</b> và <b>/clear @user</b>: Xóa 1 phía\n"
                    "3. <b>/adduser</b> và <b>/deluser</b>: Thêm User loại trừ và Xóa user loại trừ\n"
                    "4. <b>/addgroup</b> và <b>/delgroup</b>: Thêm group hóng và xóa Group hóng\n"
                    "5. <b>/listuser</b> và <b>/listgroup</b>: Show list ID User và Show list ID Group\n"
                    "6. <b>/showuser</b> và <b>/showgroup</b>: Show list loại trừ user và show list cho phép group\n"
                    "Cảm ơn bạn đã sử dụng BOT by TAK"
                )
                await client.send_message(target_user, sd_message, parse_mode='html')
                return

            # Xử lý lệnh /spam @user
            if event.message.message.startswith('/spam '):
                print("Received /spam command.")
                user_to_spam = event.message.message.split(' ')[1].lstrip('@')
                entity = await get_entity_from_username(client, user_to_spam)
                if entity:
                    sticker_set_name = 'ingusan'
                    sticker_set_response = await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name=sticker_set_name), hash=0))

                    if hasattr(sticker_set_response, 'documents'):
                        stickers = sticker_set_response.documents
                        await send_stickers(client, entity.id, stickers, delay=0.01)
                        print(f"Spammed {user_to_spam} with stickers.")
                    else:
                        print("No documents found in the sticker set.")
                return

            # Xử lý tin nhắn từ target_user đến Kakalot5678
            if sender_username == target_user:
                print("Received message from target user.")
                # Tách nội dung và ID nhóm từ tin nhắn
                message_parts = event.message.message.rsplit(' ', 1)
                if len(message_parts) < 2 or not message_parts[1].startswith('@'):
                    print("Invalid message format.")
                    return  # Nếu tin nhắn không có @id nhóm hoặc @user, bỏ qua

                group_or_user_id_with_at = message_parts[1]
                group_or_user_id = group_or_user_id_with_at.lstrip('@')
                
                try:
                    group_or_user_id = int(group_or_user_id)  # Chuyển đổi ID nhóm sang dạng số
                    is_group = True
                except ValueError:
                    is_group = False

                if is_group and str(group_or_user_id) in allowed_groups:
                    print(f"Forwarding message to group {group_or_user_id}.")
                    # Gửi nội dung vào nhóm với ID chỉ định
                    if event.message.media:
                        await client.send_file(group_or_user_id, event.message.media, caption=message_parts[0])
                    else:
                        await client.send_message(group_or_user_id, message_parts[0])
                elif not is_group:
                    print(f"Forwarding message to user {group_or_user_id}.")
                    if group_or_user_id in excluded_users:
                        print(f"User {group_or_user_id} is not allowed. Ignoring message.")
                        await client.send_message(sender_username, f"Xin lỗi @{group_or_user_id} này tôi sẽ không tương tác dưới bất kỳ hình thức nào. Cảm ơn!")
                    else:
                        if event.message.media:
                            await client.send_file(group_or_user_id, event.message.media)
                        else:
                            await client.send_message(group_or_user_id, message_parts[0])
                else:
                    print(f"Group {group_or_user_id} is not allowed. Ignoring message.")
            else:
                print(f"Forwarding message to {target_user}.")
                # Chuyển tiếp tin nhắn văn bản đến target_user
                if event.message.media:
                    # Nếu là tin nhắn chứa tệp tin, forward đến target_user
                    await client.forward_messages(target_user, event.message)
                else:
                    # Nếu là tin nhắn văn bản, bóc tách và gửi nội dung sang target_user
                    formatted_message = (
                        f"Người gửi: {sender_name} (@{sender_username})\n"
                        f"Nội dung: {event.message.message}"
                    )
                    await client.send_message(target_user, formatted_message)

        # Xử lý tin nhắn trong nhóm
        elif event.is_group:
            chat = await event.get_chat()
            chat_id_str = str(chat.id)
            if chat_id_str in allowed_groups and chat.title == allowed_groups[chat_id_str]:
                if event.message.media:
                    print(f"{sender_name} - {chat.title} - ({chat.id}) vừa gửi một file.")
                else:
                    print(f"{sender_name} - {chat.title} - ({chat.id}) vừa gửi tin nhắn.")
                if event.out:
                    print("Message sent by the bot itself in group. Ignoring.")
                    return
                if event.message.media:
                    # Nếu là tin nhắn chứa tệp tin, forward đến target_user
                    await client.forward_messages(target_user, event.message)
                else:
                    # Nếu là tin nhắn văn bản, bóc tách và gửi nội dung sang target_user
                    formatted_message = (
                        f"Tên: {sender_name} (@{sender_username}) - Tên nhóm: {chat.title} (@{chat.id})\n"
                        f"Nội dung: {event.message.message}"
                    )
                    await client.send_message(target_user, formatted_message)
            else:
                print(f"Group {chat.title} ({chat.id}) is not allowed. Ignoring message.")

    print("Bot is running...")
    await client.run_until_disconnected()

try:
    with client:
        client.loop.run_until_complete(main())
except KeyboardInterrupt:
    print("Bot stopped manually.")
