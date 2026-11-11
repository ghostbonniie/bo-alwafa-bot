# bo.alwafa Telegram bot: setup guide

What it does:
- **LIVE topic:** checks TikTok every 10 minutes. When @bo.alwafa goes LIVE it posts one message with the link (once per LIVE, no repeats).
- **Recipes topic:** posts one new xBloom recipe every day at 9:00 AM Kuwait time, from `recipes.json`. Each recipe posts once; when the list runs out it waits until you add more.
- Cost: free. It runs on GitHub Actions, so your PC does not need to be on.

Total setup time: about 20 minutes.

---

## Step 1. Make the bot (2 min)
1. In Telegram, open **@BotFather** and send `/newbot`.
2. Pick a name (example: `Bo Alwafa Bot`) and a username ending in `bot`.
3. BotFather gives you a **token** like `123456:ABC...`. Keep it private, do not paste it in any chat.
4. Still in BotFather: `/mybots` > your bot > Bot Settings > Group Privacy > **Turn off**. (Only needed for Step 3.)

## Step 2. Add the bot to your group
1. Open your group > Add members > search your bot username.
2. Make it **admin** with "Post messages" / "Manage topics" allowed.
3. Your two "channels" inside the group are **Topics**. Make sure you have both: for example `🔴 LIVE` and `☕ وصفات`.

## Step 3. Get the group id and topic ids
Easiest way, no code:
1. Open the group in **Telegram Web** (web.telegram.org/a).
2. Open the LIVE topic. The address bar looks like `#-1001234567890_5`.
   - `-1001234567890` is your **CHAT_ID**
   - `5` is the **LIVE_TOPIC_ID**
3. Open the recipes topic and note its number the same way (**RECIPE_TOPIC_ID**).

(Other way: send a message in each topic, then run `python bot.py ids` with the token set. It prints the ids.)

## Step 4. Put the files on GitHub
1. Make a new **public** repository on github.com (example name `bo-alwafa-bot`).
   - Public keeps it free with unlimited run time. Only the code and recipes are visible, never your token.
   - Private also works but the free 2,000 minutes a month will run out with 10 minute checks; change the LIVE check to every 30 minutes in that case.
2. Upload everything in this folder, including the hidden `.github/workflows` folder.
   (Tip: on the repo page use "Add file > Upload files" and drag the whole folder.)

## Step 5. Add the secrets
Repo > Settings > Secrets and variables > Actions > **New repository secret**. Add these 4:

| Name | Value |
|---|---|
| `TELEGRAM_TOKEN` | the token from BotFather |
| `CHAT_ID` | for example `-1001234567890` |
| `LIVE_TOPIC_ID` | for example `5` |
| `RECIPE_TOPIC_ID` | for example `7` |

## Step 6. Test it
Repo > **Actions** tab > enable workflows if asked.
- **Post recipe** > Run workflow: a recipe should appear in the recipes topic.
- **TikTok LIVE alert** > Run workflow (force ticked): a LIVE message should appear in the LIVE topic.

If both arrive, you are done. It now runs on its own.

---

## Daily use
- **Going LIVE:** do nothing, the alert posts within about 10 to 15 minutes.
- **Want the alert instantly?** Open the GitHub app on your phone > repo > Actions > TikTok LIVE alert > Run workflow. Takes 10 seconds and posts right away.
- **Add xBloom recipes:** edit `recipes.json` on GitHub and add a new `{"text": "..."}` entry with the share text from the xBloom app (use `\n` for a new line). Or just send the share text to Claude.
- **Change recipe time:** in `.github/workflows/recipes.yml` change `0 6 * * *`. The time is UTC, Kuwait is UTC+3, so 06:00 UTC = 9:00 AM. For 7:00 PM use `0 16 * * *`. For two a day: `0 6,16 * * *`.
- **Change the LIVE message text:** in `bot.py`, function `live_message`.

## Good to know
- TikTok has no official "is LIVE" API, so the bot reads the same public data the TikTok website uses. If TikTok changes it, the auto alert can stop working; the manual Run workflow button keeps working no matter what.
- GitHub's timer can run a few minutes late at busy times. That is normal.
- GitHub pauses timers on repos with no activity for 60 days. The bot saves a small file every day, which should keep it active. If GitHub ever emails you that a workflow was disabled, open the Actions tab and press Enable.

---

## Recipe picker (country > brand > bean > xBloom link)
Someone writes `/recipe` or `وصفة` in the group, and the bot replies with buttons. All picker recipes live in `library.json`:
```
{"country": "Yemen", "brand": "Hoy 8", "bean": "Haraz", "link": "https://share-h5.xbloom.com/...", "note": "optional tip"}
```
It runs on Vercel (free) so the buttons answer instantly.

One time setup:
1. Go to vercel.com and sign up with **Continue with GitHub**.
2. Add New > Project > Import `bo-alwafa-bot`.
3. Open **Environment Variables**, add `TELEGRAM_TOKEN` with your bot token, then press **Deploy**.
4. Copy your site address, for example `bo-alwafa-bot.vercel.app`.
5. In your browser open (put your token and address in):
   `https://api.telegram.org/botYOUR_TOKEN/setWebhook?url=https://YOUR_ADDRESS/api/webhook`
   It should say "Webhook was set".
6. Write `وصفة` in the group to test.

Every change to `library.json` on GitHub goes live by itself in about a minute.
