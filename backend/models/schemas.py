"""
Pydantic models for data validation and serialization
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class UserPreferences(BaseModel):
    """User's home search preferences extracted from conversation"""
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None
    bathrooms_min: Optional[float] = None
    bathrooms_max: Optional[float] = None
    sqft_min: Optional[int] = None
    sqft_max: Optional[int] = None
    location: Optional[str] = None  # city, zip code, or neighborhood
    property_types: Optional[List[str]] = None  # ["house", "condo", "townhouse"]
    must_have_features: Optional[List[str]] = None  # ["garage", "pool", "yard"]
    deal_breakers: Optional[List[str]] = None  # ["no HOA", "no carpet"]
    lifestyle_priorities: Optional[List[str]] = None  # ["walkability", "schools", "nightlife"]


class Listing(BaseModel):
    """Real estate listing data"""
    id: str
    source: Literal["zillow", "redfin", "realtor"]
    url: str
    address: str
    city: str
    state: str
    zip_code: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: int
    property_type: str
    description: str
    images: List[str]
    listing_date: Optional[str] = None
    days_on_market: Optional[int] = None


class EvaluationReport(BaseModel):
    """Evaluation agent's comprehensive analysis"""
    listing_id: str
    preference_match_score: float = Field(ge=0, le=10)
    crime_score: Optional[float] = Field(default=None, ge=0, le=10)
    school_score: Optional[float] = Field(default=None, ge=0, le=10)
    walkability_score: Optional[float] = Field(default=None, ge=0, le=10)
    affordability_score: Optional[float] = Field(default=None, ge=0, le=10)
    similar_evaluations: List[str] = []  # Similar past evaluation IDs from RAG
    strengths: List[str]
    concerns: List[str]
    additional_notes: Optional[str] = None


class ArgumentReport(BaseModel):
    """Pro/Con argumentative agents' reports"""
    listing_id: str
    pro_arguments: List[str]
    con_arguments: List[str]


class FinalReport(BaseModel):
    """Final compiled report for a listing"""
    listing: Listing
    evaluation: EvaluationReport
    arguments: ArgumentReport
    final_score: float = Field(ge=0, le=10)
    executive_summary: str
    recommendation: Literal["Strong Buy", "Consider", "Pass"]


class ChatMessage(BaseModel):
    """Single chat message"""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Chat session data"""
    session_id: str
    messages: List[ChatMessage] = []
    preferences: Optional[UserPreferences] = None
    preferences_complete: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class ChatMessageRequest(BaseModel):
    """Request body for sending a chat message"""
    message: str


class ChatMessageResponse(BaseModel):
    """Response for a chat message"""
    response: str
    preferences_complete: bool
    current_preferences: Optional[UserPreferences] = None


class SearchStartRequest(BaseModel):
    """Request to start a search based on chat session"""
    chat_session_id: str


class SearchStatusResponse(BaseModel):
    """Status of the search process"""
    status: Literal["pending", "scraping", "evaluating", "complete", "error"]
    progress: float = Field(ge=0, le=100)
    message: str
    listings_found: int = 0
    listings_evaluated: int = 0


class FeedbackRequest(BaseModel):
    """User feedback on a listing"""
    listing_id: str
    action: Literal["like", "dislike"]
    session_id: str
