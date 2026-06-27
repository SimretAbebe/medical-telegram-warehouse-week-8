import os
import csv
import glob
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from loguru import logger
from ultralytics import YOLO

load_dotenv()

IMAGES_PATH = os.getenv("IMAGES_PATH", "data/raw/images")
RESULTS_CSV = "data/raw/yolo_detections.csv"
CONFIDENCE_THRESHOLD = 0.3
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "medical_warehouse")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

PRODUCT_CLASSES = {
    "bottle",
    "cup",
    "bowl",
    "vase",
    "book",
    "scissors",
    "toothbrush",
    "cell phone",
    "laptop",
    "clock",
}

PERSON_CLASSES = {"person"}


def classify_image(detected_objects: set) -> str:
    detected_objects = {"person", "bottle"}
    has_person = bool(detected_objects & PERSON_CLASSES)
    has_product = bool(detected_objects & PRODUCT_CLASSES)

    if has_person and has_product:
        return "promotional"
    elif has_product and not has_person:
        return "product_display"
    elif has_person and not has_product:
        return "lifestyle"
    else:
        return "other"


def run_detection(model: YOLO, image_path: str) -> list:
    try:
        results = model(image_path, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                confidence = float(box.conf[0])
                if confidence < CONFIDENCE_THRESHOLD:
                    continue

                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                detections.append({
                    "class_name": class_name,
                    "confidence": round(confidence, 4)
                })

        return detections

    except Exception as e:
        logger.error(f"Failed to process image {image_path}: {e}")
        return []


def extract_info_from_path(image_path: str) -> dict:
    path = Path(image_path)
    message_id = path.stem
    channel_name = path.parent.name

    try:
        message_id = int(message_id)
    except:
        message_id = None

    return {
        "channel_name": channel_name,
        "message_id": message_id
    }


def save_to_csv(all_results: list) -> None:
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "message_id",
            "channel_name",
            "class_name",
            "confidence",
            "image_category",
            "image_path"
        ])
        writer.writeheader()
        writer.writerows(all_results)

    logger.info(f"Saved {len(all_results)} detections to {RESULTS_CSV}")


def load_to_postgres(all_results: list) -> None:
    if not all_results:
        logger.warning("No results to load into PostgreSQL!")
        return

    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Connected to PostgreSQL!")

        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.image_detections (
                    id              SERIAL PRIMARY KEY,
                    message_id      BIGINT,
                    channel_name    VARCHAR(255),
                    class_name      VARCHAR(100),
                    confidence      DECIMAL(5,4),
                    image_category  VARCHAR(50),
                    image_path      TEXT
                );
            """)
            conn.commit()
            logger.info("Table raw.image_detections created!")

            rows = [
                (
                    r["message_id"],
                    r["channel_name"],
                    r["class_name"],
                    r["confidence"],
                    r["image_category"],
                    r["image_path"]
                )
                for r in all_results
            ]

            execute_values(cur, """
                INSERT INTO raw.image_detections
                (message_id, channel_name, class_name,
                 confidence, image_category, image_path)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, rows)

            conn.commit()
            logger.info(f"Loaded {len(rows)} detections into PostgreSQL!")

        conn.close()

    except Exception as e:
        logger.error(f"Failed to load to PostgreSQL: {e}")
        raise


def main():
    logger.info("=" * 50)
    logger.info("Starting YOLO Object Detection Pipeline")
    logger.info("=" * 50)

    logger.info("Loading YOLOv8 nano model...")
    model = YOLO("yolov8n.pt")
    logger.info("YOLO model loaded!")

    pattern = os.path.join(IMAGES_PATH, "**", "*.jpg")
    image_files = glob.glob(pattern, recursive=True)
    logger.info(f"Found {len(image_files)} images to process")

    if not image_files:
        logger.warning("No images found! Make sure Task 1 scraper ran successfully.")
        return

    all_results = []

    for i, image_path in enumerate(image_files):
        logger.info(f"Processing image {i+1}/{len(image_files)}: {image_path}")
        info = extract_info_from_path(image_path)
        detections = run_detection(model, image_path)
        detected_classes = {d["class_name"] for d in detections}
        image_category = classify_image(detected_classes)

        if detections:
            for detection in detections:
                all_results.append({
                    "message_id": info["message_id"],
                    "channel_name": info["channel_name"],
                    "class_name": detection["class_name"],
                    "confidence": detection["confidence"],
                    "image_category": image_category,
                    "image_path": image_path
                })
        else:
            all_results.append({
                "message_id": info["message_id"],
                "channel_name": info["channel_name"],
                "class_name": "none",
                    "confidence": 0.0,
                    "image_category": "other",
                    "image_path": image_path
            })

    logger.info(f"Detection complete! Total detections: {len(all_results)}")
    save_to_csv(all_results)
    load_to_postgres(all_results)

    categories = {}
    for r in all_results:
        cat = r["image_category"]
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("=" * 50)
    logger.info("DETECTION SUMMARY")
    logger.info("=" * 50)
    for cat, count in sorted(categories.items()):
        logger.info(f"  {cat}: {count} images")


if __name__ == "__main__":
    main()
