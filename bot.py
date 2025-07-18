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

SOURCE_GROUPS = [-1002854404728]  # Default source group
TARGET_GROUPS = []  # Default target groups

ADMIN_ID = 5387926427  # Your Telegram user ID
WELCOME_IMAGE = "https://cdn.nekos.life/neko/neko370.jpeg"
# =====================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client(
    "cc_scraper_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ========== Helper Functions ==========
def extract_credit_cards(text):
    """Extract CCs in format 1234567890123456|12|2025|123"""
    pattern = r'\b(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})\b'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    card_number, month, year, cvv = cc
    return f"💳 Card: <code>{card_number}|{month}|{year}|{cvv}</code>"

async def delete_after_delay(message, delay=300):
    """Delete message after delay (default: 5 minutes)"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Delete failed: {e}")

async def verify_admin(chat_id, user_id):
    """Check if user/bot is admin"""
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Admin check failed: {e}")
        return False

# ========== Command Handlers ==========
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
        [InlineKeyboardButton("🆔 Get Group ID", callback_data="get_group_id")]
    ])
    
    await message.reply_photo(
        photo=WELCOME_IMAGE,
        caption="🔹 <b>CC Scraper Bot</b> 🔹\n\n"
                "Add me to your group with admin rights to start.\n"
                "I'll forward valid CCs to authorized channels.\n\n"
                "Admin: @approvedccm_bot",
        reply_markup=keyboard
    )

@app.on_message(filters.command("id"))
async def get_id_command(client, message: Message):
    chat_id = message.chat.id
    reply = (
        f"👤 <b>Your ID:</b> <code>{message.from_user.id}</code>\n"
        f"👥 <b>Chat ID:</b> <code>{chat_id}</code>"
    )
    await message.reply(reply, parse_mode=ParseMode.HTML)

# ========== Admin Commands ==========
@app.on_message(filters.command("addgroup") & filters.user(ADMIN_ID))
async def add_source_group(client, message: Message):
    if len(message.command) < 2:
        await message.reply("❌ Usage: /addgroup <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id in SOURCE_GROUPS:
            await message.reply(f"ℹ️ Group already in sources: <code>{group_id}</code>")
            return
            
        SOURCE_GROUPS.append(group_id)
        reply = (
            f"✅ <b>Added Source Group</b>\n"
            f"ID: <code>{group_id}</code>\n"
        )
        
        # Verify bot admin status
        if not await verify_admin(group_id, "me"):
            reply += "⚠️ <i>Warning: Bot is not admin in this group</i>"
        
        await message.reply(reply, parse_mode=ParseMode.HTML)
        
    except ValueError:
        await message.reply("❌ Invalid group ID. Must be numeric.")

# (Similar handlers for addtarget, removegroup, removetarget...)

@app.on_message(filters.command("test") & filters.user(ADMIN_ID))
async def test_bot(client, message: Message):
    """Test if bot can send to target groups"""
    if not TARGET_GROUPS:
        await message.reply("❌ No target groups configured")
        return
    
    success = 0
    for group_id in TARGET_GROUPS:
        try:
            await app.send_message(group_id, "✅ Bot connectivity test successful!")
            success += 1
        except Exception as e:
            logger.error(f"Test failed in {group_id}: {e}")
    
    await message.reply(f"Test completed:\n{success}/{len(TARGET_GROUPS)} groups reached")

# ========== Core Functionality ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def handle_messages(client, message: Message):
    # Skip if not from admin or bot not admin
    if not (await verify_admin(message.chat.id, "me") and 
            await verify_admin(message.chat.id, message.from_user.id)):
        return
    
    text = message.text or message.caption
    if not text:
        return
    
    cards = extract_credit_cards(text)
    if not cards:
        return
    
    for cc in cards:
        cc_message = format_card_message(cc)
        for target in TARGET_GROUPS:
            try:
                sent = await app.send_message(
                    target,
                    cc_message,
                    parse_mode=ParseMode.HTML
                )
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logger.error(f"Forward failed to {target}: {e}")

# ========== Bot Events ==========
@app.on_message(filters.new_chat_members)
async def welcome_new_chat(client, message: Message):
    if app.me.id in [u.id for u in message.new_chat_members]:
        welcome_msg = (
            "👋 <b>Thanks for adding me!</b>\n\n"
            "To get started:\n"
            "1. Make me <b>admin</b>\n"
            "2. Send your <code>Group ID</code> to @X_Force_1bot\n"
            "3. Wait for admin approval\n\n"
            "Use <code>/id</code> to get this group's ID"
        )
        await message.reply(welcome_msg, parse_mode=ParseMode.HTML)
        
        # Notify admin
        admin_msg = (
            f"📨 <b>New Group Added</b>\n\n"
            f"🆔 <code>{message.chat.id}</code>\n"
            f"🏷️ {message.chat.title}\n\n"
            f"To approve:\n"
            f"<code>/addgroup {message.chat.id}</code>\n"
            f"<code>/addtarget {message.chat.id}</code>"
        )
        await app.send_message(ADMIN_ID, admin_msg, parse_mode=ParseMode.HTML)

# ========== Start Bot ==========
if __name__ == "__main__":
    print("✅ Bot is running...")
    app.run()
