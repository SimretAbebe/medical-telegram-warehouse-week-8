import os
import subprocess

# Windows needs this for Dagster compute log capture to work reliably.
os.environ.setdefault("PYTHONLEGACYWINDOWSSTDIO", "1")

from dagster import (
    op,
    job,
    schedule,
    RunRequest,
    ScheduleEvaluationContext,
    get_dagster_logger,
    OpExecutionContext,
    Definitions,
    multiprocess_executor,
    in_process_executor,
)

from dotenv import load_dotenv
load_dotenv()

@op
def scrape_telegram_data(context: OpExecutionContext):
    logger = get_dagster_logger()
  

    logger.info("Starting Telegram scraping")
    logger.info(f"Channels: {os.getenv('TELEGRAM_CHANNELS')}")

    try:
        
        import asyncio
        from src.scraper import main as scraper_main
        

        asyncio.run(scraper_main())
        

        logger.info("Telegram scraping completed successfully!")
        return "scraping_done"
        # Return a value so the next op knows this finished

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise
        


@op
def load_raw_to_postgres(context: OpExecutionContext, scraping_result: str):
   
    logger = get_dagster_logger()
    logger.info("Loading raw data to PostgreSQL")

    try:
        from src.load_to_postgres import main as loader_main
        # Import  loader script

        loader_main()
        # Run it

        logger.info("Raw data loaded to PostgreSQL successfully!")
        return "loading_done"

    except Exception as e:
        logger.error(f"Loading failed: {e}")
        raise

@op
def run_dbt_transformations(context: OpExecutionContext, loading_result: str):
    """
    This op:
    1. Runs dbt run — builds all models
    2. Runs dbt test — validates data quality

    """
    logger = get_dagster_logger()
    logger.info("Running dbt transformations")

    # Path to dbt project
    dbt_project_dir = os.path.join(
        os.path.dirname(__file__),
        "medical_warehouse"
    )
    env = os.environ.copy()
    try:
        logger.info("Running dbt run")
        result = subprocess.run(
            ["dbt", "run", "--profiles-dir", "."],
            
            cwd=dbt_project_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        if result.returncode != 0:
            
            raise Exception(f"dbt run failed: {result.stderr}")

        logger.info("dbt run completed successfully!")

      
        logger.info("Running dbt test...")
        test_result = subprocess.run(
            ["dbt", "test", "--profiles-dir", "."],
            cwd=dbt_project_dir,
            env=env,
            capture_output=True,
            text=True
        )

        if test_result.stdout:
            logger.info(test_result.stdout)

        if test_result.returncode != 0:
            raise Exception(f"dbt tests failed: {test_result.stderr}")

        logger.info("All dbt tests passed!")
        return "dbt_done"

    except Exception as e:
        logger.error(f"dbt transformation failed: {e}")
        raise




@op
def run_yolo_enrichment(context: OpExecutionContext, dbt_result: str):
  
    logger = get_dagster_logger()
    logger.info("Starting YOLO object detection.")

    try:
        from src.yolo_detect import main as yolo_main
       

        yolo_main()
        

        logger.info("YOLO enrichment completed successfully!")
        return "yolo_done"

    except Exception as e:
        logger.error(f"YOLO enrichment failed: {e}")
        raise



@op
def verify_pipeline(context: OpExecutionContext, yolo_result: str):
   
    logger = get_dagster_logger()
    logger.info("Verifying pipeline results...")

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()

    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "medical_warehouse"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

        with conn.cursor() as cur:

            # Check raw messages
            cur.execute("SELECT COUNT(*) FROM raw.telegram_messages")
            raw_count = cur.fetchone()[0]
            logger.info(f"Raw messages in database: {raw_count}")

            # Check fact table
            cur.execute("SELECT COUNT(*) FROM staging_marts.fct_messages")
            fact_count = cur.fetchone()[0]
            logger.info(f"Messages in fact table: {fact_count}")

            # Check channels
            cur.execute("SELECT COUNT(*) FROM staging_marts.dim_channels")
            channel_count = cur.fetchone()[0]
            logger.info(f"Channels in warehouse: {channel_count}")

            # Check YOLO results
            try:
                cur.execute("SELECT COUNT(*) FROM raw.image_detections")
                yolo_count = cur.fetchone()[0]
                logger.info(f"YOLO detections: {yolo_count}")
            except:
                logger.warning("YOLO table not found — skipping check")

        conn.close()

        
        logger.info("PIPELINE VERIFICATION COMPLETE!")
        logger.info(f"Raw messages:    {raw_count}")
        logger.info(f"Fact table rows: {fact_count}")
        logger.info(f"Channels:        {channel_count}")
        

        return "pipeline_complete"

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise



@job(
    name="medical_telegram_pipeline",
    # name = what this job is called in Dagster UI
    description="Full ETL pipeline for Ethiopian Medical Telegram Data Warehouse",
    executor_def=in_process_executor,
)
def medical_telegram_pipeline():
    
    scraping_result = scrape_telegram_data()

    loading_result = load_raw_to_postgres(scraping_result)

    dbt_result = run_dbt_transformations(loading_result)

    yolo_result = run_yolo_enrichment(dbt_result)

    verify_pipeline(yolo_result)


@schedule(
    cron_schedule="0 6 * * *",
    job=medical_telegram_pipeline,
    execution_timezone="Africa/Addis_Ababa",
)
def daily_pipeline_schedule(context: ScheduleEvaluationContext):
    return RunRequest(
        run_key=context.scheduled_execution_time.isoformat(),
        tags={
            "schedule": "daily",
            "timezone": "Africa/Addis_Ababa"
        }
    )



from dagster import Definitions

defs = Definitions(
    jobs=[medical_telegram_pipeline],
    # jobs = list of all jobs in this file

    schedules=[daily_pipeline_schedule],
    # schedules = list of all schedules
)