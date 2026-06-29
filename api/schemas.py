from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date


class TopProduct(BaseModel):
   
    term: str
   

    mention_count: int
  

    channels_mentioned_in: int
    

    class Config:
        from_attributes = True
      


class TopProductsResponse(BaseModel):
 
    total_messages_analyzed: int
    products: List[TopProduct]
    



class DailyActivity(BaseModel):
    
    date: str
    message_count: int
    total_views: int
    avg_views: float


class ChannelActivityResponse(BaseModel):
   
    channel_name: str
    channel_title: Optional[str] = None
    channel_type: str
    total_posts: int
    avg_views: float
    first_post_date: Optional[str] = None
    last_post_date: Optional[str] = None
    daily_activity: List[DailyActivity]



class MessageResult(BaseModel):
   
    message_id: int
    channel_name: str
    message_date: Optional[str] = None
    message_text: Optional[str] = None
    view_count: int
    has_image: bool


class MessageSearchResponse(BaseModel):
   
    query: str
    total_results: int
    messages: List[MessageResult]




class ChannelVisualStats(BaseModel):
    """Visual content stats for one channel"""
    channel_name: str
    channel_type: str
    total_messages: int
    messages_with_images: int
    image_percentage: float


class ImageCategoryStats(BaseModel):
    """Stats for one image category"""
    category: str
    count: int
    percentage: float


class VisualContentResponse(BaseModel):
  
    total_messages: int
    total_with_images: int
    overall_image_percentage: float
    channel_stats: List[ChannelVisualStats]
    category_breakdown: List[ImageCategoryStats]




class ErrorResponse(BaseModel):
 
    error: str
    detail: Optional[str] = None




class HealthResponse(BaseModel):
 
    status: str
    database: str
    total_messages: int
    total_channels: int