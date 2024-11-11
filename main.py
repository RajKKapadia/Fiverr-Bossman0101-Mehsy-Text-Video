import threading
import queue
import asyncio
import logging
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Application

import config
from utils import call_meshy_api

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

task_queue = queue.Queue()


async def update_progress_bar(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str, message_id: int, start_time: float):
    progress_chars = ["⬜️", "⬜️", "⬜️", "⬜️",
                      "⬜️", "⬜️", "⬜️", "⬜️", "⬜️", "⬜️"]
    max_duration = 60
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_duration:
            break
        progress = min(elapsed_time / max_duration, 1.0)
        filled_chars = int(progress * len(progress_chars))
        progress_bar = ""
        for i in range(len(progress_chars)):
            if i < filled_chars:
                progress_bar += "🟩"
            else:
                progress_bar += "⬜️"
        status_text = f"Generating 3D Model...\n{progress_bar}\n{int(elapsed_time)}s elapsed"
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=status_text
            )
        except Exception as e:
            logging.error(f"Error updating progress bar: {e}")
            break
        await asyncio.sleep(3)


async def video_long_running_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str, prompt: str):
    progress_message = await context.bot.send_message(
        chat_id=chat_id,
        text="Starting 3D Model generation...\n⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️\n0s elapsed"
    )
    start_time = time.time()
    progress_task = asyncio.create_task(
        update_progress_bar(
            context, chat_id, progress_message.message_id, start_time)
    )
    video_urls, status = await call_meshy_api(prompt=prompt)
    progress_task.cancel()
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=progress_message.message_id
    )
    if status:
        await context.bot.send_video(chat_id=chat_id, video=video_urls[0])
    else:
        await context.bot.send_message(chat_id=chat_id, text="We are facing an issue generating a 3D Model at this moment.")


def process_queue(loop, context: ContextTypes.DEFAULT_TYPE):
    while not task_queue.empty():
        chat_id, task_type, prompt = task_queue.get()
        if task_type == "video":
            asyncio.run_coroutine_threadsafe(
                video_long_running_task(context, chat_id, prompt), loop)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Send Prompt", callback_data="text_to_video")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)


async def text_to_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please provide a prompt to generate your 3D Model in minutes.")
    context.user_data["awaiting_video_prompt"] = True


async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    prompt = update.message.text
    if context.user_data.get("awaiting_video_prompt"):
        await update.message.reply_text("Generating your 3D Model.")
        context.user_data["awaiting_video_prompt"] = False
        task_queue.put((chat_id, "video", prompt))
        loop = asyncio.get_running_loop()
        threading.Thread(target=process_queue, args=(loop, context)).start()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "text_to_video":
        await text_to_video(query, context)


async def post_init(application: Application):
    # Configure commands in the bot menu
    await application.bot.set_my_commands([
        ("send_prompt", "Generate a 3D Model from a text prompt"),
    ])


def main():
    application = ApplicationBuilder().token(
        config.TELEGRAM_BOT_TOKEN).post_init(post_init=post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_prompt", text_to_video))

    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_prompt))

    application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
