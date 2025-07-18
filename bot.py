import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatMemberStatus

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "8039426526:AAFSqWU-fRl_gwTPqYLK8yxuS0N9at1hC4s"

SOURCE_GROUPS = [-1002854404728]
TARGET_GROUPS = []

ADMIN_ID = 5387926427
WELCOME_IMAGE = "https://cdn.nekos.life/neko/neko370.jpeg"
# =====================================

logging.basicConfig(level=logging.INFO)
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== Helper Functions ==========
def extract_credit_cards(text):
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"Card: <code>{card_number}|{month}|{year}|{cvv}</code>\n"

async def delete_after_delay(message, delay=120):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Error deleting message: {e}")

async def is_bot_admin(chat_id):
    try:
        member = await app.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def is_user_admin(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

# ========== Start & ID ==========
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
        [InlineKeyboardButton("🆔 Get Group ID", callback_data="get_group_id")]
    ])
    await message.reply_photo(
        photo=WELCOME_IMAGE,
        caption="✅ Welcome to the bot!\n\nAdd me to your group as an admin to start.\n\nFor issues: @approvedccm_bot",
        reply_markup=keyboard
    )

@app.on_message(filters.command("id"))
async def get_id_command(client, message: Message):
    if message.chat.type != "private" and not await is_user_admin(message.chat.id, message.from_user.id):
        return
    await message.reply(f"👥 Chat ID: <code>{message.chat.id}</code>", parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.reply(
        "👥 Add me to your group, make me admin, then send /id here to get your group ID."
    )

@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command(["start", "id"]))
async def handle_group_id_submission(client, message: Message):
    group_id = int(message.text)
    await message.reply("✅ Your group ID has been sent to the admin.")
    await app.send_message(
        ADMIN_ID,
        f"📨 Group ID submission:\n<code>{group_id}</code>\nUser: {message.from_user.mention} (<code>{message.from_user.id}</code>)\n"
        f"/addgroup {group_id}\n/addtarget {group_id}",
        parse_mode=ParseMode.HTML
    )

# ========== Admin Commands ==========
@app.on_message(filters.command("addgroup") & filters.user(ADMIN_ID))
async def add_source_group(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /addgroup <group_id>")
    try:
        group_id = int(message.command[1])
        if group_id not in SOURCE_GROUPS:
            SOURCE_GROUPS.append(group_id)
            await message.reply(f"✅ Added source group: {group_id}")
        else:
            await message.reply(f"ℹ️ Already in source list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid group ID.")

@app.on_message(filters.command("addtarget") & filters.user(ADMIN_ID))
async def add_target_group(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /addtarget <group_id>")
    try:
        group_id = int(message.command[1])
        if group_id not in TARGET_GROUPS:
            TARGET_GROUPS.append(group_id)
            await message.reply(f"✅ Added target group: {group_id}")
        else:
            await message.reply(f"ℹ️ Already in target list: {group_id}")
    except ValueError:
        await message.reply("❌ Invalid group ID.")

@app.on_message(filters.command("listsources") & filters.user(ADMIN_ID))
async def list_sources(client, message: Message):
    if not SOURCE_GROUPS:
        return await message.reply("No source groups.")
    text = "\n".join(f"<code>{gid}</code>" for gid in SOURCE_GROUPS)
    await message.reply("📋 Source Groups:\n" + text, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("listtargets") & filters.user(ADMIN_ID))
async def list_targets(client, message: Message):
    if not TARGET_GROUPS:
        return await message.reply("No target groups.")
    text = "\n".join(f"<code>{gid}</code>" for gid in TARGET_GROUPS)
    await message.reply("📋 Target Groups:\n" + text, parse_mode=ParseMode.HTML)

@app.on_message(filters.command("removegroup") & filters.user(ADMIN_ID))
async def remove_source_group(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /removegroup <group_id>")
    try:
        group_id = int(message.command[1])
        if group_id in SOURCE_GROUPS:
            SOURCE_GROUPS.remove(group_id)
            await message.reply(f"✅ Removed source group: {group_id}")
        else:
            await message.reply("ℹ️ Not in source list.")
    except ValueError:
        await message.reply("❌ Invalid group ID.")

@app.on_message(filters.command("removetarget") & filters.user(ADMIN_ID))
async def remove_target_group(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /removetarget <group_id>")
    try:
        group_id = int(message.command[1])
        if group_id in TARGET_GROUPS:
            TARGET_GROUPS.remove(group_id)
            await message.reply(f"✅ Removed target group: {group_id}")
        else:
            await message.reply("ℹ️ Not in target list.")
    except ValueError:
        await message.reply("❌ Invalid group ID.")

# ========== NEW: Admin Reply by User ID ==========
@app.on_message(filters.command("reply") & filters.user(ADMIN_ID))
async def admin_reply_user(client, message: Message):
    if len(message.command) < 3:
        return await message.reply("Usage: /reply <user_id> <message>")
    try:
        user_id = int(message.command[1])
        user_message = " ".join(message.command[2:])
        await app.send_message(user_id, user_message)
        await message.reply(f"✅ Message sent to user {user_id}")
    except Exception as e:
        await message.reply(f"❌ Failed to send: {e}")

# ========== Prevent Unauthorized Admin Commands ==========
@app.on_message(filters.command(["addgroup", "addtarget", "removegroup", "removetarget", "listsources", "listtargets", "reply"]) & ~filters.user(ADMIN_ID))
async def unauthorized_admin_command(client, message: Message):
    await message.reply("❌ You are not authorized to use this command.")

# ========== CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    if not await is_bot_admin(message.chat.id):
        logging.warning(f"❌ Bot is not admin in source group: {message.chat.id}")
        return

    if message.from_user and message.from_user.is_bot:
        return

    text = message.text or message.caption
    if not text:
        return

    cards = extract_credit_cards(text)
    if not cards:
        return

    for cc in cards:
        msg_text = format_card_message(cc)
        for group_id in TARGET_GROUPS:
            if not await is_bot_admin(group_id):
                logging.warning(f"⚠️ Bot is NOT admin in target {group_id}, skipping")
                continue
            try:
                sent = await app.send_message(group_id, msg_text, parse_mode=ParseMode.HTML)
                asyncio.create_task(delete_after_delay(sent))
                logging.info(f"✅ Sent card to target group {group_id}")
            except Exception as e:
                logging.error(f"❌ Error sending to {group_id}: {e}")

# ========== New Group Added ==========
@app.on_message(filters.new_chat_members)
async def new_chat_members(client, message: Message):
    if app.me.id in [user.id for user in message.new_chat_members]:
        await message.reply(
            "👋 Thanks for adding me!\nMake me admin and send your group ID to @approvedccm_bot.\nUse /id to get group ID."
        )
        await app.send_message(
            ADMIN_ID,
            f"🆕 Bot added to group:\n<code>{message.chat.id}</code>\n{message.chat.title}\n/addgroup {message.chat.id}\n/addtarget {message.chat.id}",
            parse_mode=ParseMode.HTML
        )

# ========== Run Bot ==========
print("✅ Bot is running...")
app.run()
