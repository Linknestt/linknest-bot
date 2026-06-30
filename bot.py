"""
LinkNest Telegram Bot
----------------------
Listens for keyword messages and replies with the matching link from Supabase.

Environment variables required:
  TELEGRAM_BOT_TOKEN   - token from @BotFather
  SUPABASE_URL         - your Supabase project URL
  SUPABASE_KEY         - Supabase anon (or service) key
"""

import os
import logging

import telebot
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("linknest-bot")

# ---- Config / env vars --------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variable")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---- Helpers --------------------------------------------------------------
def get_all_keywords():
    """Return a list of keyword strings currently stored."""
    response = supabase.table("links").select("keyword").order("keyword").execute()
    return [row["keyword"] for row in response.data]


def get_link_for_keyword(keyword: str):
    """Return the link string for an exact (case-insensitive) keyword match, or None."""
    response = (
        supabase.table("links")
        .select("link")
        .ilike("keyword", keyword)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]["link"]
    return None


# ---- Handlers ---------------------------------------------------------------
@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    try:
        keywords = get_all_keywords()
    except Exception as e:
        log.error("Failed to fetch keywords: %s", e)
        bot.reply_to(message, "Something went wrong fetching keywords. Try again shortly.")
        return

    if not keywords:
        bot.reply_to(
            message,
            "👋 Welcome! There are no keywords set up yet. Check back soon.",
        )
        return

    keyword_list = "\n".join(f"• {kw}" for kw in keywords)
    text = (
        "👋 <b>Welcome to LinkNest!</b>\n\n"
        "Send me any of these keywords and I'll send you the link:\n\n"
        f"{keyword_list}"
    )
    bot.reply_to(message, text)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message):
    keyword = message.text.strip()

    try:
        link = get_link_for_keyword(keyword)
    except Exception as e:
        log.error("Lookup failed for '%s': %s", keyword, e)
        bot.reply_to(message, "Something went wrong looking that up. Try again shortly.")
        return

    if link:
        bot.reply_to(message, link)
    else:
        bot.reply_to(
            message,
            "❌ Keyword not found. Send /start to see the list of available keywords.",
        )


# ---- Entry point --------------------------------------------------------------
if __name__ == "__main__":
    log.info("LinkNest bot starting (long polling)...")
    bot.infinity_polling(skip_pending=True)
