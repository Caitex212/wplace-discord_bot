# 🎨 WPlace Artwork Discord Bot

This bot allows users to post and manage collaborative artwork projects for **WPlace** in a Discord server.  
It supports artwork posts, status updates, editing details, and persistence across restarts.

> ⚠️ **Note:** This project was generated with the help of AI (ChatGPT).

---

## ✨ Features
- **Artwork posting** with:
  - Image upload
  - Description
  - Overlay JSON (for WPlace Overlay Pro import)
  - Privacy toggle (hide/show author name)
- **Persistence**: Artworks are saved to a local JSON file so they survive restarts.
- **Status management**: Authors can mark their artwork as:
  - 📜 Planned
  - 🖌️ In progress
  - ✅ Done
- **Editing**: Authors can update:
  - Image
  - Description
  - Overlay JSON
  - Privacy toggle
- **Deletion**: Authors can delete their own artwork posts.
- **Likes**: Other users can like an artwork with 👍.

---

## 🚀 Commands

All commands are slash commands (`/`):

### `/artwork create`
Create a new artwork post.
- `description` – Short text describing your artwork.
- `overlay_json` – JSON string for WPlace Overlay Pro.
- `image` – Upload your artwork image.
- `private` – *(optional)* Hide your username from the post.

### `/artwork set_status`
Update the status of your artwork (only the author can do this).
- `message_id` – The message ID of the artwork post.
- `status` – Choose between ✅ Done, 🖌️ In progress, 📜 Planned.

### `/artwork edit`
Edit the details of your artwork post.
- `message_id` – The message ID of the artwork post.
- `description` – *(optional)* Update description.
- `overlay_json` – *(optional)* Update overlay JSON.
- `image` – *(optional)* Upload a new image.
- `private` – *(optional)* Change privacy setting.

### `/artwork delete`
Delete your artwork post.
- `message_id` – The message ID of the artwork post.

---

## 📂 Setup & Hosting

### Requirements
- Python 3.9+
- `py-cord` library

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/wplace-discord-bot.git
   cd wplace-discord-bot
    ```

2. Install dependencies:

   ```bash
   pip install py-cord
   ```

3. Create a `artworks.json` file (empty at start):

   ```json
   {}
   ```

4. Create `config.py` and set:

   * `TOKEN` – your Discord bot token
   * `GUILD_ID` – your Discord server ID
   * `ARTWORKS_CHANNEL_ID` – channel ID for the artwork posts

### Running

```bash
python main.py
```

The bot will come online and register its slash commands.
If commands don’t show up immediately, wait a few minutes or re-invite the bot with the correct **application.commands** permission.

---

## 📝 License

This project is released under the **MIT License**.
