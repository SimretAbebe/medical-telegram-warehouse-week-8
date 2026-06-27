WITH detections AS (
    
    SELECT * FROM {{ source('raw', 'image_detections') }}
),

messages AS (
    
    SELECT * FROM {{ ref('fct_messages') }}
),

channels AS (
  
    SELECT * FROM {{ ref('dim_channels') }}
),

dates AS (
   
    SELECT * FROM {{ ref('dim_dates') }}
)

SELECT
    d.message_id,
    c.channel_key,
    dt.date_key,
    d.channel_name,
    d.class_name          AS detected_class,
    d.confidence          AS confidence_score,
    d.image_category,
    d.image_path,
    m.view_count,
    m.forward_count,
    m.message_text

FROM detections d


LEFT JOIN channels c
    ON d.channel_name = c.channel_name


LEFT JOIN messages m
    ON d.message_id = m.message_id

LEFT JOIN dates dt
    ON m.date_key = dt.date_key