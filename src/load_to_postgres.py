import os
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from loguru import logger

# Load environment variables from .env file
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "medical_warehouse")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "data/raw/telegram_messages")


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Successfully connected to PostgreSQL!")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise


def create_raw_table(conn):
    create_table_sql = """
        -- Create raw schema if it does not exist
        CREATE SCHEMA IF NOT EXISTS raw;

        -- Create the raw messages table
        -- IF NOT EXISTS means: if table already exists, don't crash, just skip
        CREATE TABLE IF NOT EXISTS raw.telegram_messages (
            id              SERIAL PRIMARY KEY,  -- auto-generated unique ID for each row
            message_id      BIGINT,              -- the original Telegram message ID
            channel_name    VARCHAR(255),        -- username of the Telegram channel
            channel_title   VARCHAR(255),        -- display name of the channel
            message_date    TIMESTAMP,           -- when the message was posted
            message_text    TEXT,                -- the full text of the message
            has_media       BOOLEAN,             -- did the message have a photo/file?
            image_path      TEXT,                -- where we saved the image on disk
            views           INTEGER,             -- how many people viewed the message
            forwards        INTEGER,             -- how many times it was forwarded
            scraped_at      TIMESTAMP,           -- when WE scraped this message
            source_file     TEXT                 -- which JSON file this came from
        );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()
            logger.info("Raw table created successfully!")
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        conn.rollback()
        raise


def read_json_files():
    all_messages = []
    pattern = os.path.join(RAW_DATA_PATH, "**", "*.json")
    json_files = glob.glob(pattern, recursive=True)

    logger.info(f"Found {len(json_files)} JSON files to load")

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            for message in messages:
                message["source_file"] = file_path

            all_messages.extend(messages)
            logger.debug(f"Read {len(messages)} messages from {file_path}")

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")

    logger.info(f"Total messages read from data lake: {len(all_messages)}")
    return all_messages


def load_messages_to_postgres(conn, messages):
    if not messages:
        logger.warning("No messages to load!")
        return
    rows = []
    for msg in messages:
        try:
            rows.append((
                msg.get("message_id"),
                msg.get("channel_name"),
                msg.get("channel_title"),
                msg.get("message_date"),
                msg.get("message_text", ""),
                msg.get("has_media", False),
                msg.get("image_path"),
                msg.get("views", 0),
                msg.get("forwards", 0),
                msg.get("scraped_at"),
                msg.get("source_file")
            ))
        except Exception as e:
            logger.error(f"Failed to prepare message {msg.get('message_id')}: {e}")

    # SQL INSERT statement
    insert_sql = """
        INSERT INTO raw.telegram_messages (
            message_id,
            channel_name,
            channel_title,
            message_date,
            message_text,
            has_media,
            image_path,
            views,
            forwards,
            scraped_at,
            source_file
        ) VALUES %s
        ON CONFLICT DO NOTHING
    """

    try:
        with conn.cursor() as cur:
            # execute_values inserts all rows in one efficient batch
            execute_values(cur, insert_sql, rows)
            conn.commit()
            logger.info(f"Successfully loaded {len(rows)} messages into PostgreSQL!")
    except Exception as e:
        logger.error(f"Failed to insert messages: {e}")
        conn.rollback()
        raise


def verify_load(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.telegram_messages")
        count = cur.fetchone()[0]

        cur.execute("""
            SELECT channel_name, COUNT(*) as total
            FROM raw.telegram_messages
            GROUP BY channel_name
            ORDER BY total DESC
        """)
        channel_counts = cur.fetchall()

    logger.info(f"Total rows in database: {count}")
    logger.info("Messages per channel:")
    for channel, total in channel_counts:
        logger.info(f"  {channel}: {total} messages")


def main():
    logger.info("Starting data load from JSON to PostgreSQL")

    
    conn = get_db_connection()

    try:
       
        create_raw_table(conn)

        
        messages = read_json_files()

        
        load_messages_to_postgres(conn, messages)

        
        verify_load(conn)

        logger.info("Data load completed successfully!")

    finally:
        conn.close()
        logger.info("Database connection closed.")


if __name__ == "__main__":
    main()