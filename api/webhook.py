"""
Recipe picker for the bo.alwafa Telegram group (runs on Vercel, free).

Someone writes /recipe (or the word وصفة / recipe) in the group.
The bot answers with buttons:  country  ->  bag brand  ->  bean  ->  xBloom link.
All recipes live in library.json at the top of the repo.

Env vars on Vercel: TELEGRAM_TOKEN, WEBHOOK_SECRET
"""
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SECRET = os.environ.get("WEBHOOK_SECRET", "")
LIBRARY_FILE = Path(__file__).resolve().parent.parent / "library.json"
TRIGGERS = ("/recipe", "/start", "وصفة", "وصفه", "recipe")
PER_ROW = 2


def load_library():
    return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))


def tg(method, payload):
    if not TOKEN:  # offline test mode
        print(method, json.dumps(payload, ensure_ascii=False))
        return {}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def unique(items):
    out = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def keyboard(labels, prefix, back=None):
    """labels -> rows of buttons; callback data = prefix + index."""
    rows, row = [], []
    for i, label in enumerate(labels):
        row.append({"text": label, "callback_data": f"{prefix}{i}"})
        if len(row) == PER_ROW:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if back:
        rows.append([{"text": "⬅️ رجوع", "callback_data": back}])
    return {"inline_keyboard": rows}


def countries(lib):
    return sorted(unique(r["country"] for r in lib))


def brands(lib, c):
    return sorted(unique(r["brand"] for r in lib if r["country"] == c))


def beans(lib, c, b):
    return [r for r in lib if r["country"] == c and r["brand"] == b]


# ---- screens: (text, keyboard) ----
def screen_countries(lib):
    if not lib:
        return "ما في وصفات للحين، قريب إن شاء الله ☕", None
    return "☕ اختار بلد البن:", keyboard(countries(lib), "c:")


def screen_brands(lib, ci):
    c = countries(lib)[ci]
    return (f"☕ {c}\nاختار المحمصة / البراند:",
            keyboard(brands(lib, c), f"b:{ci}:", back="home"))


def screen_beans(lib, ci, bi):
    c = countries(lib)[ci]
    b = brands(lib, c)[bi]
    items = beans(lib, c, b)
    if len(items) == 1:
        return screen_recipe(lib, ci, bi, 0)
    return (f"☕ {c} / {b}\nاختار البن:",
            keyboard([r["bean"] for r in items], f"r:{ci}:{bi}:",
                     back=f"c:{ci}"))


def screen_recipe(lib, ci, bi, ri):
    c = countries(lib)[ci]
    b = brands(lib, c)[bi]
    r = beans(lib, c, b)[ri]
    text = (f"Recipe shared by Bo Alwafa ☕️\n"
            f"{r['bean']}\n{c} / {b}\n\n{r['link']}")
    if r.get("note"):
        text += f"\n\n💡 {r['note']}"
    return text, {"inline_keyboard": [[{"text": "⬅️ رجوع", "callback_data": f"b:{ci}:{bi}"},
                                       {"text": "🏠 البداية", "callback_data": "home"}]]}


def route(lib, data):
    p = data.split(":")
    try:
        if p[0] == "c":
            return screen_brands(lib, int(p[1]))
        if p[0] == "b":
            return screen_beans(lib, int(p[1]), int(p[2]))
        if p[0] == "r":
            return screen_recipe(lib, int(p[1]), int(p[2]), int(p[3]))
    except (IndexError, ValueError):
        pass  # menu is out of date (library changed): start over
    return screen_countries(lib)


def handle(update):
    lib = load_library()
    if "callback_query" in update:
        q = update["callback_query"]
        msg = q["message"]
        text, kb = route(lib, q.get("data", ""))
        tg("answerCallbackQuery", {"callback_query_id": q["id"]})
        payload = {"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                   "text": text}
        if kb:
            payload["reply_markup"] = kb
        tg("editMessageText", payload)
        return
    msg = update.get("message") or {}
    words = (msg.get("text") or "").strip().lower()
    if not any(words.startswith(t) for t in TRIGGERS):
        return
    text, kb = screen_countries(lib)
    payload = {"chat_id": msg["chat"]["id"], "text": text,
               "reply_to_message_id": msg["message_id"]}
    if msg.get("message_thread_id"):
        payload["message_thread_id"] = msg["message_thread_id"]
    if kb:
        payload["reply_markup"] = kb
    tg("sendMessage", payload)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if SECRET and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
            self.send_response(403)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            handle(json.loads(self.rfile.read(length) or b"{}"))
        except Exception as e:  # never make Telegram retry forever
            print("error:", e)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("bo.alwafa recipe bot is running".encode())
