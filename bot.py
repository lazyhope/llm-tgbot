import asyncio
import os

from faster_whisper import WhisperModel
from langchain.chat_models import ChatAnthropic
from telebot import asyncio_filters, asyncio_helper
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from telebot.types import CallbackQuery, Message

asyncio_helper.proxy = os.getenv("HTTPS_PROXY")
allowed_users = []
bot = AsyncTeleBot(token=os.getenv("TG_BOT", ""))

claude = ChatAnthropic(model="claude-2.1", max_tokens=1024, temperature=0)

chat_model = claude
whisper = WhisperModel("large-v2", device="cpu", compute_type="int8")
voice_callback = CallbackData("task", "prompt", prefix="voice_callback")


@bot.message_handler(chat_id=allowed_users, commands=["dalle"])
async def generate_image(message: Message):
    import openai
    from telebot.util import extract_arguments

    client = openai.AsyncOpenAI()
    image_prompt = extract_arguments(message.text)
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
        await bot.reply_to(
            message,
            text=f"[!] Bot exception:\n{e}",
        )


@bot.message_handler(chat_id=allowed_users, content_types=["voice"])
async def transcript(message: Message):
    import io

    from telebot.util import quick_markup

    voice_file_info = await bot.get_file(message.voice.file_id)
    voice_bytes = await bot.download_file(voice_file_info.file_path)
    voice_file = io.BytesIO(voice_bytes)

    print("[+] Transcribing voice message...")
    segments, _ = await asyncio.to_thread(whisper.transcribe, voice_file)
    transcripts = "".join(segment.text for segment in segments)

    await bot.reply_to(
        message,
        text=f"Transcripts: {transcripts}",
        reply_markup=quick_markup(
            {
                "❓ Ask GPT": {
                    "callback_data": voice_callback.new(
                        task="ask_gpt", prompt=transcripts
                    )
                },
                "🎨 Dream": {
                    "callback_data": voice_callback.new(
                        task="dream", prompt=f"/dalle {transcripts}"
                    )
                },
            }
        ),
    )


@bot.callback_query_handler(chat_id=allowed_users, func=voice_callback.filter().check)
async def voice_callback_handler(call: CallbackQuery):
    callback_data: dict = voice_callback.parse(callback_data=call.data)

    call.message.text = callback_data.get("prompt")
    task = callback_data.get("task")
    if task == "ask_gpt":
        await chat_query(call.message)
    elif task == "dream":
        await generate_image(call.message)


@bot.message_handler(chat_id=allowed_users, content_types=["text"])
async def chat_query(message: Message):
    from mistletoe import markdown

    from telegram_html_render import TelegramHtmlRenderer

    if message.text.isspace():
        await bot.reply_to(message, text="Please specify the query")
        return
    api_task = asyncio.create_task(bot.reply_to(message, text="Generating..."))
    message_sent = await api_task

    bot_response = ""
    user_query = message.text
    print(f"[User] {user_query}")
    async for chunk in chat_model.astream(user_query):
        print(chunk.content, end="", flush=True)

        bot_response += chunk.content
        if api_task.done() and not bot_response.isspace():
            api_task = asyncio.create_task(
                bot.edit_message_text(
                    text=bot_response,
                    chat_id=message_sent.chat.id,
                    message_id=message_sent.message_id,
                )
            )

        await asyncio.sleep(0.1)

    print(f"\n[Bot] {bot_response}")
    print("[+] Chat message completed.")
    if bot_response.isspace():
        return

    try:
        await bot.edit_message_text(
            text=markdown(bot_response, TelegramHtmlRenderer),
            chat_id=message_sent.chat.id,
            message_id=message_sent.message_id,
            parse_mode="HTML",
        )
    except asyncio_helper.ApiTelegramException as e:
        print(f"[!] Error Log: {e.description}")
        if "message is not modified" not in e.description:
            await bot.reply_to(
                message_sent,
                text=f"[!] Bot exception:\n{e.description}",
            )


@bot.message_handler(chat_id=allowed_users, commands=["clear"])
async def clear_history(message: Message):
    chat_id = message.chat.id


bot.add_custom_filter(asyncio_filters.ChatFilter())

print("[+] Bot severing...")
asyncio.run(bot.polling())
