import os
import json
from datetime import datetime
from loguru import logger


def setup_logger(log_dir: str = "logs") -> None:
   
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(
        log_dir,
        f"scraper_{datetime.now().strftime('%Y-%m-%d')}.log"
    )


    logger.remove()

    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level}</level> | {message}",
        level="INFO"
    )

    # Log to file
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="1 day", 
        retention="7 days"  
    )

    logger.info(f"Logger initialized. Saving logs to: {log_file}")


def save_json(data: list, file_path: str) -> None:
    # Create the folder if it does not exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Saved {len(data)} messages to {file_path}")


def get_image_path(channel_name: str, message_id: int) -> str:
    folder = os.path.join("data", "raw", "images", channel_name)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{message_id}.jpg")


def get_json_path(channel_name: str, date: datetime) -> str:
    date_str = date.strftime("%Y-%m-%d")
    folder = os.path.join("data", "raw", "telegram_messages", date_str)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{channel_name}.json")