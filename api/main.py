from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import re

from api.database import get_db, test_connection
from api.schemas import (
    TopProductsResponse, TopProduct,
    ChannelActivityResponse, DailyActivity,
    MessageSearchResponse, MessageResult,
    VisualContentResponse, ChannelVisualStats, ImageCategoryStats,
    HealthResponse, ErrorResponse
)



app = FastAPI(
    title="Ethiopian Medical Telegram API",
    

    description="""
    Ethiopian Medical Telegram Data Warehouse API

    This API exposes insights from Ethiopian medical Telegram channels.

    What you can do:
    - Search messages for specific products or keywords
    - Get top mentioned products across all channels
    - Analyze channel posting activity and trends
    - Get visual content statistics

    Data Sources:
    Data is collected from 6 Ethiopian medical Telegram channels
    and transformed using dbt into a clean star schema warehouse.
    """,

    version="1.0.0",
   
)



app.add_middleware(
    CORSMiddleware,
   

    allow_origins=["*"],
  

    allow_credentials=True,
    allow_methods=["*"],
    

    allow_headers=["*"],
)



@app.on_event("startup")
async def startup_event():
   
    print("Starting Ethiopian Medical Telegram API...")
    if test_connection():
        print("Database connection successful!")
    else:
        print("Database connection failed!")




@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check API health status"
)
def health_check(db: Session = Depends(get_db)):
  
    try:
        
        result = db.execute(text("""
            SELECT COUNT(*) FROM marts.fct_messages
        """))
        total_messages = result.scalar()
        

        
        result = db.execute(text("""
            SELECT COUNT(*) FROM marts.dim_channels
        """))
        total_channels = result.scalar()

        return HealthResponse(
            status="ok",
            database="connected",
            total_messages=total_messages,
            total_channels=total_channels
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
       



@app.get(
    "/api/reports/top-products",
    response_model=TopProductsResponse,
    tags=["Reports"],
    summary="Get top mentioned medical products"
)
def get_top_products(
    limit: int = Query(
        default=10,
        ge=1,
       
        le=50,
        
        description="Number of top products to return (1-50)"
    ),
    db: Session = Depends(get_db)
   
):
    
    try:
    
        query = text("""
            WITH words AS (
                SELECT
                    channel_name,
                    LOWER(
                        REGEXP_REPLACE(
                            UNNEST(STRING_TO_ARRAY(message_text, ' ')),
                            '[^a-zA-Z]', '', 'g'
                        )
                    ) AS word
                    -- UNNEST splits array into rows
                    -- STRING_TO_ARRAY splits text by space into array
                    -- REGEXP_REPLACE removes non-letter characters
                    -- LOWER converts to lowercase
                FROM marts.fct_messages
                WHERE message_text IS NOT NULL
                AND LENGTH(message_text) > 0
            ),
            filtered AS (
                SELECT word, channel_name
                FROM words
                WHERE
                    LENGTH(word) > 3
                    -- Skip very short words (and, the, is, etc)
                    AND word NOT IN (
                        'this', 'that', 'with', 'from', 'have',
                        'will', 'your', 'what', 'when', 'here',
                        'there', 'they', 'them', 'then', 'than',
                        'also', 'more', 'been', 'were', 'into',
                        'only', 'some', 'such', 'each', 'most',
                        'over', 'after', 'where', 'about', 'which',
                        'their', 'would', 'could', 'should', 'these',
                        'those', 'other', 'first', 'price', 'birr',
                        'https', 'http', 'www', 'com', 'call',
                        'contact', 'order', 'available', 'get',
                        'like', 'page', 'post', 'send', 'need'
                    )
                    
            )
            SELECT
                word                        AS term,
                COUNT(*)                    AS mention_count,
                COUNT(DISTINCT channel_name) AS channels_mentioned_in
            FROM filtered
            WHERE word != ''
            GROUP BY word
            ORDER BY mention_count DESC
            LIMIT :limit
        """)

        results = db.execute(query, {"limit": limit}).fetchall()
        # fetchall() gets all result rows

        # Count total messages
        total = db.execute(text(
            "SELECT COUNT(*) FROM marts.fct_messages"
        )).scalar()

        products = [
            TopProduct(
                term=row[0],
                mention_count=row[1],
                channels_mentioned_in=row[2]
            )
            for row in results
        ]
        # Listing comprehension creates TopProduct for each row

        return TopProductsResponse(
            total_messages_analyzed=total,
            products=products
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=ChannelActivityResponse,
    tags=["Channels"],
    summary="Get posting activity for a specific channel"
)
def get_channel_activity(
    channel_name: str,
    # channel_name comes from the URL path
    # Example: /api/channels/tikvahpharma/activity
    # → channel_name = "tikvahpharma"

    db: Session = Depends(get_db)
):
 
    try:
        # First check if channel exists
        channel = db.execute(text("""
            SELECT
                channel_name,
                channel_title,
                channel_type,
                total_posts,
                avg_views,
                first_post_date,
                last_post_date
            FROM marts.dim_channels
            WHERE LOWER(channel_name) = LOWER(:channel_name)
        """), {"channel_name": channel_name}).fetchone()
       

        if not channel:
            raise HTTPException(
                status_code=404,
                # 404 = Not Found
                detail=f"Channel '{channel_name}' not found. "
                       f"Check spelling or use /api/channels to see all channels."
            )

        # Get daily activity
        daily = db.execute(text("""
            SELECT
                d.full_date::TEXT         AS date,
                COUNT(*)                  AS message_count,
                SUM(f.view_count)         AS total_views,
                ROUND(AVG(f.view_count)::NUMERIC, 2) AS avg_views
            FROM marts.fct_messages f
            JOIN marts.dim_dates d ON f.date_key = d.date_key
            JOIN marts.dim_channels c ON f.channel_key = c.channel_key
            WHERE LOWER(c.channel_name) = LOWER(:channel_name)
            GROUP BY d.full_date
            ORDER BY d.full_date DESC
            LIMIT 30
            -- Last 30 days of activity
        """), {"channel_name": channel_name}).fetchall()

        return ChannelActivityResponse(
            channel_name=channel[0],
            channel_title=channel[1],
            channel_type=channel[2],
            total_posts=channel[3],
            avg_views=float(channel[4]) if channel[4] else 0.0,
            first_post_date=str(channel[5]) if channel[5] else None,
            last_post_date=str(channel[6]) if channel[6] else None,
            daily_activity=[
                DailyActivity(
                    date=str(row[0]),
                    message_count=row[1],
                    total_views=row[2] or 0,
                    avg_views=float(row[3]) if row[3] else 0.0
                )
                for row in daily
            ]
        )

    except HTTPException:
        raise
      

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get(
    "/api/search/messages",
    response_model=MessageSearchResponse,
    tags=["Search"],
    summary="Search messages by keyword"
)
def search_messages(
    query: str = Query(
        ...,
      
        min_length=2,
       
        description="Keyword to search for in message text"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results (1-100)"
    ),
    channel: Optional[str] = Query(
        default=None,
        description="Filter by channel name (optional)"
    ),
    db: Session = Depends(get_db)
):
   
    try:
        # Build the WHERE clause
        where_clause = """
            WHERE LOWER(f.message_text) LIKE LOWER(:search_term)
            -- LIKE = search for pattern
            -- % around term = word can appear anywhere in text
        """

        params = {"search_term": f"%{query}%", "limit": limit}
       

        if channel:
            where_clause += " AND LOWER(f.channel_name) = LOWER(:channel)"
            params["channel"] = channel

        # Search query
        results = db.execute(text(f"""
            SELECT
                f.message_id,
                f.channel_name,
                d.full_date::TEXT   AS message_date,
                f.message_text,
                f.view_count,
                f.has_image
            FROM marts.fct_messages f
            LEFT JOIN marts.dim_dates d ON f.date_key = d.date_key
            {where_clause}
            ORDER BY f.view_count DESC
            -- Show most viewed results first
            LIMIT :limit
        """), params).fetchall()

        # Count total matches
        count_result = db.execute(text(f"""
            SELECT COUNT(*)
            FROM marts.fct_messages f
            {where_clause}
        """), {k: v for k, v in params.items() if k != 'limit'}).scalar()

        return MessageSearchResponse(
            query=query,
            total_results=count_result,
            messages=[
                MessageResult(
                    message_id=row[0],
                    channel_name=row[1],
                    message_date=str(row[2]) if row[2] else None,
                    message_text=row[3],
                    view_count=row[4] or 0,
                    has_image=row[5] or False
                )
                for row in results
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get(
    "/api/reports/visual-content",
    response_model=VisualContentResponse,
    tags=["Reports"],
    summary="Get visual content statistics across channels"
)
def get_visual_content(db: Session = Depends(get_db)):
 
    try:
        # Overall stats
        overall = db.execute(text("""
            SELECT
                COUNT(*)                              AS total_messages,
                SUM(CASE WHEN has_image THEN 1 ELSE 0 END) AS with_images
            FROM marts.fct_messages
        """)).fetchone()

        total_messages = overall[0]
        total_with_images = overall[1] or 0
        overall_pct = round(
            (total_with_images / total_messages * 100) if total_messages > 0 else 0,
            2
        )

        # Per channel stats
        channel_stats = db.execute(text("""
            SELECT
                c.channel_name,
                c.channel_type,
                COUNT(*)                                   AS total_messages,
                SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END) AS with_images,
                ROUND(
                    SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END)::NUMERIC
                    / COUNT(*) * 100, 2
                ) AS image_pct
            FROM marts.fct_messages f
            JOIN marts.dim_channels c ON f.channel_key = c.channel_key
            GROUP BY c.channel_name, c.channel_type
            ORDER BY image_pct DESC
        """)).fetchall()

        # Image category breakdown from YOLO results
        try:
            category_stats = db.execute(text("""
                SELECT
                    image_category,
                    COUNT(DISTINCT message_id) AS count
                FROM marts.fct_image_detections
                GROUP BY image_category
                ORDER BY count DESC
            """)).fetchall()

            total_categorized = sum(row[1] for row in category_stats)
            categories = [
                ImageCategoryStats(
                    category=row[0],
                    count=row[1],
                    percentage=round(
                        row[1] / total_categorized * 100
                        if total_categorized > 0 else 0, 2
                    )
                )
                for row in category_stats
            ]
        except:
           
            categories = []

        return VisualContentResponse(
            total_messages=total_messages,
            total_with_images=total_with_images,
            overall_image_percentage=overall_pct,
            channel_stats=[
                ChannelVisualStats(
                    channel_name=row[0],
                    channel_type=row[1],
                    total_messages=row[2],
                    messages_with_images=row[3] or 0,
                    image_percentage=float(row[4]) if row[4] else 0.0
                )
                for row in channel_stats
            ],
            category_breakdown=categories
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get(
    "/api/channels",
    tags=["Channels"],
    summary="List all scraped channels"
)
def list_channels(db: Session = Depends(get_db)):
  
    try:
        results = db.execute(text("""
            SELECT
                channel_name,
                channel_title,
                channel_type,
                total_posts,
                avg_views,
                first_post_date,
                last_post_date
            FROM marts.dim_channels
            ORDER BY total_posts DESC
        """)).fetchall()

        return {
            "total_channels": len(results),
            "channels": [
                {
                    "channel_name": row[0],
                    "channel_title": row[1],
                    "channel_type": row[2],
                    "total_posts": row[3],
                    "avg_views": float(row[4]) if row[4] else 0.0,
                    "first_post_date": str(row[5]) if row[5] else None,
                    "last_post_date": str(row[6]) if row[6] else None,
                }
                for row in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/", tags=["System"])
def root():
  
    return {
        "message": "Ethiopian Medical Telegram API is running!",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }