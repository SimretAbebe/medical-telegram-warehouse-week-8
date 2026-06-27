# Medical Telegram Data Warehouse

A complete end-to-end data engineering repository for ingesting, transforming,
and analyzing Ethiopian medical Telegram channel data.

This project collects raw Telegram messages and images, stores them in a
lake-style raw dataset, transforms them with dbt, and loads curated data into
PostgreSQL for analytics.

---

## Project Overview

Key capabilities:

- Scrape public Telegram channels and persist raw JSON message data.
- Download channel images and organize them by source.
- Load raw data into PostgreSQL for warehouse consumption.
- Transform raw Telegram data into clean staging and dimensional models with dbt.
- Validate data quality with dbt tests.
- Expose a lightweight API layer for downstream consumption.

---

## Repository Structure

medical-telegram-warehouse/

├── `.github/`
│ └── `workflows/`
│ └── `unittests.yml` # GitHub Actions CI pipeline

├── `.env` # Secrets — DO NOT COMMIT
├── `.env.example` # Safe template for environment setup
├── `.gitignore`
├── `requirements.txt` # Python dependencies
├── `README.md`
├── `docker-compose.yml` # Containerized orchestration setup
├── `Dockerfile` # Image build definition

├── `data/`
│ └── `raw/`
│ ├── `telegram_messages/` # JSON files partitioned by date
│ │ └── `YYYY-MM-DD/`
│ │ └── `channel_name.json`
│ └── `images/` # Downloaded images by channel
│ └── `channel_name/`
│ └── `message_id.jpg`

├── `medical_warehouse/` # dbt project
│ ├── `dbt_project.yml`
│ ├── `profiles.yml`
│ ├── `models/`
│ │ ├── `staging/`
│ │ │ ├── `sources.yml`
│ │ │ ├── `schema.yml`
│ │ │ └── `stg_telegram_messages.sql`
│ │ └── `marts/`
│ │ ├── `schema.yml`
│ │ ├── `dim_channels.sql`
│ │ ├── `dim_dates.sql`
│ │ └── `fct_messages.sql`
│ └── `tests/`
│ ├── `assert_no_future_messages.sql`
│ └── `assert_positive_views.sql`

├── `src/`
│ ├── `__init__.py`
│ ├── `scraper.py` # Telegram scraping pipeline
│ ├── `utils.py` # Helper functions
│ └── `load_to_postgres.py` # Data lake to PostgreSQL loader

├── `logs/` # Scraping activity logs
├── `notebooks/`
├── `api/`
│ ├── `__init__.py`
│ ├── `main.py`
│ ├── `database.py`
│ └── `schemas.py`

├── `tests/`
│ └── `test_placeholder.py`

└── `scripts/`
└── `run_dbt.sh`

---

## Getting Started

1. Create a Python virtual environment:

```bash
python -m venv venv
.
venv/Scripts/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
copy .env.example .env
```

4. Configure `.env` with your Telegram credentials, database settings, and any
   other required secrets.

---

## Telegram Channels Scraped

| Channel Username | Channel Title | Type |
|---|---|---|
| `lobelia4cosmetics` | Lobelia Pharmacy and Cosmetics | Cosmetics |
| `tikvahpharma` | Tikva PHARMA | Pharmaceutical |
| `Thequorachannel` | Doctors Online 🇪🇹 | Medical |
| `HakimApps_Guideline` | Hakimed: Medical Resources | Pharmaceutical |
| `HakimEthio` | Hakim | Medical |
| `CheMed123` | CheMed | Medical |

---

## Setup and Installation

### Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/medical-telegram-warehouse.git
cd medical-telegram-warehouse
```

---