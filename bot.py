import asyncio
import os

from dotenv import load_dotenv
from faster_whisper import WhisperModel
from langchain.chat_models import ChatAnthropic
from telebot import asyncio_filters, asyncio_helper, logger, logging
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from telebot.types import CallbackQuery, Message

from message_db import MessageDB

load_dotenv()

# Bot setup
# asyncio_helper.proxy = os.getenv("HTTPS_PROXY")  # Optional proxy setup
bot = AsyncTeleBot(token=os.getenv("TG_BOT", ""))
logger.setLevel(logging.INFO)

# Handler filters
allowed_users = [
    int(user_id) for user_id in os.getenv("ALLOWED_USERS", "").split(",") if user_id
]
voice_callback = CallbackData("task", prefix="voice_callback")

# Database setup
db = MessageDB()

# Model setup
chat_model = ChatAnthropic(model="claude-2.1", max_tokens=4096, temperature=0)
whisper = WhisperModel("small", device="cpu", compute_type="int8")


@bot.message_handler(chat_id=allowed_users, commands=["clear"])
async def clear_history(message: Message):
    db.clear_history(message)
    await bot.reply_to(message, text="History cleared.")


@bot.message_handler(chat_id=allowed_users, commands=["dalle"])
async def generate_image(message: Message):
    import openai
    from telebot.util import extract_arguments

    client = openai.AsyncOpenAI()
    image_prompt = extract_arguments(message.text) or message.text
    if not image_prompt.strip():
        await bot.reply_to(message, text="Please specify the prompt")
        return
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        response = await client.images.generate(
            model=f"dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image = response.data[0]
        await bot.send_photo(
            chat_id=message.chat.id, photo=image.url, caption=image.revised_prompt
        )
    except openai.OpenAIError as e:
        error_message = f"[!] Bot exception:\n{e}"
        logger.error(error_message)
        await bot.reply_to(
            message,
            text=error_message,
        )


@bot.message_handler(chat_id=allowed_users, content_types=["voice"])
async def transcript(message: Message):
    import io

    from telebot.util import quick_markup

    voice_file_info = await bot.get_file(message.voice.file_id)
    voice_bytes = await bot.download_file(voice_file_info.file_path)
    voice_file = io.BytesIO(voice_bytes)

    message_sent = await bot.reply_to(message, text="Transcribing voice message...")
    segments, _ = await asyncio.to_thread(whisper.transcribe, voice_file)
    transcripts = "".join(segment.text for segment in segments)
    if not transcripts.strip():
        await bot.edit_message_text(
            text="No transcripts found.",
            chat_id=message_sent.chat.id,
            message_id=message_sent.message_id,
        )
        return

    await bot.edit_message_text(
        text=transcripts,
        chat_id=message_sent.chat.id,
        message_id=message_sent.message_id,
        reply_markup=quick_markup(
            {
                "❓ Ask GPT": {"callback_data": voice_callback.new(task="ask_gpt")},
                "🎨 Dream": {"callback_data": voice_callback.new(task="dream")},
            }
        ),
    )


@bot.callback_query_handler(chat_id=allowed_users, func=voice_callback.filter().check)
async def voice_callback_handler(call: CallbackQuery):
    callback_data: dict = voice_callback.parse(callback_data=call.data)

    task = callback_data.get("task")
    if task == "ask_gpt":
        call.message.from_user.is_bot = False
        await chat_query(call.message)
    elif task == "dream":
        await generate_image(call.message)


@bot.message_handler(chat_id=allowed_users, content_types=["text"])
async def chat_query(message: Message):
    from mistletoe import markdown

    from telegram_html_render import TelegramHtmlRenderer

    if not message.text.strip():
        await bot.reply_to(message, text="Please specify the query")
        return
    api_task = asyncio.create_task(bot.reply_to(message, text="Generating..."))
    message_sent = await api_task

    db.add_message(message)
    messages = db.get_all_history(message)  # Retrieve history including current query

    bot_response = ""
    async for chunk in chat_model.astream(messages):
        bot_response += chunk.content
        if api_task.done() and bot_response.strip():
            api_task = asyncio.create_task(
                bot.edit_message_text(
                    text=bot_response,
                    chat_id=message_sent.chat.id,
                    message_id=message_sent.message_id,
                )
            )

        await asyncio.sleep(0.1)

    if not bot_response.strip():
        await bot.edit_message_text(
            text="No response received.",
            chat_id=message_sent.chat.id,
            message_id=message_sent.message_id,
        )
        return

    message_sent = await api_task
    message_sent.text = bot_response  # Prevent incomplete message stored
    db.add_message(message_sent)

    try:
        await bot.edit_message_text(
            text=markdown(bot_response, TelegramHtmlRenderer),
            chat_id=message_sent.chat.id,
            message_id=message_sent.message_id,
            parse_mode="HTML",
        )
    except asyncio_helper.ApiTelegramException as e:
        if "message is not modified" not in e.description:
            error_message = f"[!] Bot exception:\n{e.description}"
            logger.error(error_message)
            await bot.reply_to(
                message_sent,
                text=error_message,
            )


bot.add_custom_filter(asyncio_filters.ChatFilter())

asyncio.run(bot.infinity_polling())
