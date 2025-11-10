import json
import asyncio
import aiohttp
import aiofiles

from telegram import (
    Bot,
    InputMediaPhoto,
    LinkPreviewOptions
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.request import HTTPXRequest
from .config import Config
import telegramify_markdown
import io

class Message:
    def __init__(self, body: str, chat_id: int = 0, title = 'Signals Trade', format: str | None = ParseMode.MARKDOWN_V2, image: str | io.BytesIO | None = None, images: list[str] | list[io.BytesIO] | None = None, group_message_id: int | None = None):
        self.title = title
        self.body = body
        self.format = format
        self.image = image
        self.images = images
        self.chat_id = chat_id
        self.group_message_id = group_message_id
    def __str__(self):
        payload = {
            "title": self.title,
            "body": self.body,
            "format": self.format,
            "image": "<image>" if self.image else None,
            "images": f"<{len(self.images)} images>" if self.images else None,
            "chat_id": self.chat_id,
            "group_message_id": self.group_message_id
        }
        return json.dumps(payload)
    def build_text_notify(self):
        return f"**{self.title}**\n{self.body}"


class NotificationHandler:
    def __init__(self, cfg: Config, enabled=True):
        if enabled:
            self.config = cfg
            self.queue = asyncio.Queue()
            self.enabled = True

            self.bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
        else:
            self.enabled = False

    async def notify(self, message: Message):
        text_msg = message.build_text_notify()
        if message.format is not None:
            text_msg = telegramify_markdown.markdownify(text_msg)

        try:
            # case: multiple images
            if message.images and len(message.images) > 1:
                list_media = []
                for index, image in enumerate(message.images):
                    if index == 0:
                        list_media.append(InputMediaPhoto(
                            media=image,
                            caption=text_msg,
                            parse_mode=message.format
                        ))
                    else:
                        list_media.append(InputMediaPhoto(media=image))

                await self.bot.send_media_group(chat_id = message.chat_id, media=list_media, reply_to_message_id=message.group_message_id)

            # case: single image
            elif message.image:
                try:
                    await self.bot.send_photo(chat_id = message.chat_id, photo=message.image, caption = text_msg, parse_mode=message.format, reply_to_message_id=message.group_message_id)
                except TelegramError:
                    # fallback: download then send
                    async with aiohttp.ClientSession() as session:
                        async with session.get(message.image) as resp:
                            resp.raise_for_status()  # Raise exception for HTTP errors
                            async with aiofiles.open("photo.png", "wb") as file:
                                async for chunk in resp.content.iter_chunked(1024):
                                    await file.write(chunk)

                    await self.bot.send_photo(chat_id = message.chat_id, photo="photo.png", caption = text_msg, parse_mode=message.format, reply_to_message_id=message.group_message_id)

            # case: text only
            else:
                await self.bot.send_message(chat_id = message.chat_id, text=text_msg, parse_mode=message.format, link_preview_options=LinkPreviewOptions(is_disabled=True), reply_to_message_id=message.group_message_id)

        except Exception as err:
            # fallback error notification
            await self.bot.send_message(
                chat_id=message.chat_id,
                text=text_msg + f"\nError sending message: {err}",
                parse_mode=message.format,
                reply_to_message_id=message.group_message_id,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )

    async def process_queue(self):
        while True:
            message: Message = await self.queue.get()
            await self.notify(message)

    def send_notification(self, message: Message, attachments=None):
        if self.enabled:
            self.queue.put_nowait(message)