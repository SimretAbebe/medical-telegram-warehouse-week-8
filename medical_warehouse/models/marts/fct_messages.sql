WITH messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

channels AS (
    SELECT * FROM {{ ref('dim_channels') }}
),

dates AS (
    SELECT * FROM {{ ref('dim_dates') }}
)

SELECT
    m.message_id,
    c.channel_key,
    d.date_key,
    m.message_text,
    m.message_length,
    m.views         AS view_count,
    m.forwards      AS forward_count,
    m.has_image,
    m.message_date,
    m.channel_name,
    m.scraped_at
FROM messages m
LEFT JOIN channels c ON m.channel_name = c.channel_name
LEFT JOIN dates d ON CAST(m.message_date AS DATE) = d.full_date