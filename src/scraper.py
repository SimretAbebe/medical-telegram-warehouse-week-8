import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from loguru import logger

from src.utils import setup_logger, save_json, get_image_path, get_json_path


load_dotenv()

# Read credentials from .env
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
CHANNELS = os.getenv("TELEGRAM_CHANNELS", "").split(",")
SCRAPE_LIMIT = int(os.getenv("SCRAPE_LIMIT", 200))


async def scrape_channel(client: TelegramClient, channel_name: str) -> None:
    logger.info(f"Starting to scrape channel: {channel_name}")

    messages_by_date = {}

    try:
        # Connect to the channel
        from telethon.tl.types import Channel, Chat
        entity = await client.get_entity(channel_name)
        if not isinstance(entity, (Channel, Chat)):
            logger.error(f"Skipping {channel_name} — it is a user account, not a channel")
            return
        logger.info(f"Connected to channel: {entity.title}")

        # Iterate messages safely so one bad message does not stop the whole channel.
        message_iter = client.iter_messages(entity, limit=SCRAPE_LIMIT)
        while True:
            try:
                message = await message_iter.__anext__()
            except StopAsyncIteration:
                break
            except Exception as e:
                logger.error(f"Failed to fetch a message from {channel_name}: {e}")
                continue

            if message is None:
                continue

            try:
                message_data = {
                    "message_id": message.id,
                    "channel_name": channel_name,
                    "channel_title": entity.title,
                    "message_date": str(message.date),
                    "message_text": message.text or "",
                    "has_media": message.media is not None,
                    "image_path": None,
                    "views": message.views or 0,
                    "forwards": message.forwards or 0,
                    "scraped_at": str(datetime.now())
                }

                # Download image if the message has a photo
                if isinstance(message.media, MessageMediaPhoto):
                    try:
                        image_path = get_image_path(channel_name, message.id)
                        await client.download_media(message.media, file=image_path)
                        message_data["image_path"] = image_path
                        logger.debug(f"Downloaded image for message {message.id}")
                    except Exception as e:
                        logger.error(f"Failed to download image for message {message.id}: {e}")
                        message_data["image_path"] = None

                message_date = message.date.strftime("%Y-%m-%d")
                if message_date not in messages_by_date:
                    messages_by_date[message_date] = []
                messages_by_date[message_date].append(message_data)

            except Exception as e:
                logger.error(f"Failed to process message from {channel_name}: {e}")
                continue

        # Save messages to JSON files grouped by date
        for date_str, messages in messages_by_date.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            file_path = get_json_path(channel_name, date_obj)
            save_json(messages, file_path)

        total = sum(len(v) for v in messages_by_date.values())
        logger.info(f"Finished scraping {channel_name}. Total messages: {total}")

    except Exception as e:
        logger.error(f"Error scraping channel {channel_name}: {e}")


async def main():
    # Set up logging first
    setup_logger()

    logger.info("=" * 50)
    logger.info("Starting Telegram Medical Data Scraper")
    logger.info(f"Channels to scrape: {CHANNELS}")
    logger.info(f"Message limit per channel: {SCRAPE_LIMIT}")
    logger.info("=" * 50)

    session_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "telegram_session")
    async with TelegramClient(session_path, API_ID, API_HASH) as client:

        # Login to Telegram
        await client.start(phone=PHONE)
        logger.info("Successfully connected to Telegram!")

        # Scrape each channel one by one
        for channel in CHANNELS:
            channel = channel.strip()
            if channel:
                await scrape_channel(client, channel)
                # Wait 2 seconds 
                await asyncio.sleep(2)

    logger.info("All channels scraped successfully!")


# Run the scraper
if __name__ == "__main__":
    asyncio.run(main())