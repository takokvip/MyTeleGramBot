
# Telegram Bot with Advanced Features

This repository contains a Telegram bot that offers various advanced features, including handling messages, automating tasks, and managing groups and users. The bot is built using the Telethon library and can be customized for different use cases.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/yourrepository.git
```

2. Navigate to the project directory:

```bash
cd yourrepository
```

3. Create a virtual environment:

```bash
python3 -m venv .venv
```

4. Activate the virtual environment:

- On macOS/Linux:
  
  ```bash
  source .venv/bin/activate
  ```

- On Windows:

  ```bash
  .venv\Scripts\activate
  ```

5. Install the required dependencies:

```bash
pip install -r requirements.txt
```

6. Configure the `.env` file:

Create a `.env` file in the root directory of the project and add your Telegram API credentials and other necessary configurations:

```bash
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=your_phone_number
TARGET_USER=your_target_user
API_CHATGPT=your_chatgpt_api_key
```

Replace `your_api_id`, `your_api_hash`, `your_phone_number`, `your_target_user`, and `your_chatgpt_api_key` with your actual values.

## Usage

1. Start the bot:

```bash
python main.py
```

2. Use the following commands to interact with the bot:

### Bot Commands

- `/on`: Activate the bot and set its active hours to 12:00 to 22:30.
- `/off`: Deactivate the bot and set its active hours to the current time.
- `/ve {prompt}`: Generate an image based on the given prompt (e.g., `/ve A beautiful sunset`).
- `/xoa`: Delete all chat history between you and the bot from both sides.
- `/xoa @user`: Delete all chat history between the bot and a specified user from both sides.
- `/clear`: Clear all chat history between you and the bot from the bot's side only.
- `/clear @user`: Clear all chat history between the bot and a specified user from the bot's side only.
- `/adduser @user`: Add a user to the exclusion list; the bot will not interact with this user.
- `/deluser @user`: Remove a user from the exclusion list.
- `/addgroup @id_group group_name`: Add a group to the allowed list; the bot will listen and interact in this group.
- `/delgroup @id_group`: Remove a group from the allowed list.
- `/listuser`: Show the list of all users the bot has interacted with.
- `/listgroup`: Show the list of all groups the bot has joined.
- `/showuser`: Show the list of users in the exclusion list.
- `/showgroup`: Show the list of groups in the allowed list.
- `/spam @user`: Send a series of stickers to a specified user.

### Sending Messages to Users and Groups

1. **Sending a Message to a User:**
   - To send a message to a specific user, use the following format:
     ```
     [Your message content] @username
     ```
   - Replace `@username` with the actual username of the recipient.

2. **Sending a Message to a Group:**
   - To send a message to a group, use the following format:
     ```
     [Your message content] @group_id
     ```
   - Replace `@group_id` with the actual ID of the group.

3. **Tagging Users in a Group:**
   - If you want to tag a user in a group, use the following format:
     ```
     [Your message content] #username @group_id
     ```
   - Replace `#username` with the username of the person you want to tag and `@group_id` with the group ID.

## Notes

- The bot operates within a specific time range, which can be adjusted using the `/on` and `/off` commands.
- All operations are logged to the console for monitoring and debugging purposes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

If you'd like to contribute, please fork the repository and use a feature branch. Pull requests are warmly welcome.
