# Telegram Bot with Advanced Features

This repository contains a Telegram bot that offers various advanced features, including handling messages, automating tasks, and managing groups and users. The bot is built using the Telethon library and can be customized for different use cases.

## Features

- **/on**: Activates the bot with a default operating time.
- **/off**: Deactivates the bot temporarily, setting the operating time to the current time.
- **/ve {prompt}**: Generates an image based on the provided prompt using DALL-E 3 API.
- **/xoa**: Deletes all conversations between you and the bot from both sides.
- **/clear**: Deletes chat history between you and the bot from the bot's side only.
- **/adduser @user**: Adds a user to the exclusion list, preventing the bot from interacting with them.
- **/deluser @user**: Removes a user from the exclusion list.
- **/addgroup @id_group**: Adds a group to the allowed list, enabling the bot to interact within that group.
- **/delgroup @id_group**: Removes a group from the allowed list.
- **/listuser**: Displays a list of all users the bot interacts with.
- **/listgroup**: Displays a list of all groups the bot participates in.
- **/showuser**: Shows the exclusion list of users.
- **/showgroup**: Shows the list of allowed groups.
- **/hat {lyric} @user**: Sends a lyric to the specified user, simulating a singing experience.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.7+
- A Telegram account
- [Telethon](https://docs.telethon.dev/en/stable/) library installed
- An API key for DALL-E 3 (for image generation)

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/your-repository.git
    cd your-repository
    ```

2. **Create and Activate a Virtual Environment (Optional but Recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables:**

    Create a `.env` file in the root directory of the project and add the following environment variables:

    ```env
    API_ID=your_api_id
    API_HASH=your_api_hash
    PHONE_NUMBER=your_phone_number
    TARGET_USER=target_user_username
    API_CHATGPT=your_chatgpt_api_key
    ```

    - Replace `your_api_id` with your Telegram API ID.
    - Replace `your_api_hash` with your Telegram API Hash.
    - Replace `your_phone_number` with your Telegram phone number.
    - Replace `target_user_username` with the username of the target user.
    - Replace `your_chatgpt_api_key` with your DALL-E 3 API key.

5. **Run the Bot:**

    ```bash
    python U-rep-to-rep.py
    ```

## Usage

Once the bot is running, you can interact with it through your Telegram account. Here are some examples:

- **Activate the Bot:**

    ```bash
    /on
    ```

- **Deactivate the Bot:**

    ```bash
    /off
    ```

- **Generate an Image:**

    ```bash
    /ve A beautiful sunset over the mountains
    ```

- **Delete Conversations:**

    ```bash
    /xoa
    ```

- **Add a User to the Exclusion List:**

    ```bash
    /adduser @username
    ```

- **Send a Lyric:**

    ```bash
    /hat Hello, how are you? @username
    ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
