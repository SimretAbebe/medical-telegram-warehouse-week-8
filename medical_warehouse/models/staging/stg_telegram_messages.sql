WITH source AS (
    SELECT * FROM {{ source('raw', 'telegram_messages') }}
),

cleaned AS (
    SELECT
        message_id,
        channel_name,
        channel_title,
        CAST(message_date AS TIMESTAMP)             AS message_date,
        TRIM(message_text)                          AS message_text,
        LENGTH(COALESCE(TRIM(message_text), ''))    AS message_length,
        has_media,
        CASE
            WHEN image_path IS NOT NULL
             AND image_path != '' THEN TRUE
            ELSE FALSE
        END                                         AS has_image,
        image_path,
        GREATEST(COALESCE(views, 0), 0)             AS views,
        GREATEST(COALESCE(forwards, 0), 0)          AS forwards,
        CAST(scraped_at AS TIMESTAMP)               AS scraped_at,
        source_file
    FROM source
    WHERE
        message_id IS NOT NULL
        AND channel_name IS NOT NULL
        AND CAST(message_date AS TIMESTAMP) <= NOW()
)

SELECT * FROM cleaned