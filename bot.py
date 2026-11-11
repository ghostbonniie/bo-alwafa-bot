"""
bo.alwafa Telegram bot
Posts into two topics of one Telegram group:
  1) LIVE topic: a message when @bo.alwafa goes LIVE on TikTok
  2) Recipes topic: one xBloom recipe on a schedule (from recipes.json)

Usage:
  python bot.py recipe        -> post the next new xBloom recipe
  python bot.py live          -> check TikTok, post once if LIVE
  python bot.py live --force  -> post the LIVE message now (manual button)
  python bot.py ids           -> print group id and topic ids (setup helper)

Add --dry to any command to print instead of sending.

Settings come from environment variables (GitHub Secrets):
  TELEGRAM_TOKEN, CHAT_ID, LIVE_TOPIC_ID, RECIPE_TOPIC_ID, TIKTOK_USER
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
STATE_FILE = HERE / "state.json"
RECIPES_FILE = HERE / "recipes.json"

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
LIVE_TOPIC_ID = os.environ.get("LIVE_TOPIC_ID", "")
RECIPE_TOPIC_ID = os.environ.get("RECIPE_TOPIC_ID", "")
TIKTOK_USER = os.environ.get("TIKTOK_USER", "bo.alwafa").lstrip("@")

DRY = "--dry" in sys.argv
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
KUWAIT = dt.timezone(dt.timedelta(hours=3))


# ---------- helpers ----------
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"recipe_index": 0, "last_live_room": "", "is_live": False}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def tg(method, **params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=30) as r:
        res = json.loads(r.read().decode())
    if not res.get("ok"):
        raise RuntimeError(res)
    return res["result"]


def send(topic_id, text):
    if DRY:
        print(f"--- would send to topic {topic_id} ---\n{text}\n")
        return
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
              "disable_web_page_preview": "false"}
    if topic_id:
        params["message_thread_id"] = topic_id
    tg("sendMessage", **params)


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


# ---------- recipes ----------
# recipes.json is a list of xBloom recipes. Each one has a "text" field:
# paste the share text from the xBloom app exactly as you want it posted.
# Each recipe is posted once, in order. When the list runs out the bot
# waits quietly until you add more (no repeats).
def post_recipe():
    recipes = json.loads(RECIPES_FILE.read_text(encoding="utf-8"))
    state = load_state()
    i = state.get("recipe_index", 0)
    if i >= len(recipes):
        print(f"no new recipes ({len(recipes)} already posted), add more to recipes.json")
        return
    text = recipes[i]["text"]
    if DRY:
        print(f"--- would send to topic {RECIPE_TOPIC_ID} ---\n{text}\n")
    else:
        params = {"chat_id": CHAT_ID, "text": text,
                  "disable_web_page_preview": "false"}
        if RECIPE_TOPIC_ID:
            params["message_thread_id"] = RECIPE_TOPIC_ID
        tg("sendMessage", **params)
        state["recipe_index"] = i + 1
        save_state(state)
    print(f"posted recipe {i + 1}/{len(recipes)}")


# ---------- TikTok LIVE ----------
def check_tiktok_live():
    """Return (is_live, room_id). TikTok has no official LIVE status API,
    so this reads the same public endpoint the website uses. It can stop
    working if TikTok changes it; the --force button still works then."""
    url = ("https://www.tiktok.com/api-live/user/room/?aid=1988"
           f"&sourceType=54&uniqueId={urllib.parse.quote(TIKTOK_USER)}")
    try:
        data = json.loads(http_get(url))
        d = data.get("data") or {}
        user = d.get("user") or {}
        room = d.get("liveRoom") or {}
        room_id = str(user.get("roomId") or room.get("roomId") or "")
        # status 2 = live, 4 = ended
        status = user.get("status") or room.get("status")
        print(f"tiktok api: user.status={user.get('status')} "
              f"liveRoom.status={room.get('status')} roomId={room_id} "
              f"statusCode={data.get('statusCode')}")
        if status is not None:
            return status == 2 and bool(room_id), room_id
    except Exception as e:
        print("api check failed:", e)

    # fallback: read the live page
    try:
        html = http_get(f"https://www.tiktok.com/@{TIKTOK_USER}/live")
        m = re.search(r'"roomId":"(\d+)"', html)
        s = re.search(r'"status":(\d)', html)
        if m and s:
            return s.group(1) == "2", m.group(1)
    except Exception as e:
        print("page check failed:", e)
    return False, ""


def live_message():
    link = f"https://www.tiktok.com/@{TIKTOK_USER}/live"
    return ("🔴 <b>بث مباشر الحين!</b>\n\n"
            "بو الوفا لايف على تيك توك ☕\n"
            "تعالوا نسولف قهوة ونحل مشاكلكم مع أجهزتكم\n\n"
            f"👈 {link}")


def post_live(force=False):
    state = load_state()
    if force:
        send(LIVE_TOPIC_ID, live_message())
        print("posted LIVE (manual)")
        return
    is_live, room_id = check_tiktok_live()
    print(f"live={is_live} room={room_id}")
    if is_live and room_id != state.get("last_live_room"):
        send(LIVE_TOPIC_ID, live_message())
        state["last_live_room"] = room_id
    state["is_live"] = is_live
    if not DRY:
        save_state(state)


# ---------- setup helper ----------
def print_ids():
    """Write any message inside each topic first, then run this."""
    for u in tg("getUpdates"):
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        print(f"group: {chat.get('title')}  CHAT_ID={chat.get('id')}  "
              f"topic id={msg.get('message_thread_id', '(General)')}  "
              f"text={msg.get('text', '')[:30]!r}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "recipe":
        post_recipe()
    elif cmd == "live":
        post_live(force="--force" in sys.argv)
    elif cmd == "ids":
        print_ids()
    else:
        print(__doc__)
