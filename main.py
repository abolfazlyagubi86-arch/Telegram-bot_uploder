import json
import asyncio
import datetime
import os
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 🔹 تنظیمات مخصوص خودت
BOT_TOKEN = "8513329564:AAH1so9NqLN4fenxh6poKF27shYgjGdvYUQ"
CHANNEL_ID = "@grow_up_pro"
ADMIN_ID = 7959284252  # آیدی عددی خودت

POSTS_FILE = "posts.json"

# 📁 ایجاد فایل پست‌ها در صورت نبود
if not os.path.exists(POSTS_FILE):
    with open(POSTS_FILE, "w") as f:
        json.dump([], f)

# ✅ بررسی ادمین بودن
def is_admin(update: Update):
    return update.effective_user and update.effective_user.id == ADMIN_ID

# 🚀 دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\nبرای زمان‌بندی پست:\n"
        "1️⃣ پستت رو بفرست (متن، عکس یا ویدیو)\n"
        "2️⃣ بعد بنویس: 2025-11-08 18:30\n"
        "ربات خودش تو زمان مشخص پست رو می‌فرسته ✅"
    )

# 🧩 حافظه موقت برای پست‌ها
pending_posts = {}

# 🖼 گرفتن پست و زمان
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # اگر پیام کاربر زمان باشه
    if update.message.text and update.message.text.count(":") == 1 and len(update.message.text.split(" ")) == 2:
        if user_id not in pending_posts:
            await update.message.reply_text("⚠️ اول پستت رو بفرست بعد زمانش رو وارد کن.")
            return

        time_str = update.message.text.strip()
        try:
            send_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await update.message.reply_text("❌ فرمت اشتباهه. مثال درست:\n2025-11-08 18:30")
            return

        with open(POSTS_FILE, "r") as f:
            posts = json.load(f)

        post = pending_posts.pop(user_id)
        post["time"] = send_time.strftime("%Y-%m-%d %H:%M")
        posts.append(post)

        with open(POSTS_FILE, "w") as f:
            json.dump(posts, f)

        await update.message.reply_text(f"✅ پست برای {post['time']} ذخیره شد.")

    else:
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            caption = update.message.caption or ""
            pending_posts[user_id] = {"type": "photo", "file_id": file_id, "caption": caption}
            await update.message.reply_text("📅 حالا زمان ارسال رو بنویس مثل: 2025-11-08 18:30")

        elif update.message.video:
            file_id = update.message.video.file_id
            caption = update.message.caption or ""
            pending_posts[user_id] = {"type": "video", "file_id": file_id, "caption": caption}
            await update.message.reply_text("📅 حالا زمان ارسال رو بنویس مثل: 2025-11-08 18:30")

        elif update.message.text:
            text = update.message.text
            pending_posts[user_id] = {"type": "text", "content": text}
            await update.message.reply_text("📅 حالا زمان ارسال رو بنویس مثل: 2025-11-08 18:30")

# 📋 لیست پست‌ها
async def list_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(POSTS_FILE, "r") as f:
        posts = json.load(f)

    if not posts:
        await update.message.reply_text("📭 هنوز پستی زمان‌بندی نشده.")
        return

    msg = "🗓 پست‌های زمان‌بندی‌شده:\n\n"
    for i, p in enumerate(posts, start=1):
        msg += f"{i}. [{p['type']}] {p['time']}\n"
        if p['type'] == 'text':
            msg += f"   📝 {p['content'][:40]}...\n"
        msg += "\n"

    await update.message.reply_text(msg)

# ❌ حذف پست
async def delete_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ فقط ادمین می‌تونه پست حذف کنه.")
        return

    if len(context.args) < 1 or not context.args[0].isdigit():
        await update.message.reply_text("❌ لطفاً شماره پست رو وارد کن. مثال:\n/delete 2")
        return

    index = int(context.args[0]) - 1
    with open(POSTS_FILE, "r") as f:
        posts = json.load(f)

    if index < 0 or index >= len(posts):
        await update.message.reply_text("❌ شماره پست معتبر نیست.")
        return

    removed = posts.pop(index)
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f)

    await update.message.reply_text(f"🗑 پست {removed['time']} حذف شد.")

# ⏰ زمان‌بندی ارسال پست‌ها
async def scheduler(bot: Bot):
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(POSTS_FILE, "r") as f:
            posts = json.load(f)

        sent = []
        for post in posts:
            if post["time"] == now:
                try:
                    if post["type"] == "text":
                        await bot.send_message(CHANNEL_ID, post["content"])
                    elif post["type"] == "photo":
                        await bot.send_photo(CHANNEL_ID, post["file_id"], caption=post["caption"])
                    elif post["type"] == "video":
                        await bot.send_video(CHANNEL_ID, post["file_id"], caption=post["caption"])
                    sent.append(post)
                except Exception as e:
                    print("❌ خطا در ارسال:", e)

        if sent:
            posts = [p for p in posts if p not in sent]
            with open(POSTS_FILE, "w") as f:
                json.dump(posts, f)

        await asyncio.sleep(30)

# 🎯 اجرای ربات
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_posts))
    app.add_handler(CommandHandler("delete", delete_post))
    app.add_handler(MessageHandler(filters.ALL, receive_message))

    bot = Bot(BOT_TOKEN)
    asyncio.create_task(scheduler(bot))
    print("🤖 ربات فعال شد و آماده است...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
