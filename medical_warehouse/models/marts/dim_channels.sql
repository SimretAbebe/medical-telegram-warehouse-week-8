WITH channel_stats AS (
    SELECT
        channel_name,
        channel_title,
        CASE
            WHEN LOWER(channel_name) LIKE '%pharma%'
              OR LOWER(channel_name) LIKE '%tikva%'
              OR LOWER(channel_name) LIKE '%hakim%'
              THEN 'Pharmaceutical'
            WHEN LOWER(channel_name) LIKE '%cosmet%'
              OR LOWER(channel_name) LIKE '%lobelia%'
              THEN 'Cosmetics'
            ELSE 'Medical'
        END                     AS channel_type,
        MIN(message_date)       AS first_post_date,
        MAX(message_date)       AS last_post_date,
        COUNT(*)                AS total_posts,
        ROUND(AVG(views), 2)    AS avg_views
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY channel_name, channel_title
)

SELECT
    ROW_NUMBER() OVER (ORDER BY channel_name)   AS channel_key,
    channel_name,
    channel_title,
    channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    avg_views
FROM channel_stats