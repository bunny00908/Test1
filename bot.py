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
TARGET_GROUPS = []  # Default target groups (must be groups, not channels)

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
    """Extract credit card information using regex pattern"""
    pattern = r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})'
    return re.findall(pattern, text or "")

def format_card_message(cc):
    """Format extracted CC information into readable message"""
    card_number, month, year, cvv = cc
    return f"💳 Card: <code>{card_number}|{month}|{year}|{cvv}</code>\n"

async def delete_after_delay(message, delay=120):
    """Delete message after specified delay"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Error deleting message: {e}")

async def is_bot_admin(chat_id):
    """Check if bot is admin in specified chat"""
    try:
        member = await app.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

async def is_user_admin(chat_id, user_id):
    """Check if user is admin in specified chat"""
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"User admin check error: {e}")
        return False

async def is_group(chat_id):
    """Verify if chat is a group/supergroup"""
    try:
        chat = await app.get_chat(chat_id)
        return chat.type in ["group", "supergroup"]
    except Exception as e:
        logger.error(f"Group check error: {e}")
        return False

# ========== Command Handlers ==========
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Handle /start command with welcome message"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
        [InlineKeyboardButton("🆔 Get Group ID", callback_data="get_group_id")]
    ])
    
    await message.reply_photo(
        photo=WELCOME_IMAGE,
        caption="🤖 Welcome to CC Scraper Bot!\n\n"
                "🔹 Add me to your group as admin\n"
                "🔹 Only admins can post CCs\n"
                "🔹 Auto-forward to target groups\n\n"
                "Contact: @approvedccm_bot for support",
        reply_markup=keyboard
    )

@app.on_message(filters.command("id"))
async def get_id_command(client, message: Message):
    """Handle /id command to show chat ID"""
    if message.chat.type != "private" and not await is_user_admin(message.chat.id, message.from_user.id):
        return
    
    chat_id = message.chat.id
    reply_text = (
        f"👥 Chat ID: <code>{chat_id}</code>\n"
        f"💬 Type: {message.chat.type}\n"
        f"📛 Title: {message.chat.title or 'Private Chat'}"
    )
    await message.reply(reply_text, parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    """Handle group ID callback query"""
    await callback_query.answer()
    await callback_query.message.reply(
        "📌 How to get Group ID:\n\n"
        "1. Add me to your group\n"
        "2. Make me admin\n"
        "3. Send /id command in group\n"
        "4. Copy the ID and send it here\n\n"
        "⚠️ Note: Only approved groups will be activated"
    )

# ========== Group Management ==========
@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command())
async def handle_group_id_submission(client, message: Message):
    """Process submitted group IDs"""
    group_id = int(message.text)
    
    # Verify group exists and bot is member
    try:
        chat = await app.get_chat(group_id)
        if chat.type not in ["group", "supergroup"]:
            await message.reply("❌ This ID is not a group. Please provide a group ID.")
            return
    except Exception as e:
        await message.reply(f"❌ Error accessing group: {str(e)}")
        return

    await message.reply(
        "✅ Group ID received!\n\n"
        "Admin has been notified for approval.\n"
        "You'll receive a confirmation when approved."
    )
    
    # Notify admin with approval buttons
    approve_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Approve as Source", callback_data=f"approve_source_{group_id}"),
            InlineKeyboardButton("Approve as Target", callback_data=f"approve_target_{group_id}")
        ],
        [InlineKeyboardButton("Reject", callback_data=f"reject_{group_id}")]
    ])
    
    await app.send_message(
        ADMIN_ID,
        f"📨 New Group Submission:\n\n"
        f"🆔 ID: <code>{group_id}</code>\n"
        f"📛 Title: {chat.title}\n"
        f"👤 Submitted by: {message.from_user.mention} (ID: {message.from_user.id})",
        reply_markup=approve_buttons,
        parse_mode=ParseMode.HTML
    )

# ========== Admin Callbacks ==========
@app.on_callback_query(filters.regex(r"^approve_(source|target)_(\-?\d+)$"))
async def approve_group_callback(client, callback_query):
    """Handle group approval callbacks"""
    action, group_id = callback_query.matches[0].groups()
    group_id = int(group_id)
    
    try:
        chat = await app.get_chat(group_id)
        if not await is_group(group_id):
            await callback_query.answer("❌ Not a valid group!", show_alert=True)
            return
            
        if action == "source":
            if group_id not in SOURCE_GROUPS:
                SOURCE_GROUPS.append(group_id)
                list_name = "source groups"
        else:
            if group_id not in TARGET_GROUPS:
                TARGET_GROUPS.append(group_id)
                list_name = "target groups"
                
        await callback_query.answer(f"✅ Added to {list_name}!", show_alert=True)
        await callback_query.message.edit_text(
            f"✅ Approved Group:\n\n"
            f"🆔 ID: <code>{group_id}</code>\n"
            f"📛 Title: {chat.title}\n"
            f"⭐ Type: {'Source' if action == 'source' else 'Target'}",
            parse_mode=ParseMode.HTML
        )
        
        # Notify submitter
        try:
            submitter = callback_query.message.reply_to_message.from_user.id
            await app.send_message(
                submitter,
                f"🎉 Your group has been approved!\n\n"
                f"📛 {chat.title}\n"
                f"🆔 <code>{group_id}</code>\n"
                f"⭐ Type: {'Source' if action == 'source' else 'Target'}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error notifying submitter: {e}")

    except Exception as e:
        logger.error(f"Approval error: {e}")
        await callback_query.answer("❌ Approval failed!", show_alert=True)

# ========== Admin Commands ==========
@app.on_message(filters.command("reply") & filters.user(ADMIN_ID))
async def admin_reply(client, message: Message):
    """Allow admin to reply to users by ID"""
    if len(message.command) < 3:
        await message.reply("Usage: /reply <user_id> <message>")
        return
    
    try:
        user_id = int(message.command[1])
        reply_text = " ".join(message.command[2:])
        
        try:
            await app.send_message(
                user_id,
                f"📨 Admin Reply:\n\n{reply_text}",
                parse_mode=ParseMode.HTML
            )
            await message.reply(f"✅ Reply sent to user {user_id}")
        except Exception as e:
            await message.reply(f"❌ Failed to send to user {user_id}: {str(e)}")
    except ValueError:
        await message.reply("❌ Invalid user ID. Must be numeric.")

@app.on_message(filters.command("listsources") & filters.user(ADMIN_ID))
async def list_source_groups(client, message: Message):
    """List all source groups"""
    if not SOURCE_GROUPS:
        await message.reply("❌ No source groups configured")
        return
    
    groups_info = []
    for group_id in SOURCE_GROUPS:
        try:
            chat = await app.get_chat(group_id)
            groups_info.append(f"📛 {chat.title} (ID: <code>{group_id}</code>)")
        except Exception:
            groups_info.append(f"❓ Unknown Group (ID: <code>{group_id}</code>)")
    
    await message.reply(
        "📋 Source Groups:\n\n" + "\n".join(groups_info),
        parse_mode=ParseMode.HTML
    )

# [Similar listtargets, removegroup, removetarget commands...]

# ========== CC Processing ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def process_cc_messages(client, message: Message):
    """Process messages in source groups for CC info"""
    # Verify bot and sender permissions
    if not await is_bot_admin(message.chat.id):
        return
        
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return
        
    if message.from_user and message.from_user.is_bot:
        return
    
    # Extract and validate CC info
    text = message.text or message.caption
    if not text:
        return
        
    cards = extract_credit_cards(text)
    if not cards:
        return

    # Forward to all target groups
    for cc in cards:
        cc_message = format_card_message(cc)
        for target_id in TARGET_GROUPS:
            try:
                sent = await app.send_message(
                    target_id,
                    f"🔔 New CC from {message.chat.title}:\n\n{cc_message}",
                    parse_mode=ParseMode.HTML
                )
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logger.error(f"Forward error to {target_id}: {e}")

# ========== Group Events ==========
@app.on_message(filters.new_chat_members)
async def welcome_new_chat(client, message: Message):
    """Welcome message when added to new group"""
    if app.me.id in [user.id for user in message.new_chat_members]:
        welcome_msg = (
            "👋 Thanks for adding me!\n\n"
            "To activate this group:\n"
            "1. Make me admin\n"
            "2. Send your group ID to @approvedccm_bot\n"
            "3. Wait for admin approval\n\n"
            "Use /id to get this group's ID"
        )
        
        try:
            await message.reply(welcome_msg)
        except Exception as e:
            logger.error(f"Welcome message error: {e}")

# ========== Startup ==========
@app.on_raw_update()
async def startup_notify(client, _):
    """Notify admin when bot starts"""
    if not hasattr(startup_notify, "has_run"):
        await app.send_message(
            ADMIN_ID,
            "✅ Bot started successfully!\n\n"
            f"📡 Monitoring {len(SOURCE_GROUPS)} source groups\n"
            f"🎯 Forwarding to {len(TARGET_GROUPS)} target groups"
        )
        startup_notify.has_run = True

if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run()
