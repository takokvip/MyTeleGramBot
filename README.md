# Telegram Bot ALLIN ONE - CODE BY TAK OKVIP

## How to Install

**Python Required**

1. Install the required libraries:

    ```sh
    pip install -r requirements.txt
    ```

2. Configure the `.env` file:

    Create a `.env` file in the same directory as your script and add the following content:

    ```env
    API_ID=your_api_id
    API_HASH=your_api_hash
    PHONE_NUMBER=your_phone_number
    TARGET_USER=your_target_user
    ```

    Replace `your_api_id`, `your_api_hash`, `your_phone_number`, and `your_target_user` with your actual Telegram API credentials and target user.

3. Run the script:

    ```sh
    python U-rep-to-rep.py
    ```

## Bot Functions

1. **/xoa & /xoa @user**: Delete all messages from both Admin & Bot side.
2. **/clear & /clear @user**: Delete messages only on the BOT side.
3. **/adduser & /deluser**: Add or remove users to avoid abuse.
4. **/addgroup & /delgroup**: Add or remove groups with permission to listen to messages.
5. **/listuser & /listgroup**: Show the list of added users and groups.
6. **/showuser & /showgroup**: Show the list of excluded users and allowed groups.

   ```sh
    /spam @user (learn don't abuse ^^!)
    ```

## How to Reply to a Message

When there is a message to the BOT, the BOT will forward it to the admin. If the admin wants to reply, just follow these instructions:

- For personal messages: Send a message in the format `Content @User`.
- For group messages: Send a message in the format `Content @group_id`.

All messages should be sent to the BOT, and the BOT will act as an intermediary to send the message, ensuring that the admin's name is not exposed anywhere.

---

## Example .env file

```env
API_ID=25169999
API_HASH=a95b580f11a6b1975c9d64f15502b999
PHONE_NUMBER=+84987654321
TARGET_USER=MyAdminControl
