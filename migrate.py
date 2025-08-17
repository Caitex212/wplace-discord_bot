import json
import sqlite3

JSON_FILE = "artworks.json"
DB_FILE = "artworks.db"

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS artworks (
    message_id TEXT PRIMARY KEY,
    author_id TEXT,
    title TEXT,
    description TEXT,
    overlay_json TEXT,
    image_url TEXT,
    private INTEGER,
    status TEXT,
    followers TEXT
)
""")
conn.commit()

with open(JSON_FILE, "r") as f:
    data = json.load(f)

for message_id, art in data.items():
    conn.execute("""
    INSERT OR REPLACE INTO artworks
    (message_id, author_id, title, description, overlay_json, image_url, private, status, followers)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        art["message_id"], art["author_id"], art["title"], art["description"],
        art["overlay_json"], art["image_url"], int(art["private"]),
        art.get("status", "📜 Planned"),
        json.dumps(art.get("followers", []))
    ))

conn.commit()
print("Migration complete: JSON → SQLite")
