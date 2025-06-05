"""
FastAPI Style API Example for Corgi Recommender Service.

This module demonstrates how the API could be implemented using FastAPI
for automatic documentation generation. This is provided as an example
and is not currently used in the production service.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Query, Path, Body, HTTPException, Depends

# Create FastAPI app with documentation configuration
app = FastAPI(
    title="Corgi Recommender Service API",
    description="""
    API for the Corgi Recommender Service, a personalized recommendations system
    for Mastodon posts. The API handles user interactions, preferences, and generates
    personalized timelines.
    
    ## Key Features
    - **User Interaction Tracking**: Records favorites, bookmarks, and explicit feedback
    - **Personalized Recommendations**: Generates tailored post suggestions based on user activity
    - **Privacy Controls**: Provides user-configurable privacy settings
    - **Mastodon Compatibility**: Returns data in Mastodon-compatible format for easy integration
    - **Transparent Proxy**: Proxies requests to Mastodon instances with added recommendations
    """,
    version="1.0.0",
    docs_url="/api/v1/docs/fastapi",
    redoc_url="/api/v1/docs/redoc-fastapi",
    openapi_url="/api/v1/docs/openapi.json",
)


# Define models
class ActionType(str, Enum):
    """Types of user interactions with posts."""

    favorite = "favorite"
    bookmark = "bookmark"
    reblog = "reblog"
    more_like_this = "more_like_this"
    less_like_this = "less_like_this"


class TrackingLevel(str, Enum):
    """Privacy levels controlling data collection and usage."""

    full = "full"  # All interaction data is collected and used for personalization
    limited = "limited"  # Only aggregated data is stored, with limited personalization
    none = "none"  # No tracking of interactions, only basic functionality


class InteractionContext(BaseModel):
    """Additional context information for an interaction."""

    source: Optional[str] = Field(
        None, description="Source of the interaction (e.g., timeline_home)"
    )


class InteractionRequest(BaseModel):
    """Request model for logging a user interaction."""

    user_alias: Optional[str] = Field(
        None, description="Pseudonymized identifier for the user"
    )
    user_id: Optional[str] = Field(
        None, description="Alternative direct user identifier"
    )
    post_id: str = Field(..., description="Unique identifier for the post")
    action_type: ActionType = Field(..., description="The type of interaction")
    context: Optional[InteractionContext] = Field(
        None, description="Additional context about the interaction"
    )

    class Config:
        schema_extra = {
            "example": {
                "user_alias": "user_12345",
                "post_id": "post_67890",
                "action_type": "favorite",
                "context": {"source": "timeline_home"},
            }
        }


class InteractionCounts(BaseModel):
    """Count of different interaction types for a post."""

    favorites: int = Field(0, description="Number of favorites")
    reblogs: int = Field(0, description="Number of reblogs")
    replies: int = Field(0, description="Number of replies")
    bookmarks: int = Field(0, description="Number of bookmarks")


class Account(BaseModel):
    """User account information in Mastodon format."""

    id: str = Field(..., description="Unique identifier for the account")
    username: str = Field(..., description="Username of the account")
    display_name: str = Field(..., description="Display name of the account")
    followers_count: Optional[int] = Field(None, description="Number of followers")
    following_count: Optional[int] = Field(
        None, description="Number of accounts following"
    )
    statuses_count: Optional[int] = Field(None, description="Number of posted statuses")
    url: Optional[str] = Field(None, description="URL to the account's profile")


class MastodonPost(BaseModel):
    """Post in Mastodon-compatible format."""

    id: str = Field(..., description="Unique identifier for the post")
    content: str = Field(..., description="HTML content of the post")
    created_at: datetime = Field(..., description="Creation timestamp")
    language: Optional[str] = Field("en", description="ISO language code (e.g., 'en')")
    account: Account
    replies_count: Optional[int] = Field(
        0, description="Number of replies to this post"
    )
    reblogs_count: Optional[int] = Field(
        0, description="Number of reblogs of this post"
    )
    favourites_count: Optional[int] = Field(
        0, description="Number of favorites for this post"
    )
    url: Optional[str] = Field(None, description="URL to the post")
    sensitive: Optional[bool] = Field(
        False, description="Whether the post contains sensitive content"
    )
    spoiler_text: Optional[str] = Field("", description="Content warning text")
    visibility: Optional[str] = Field(
        "public", description="Visibility level of the post"
    )
    ranking_score: Optional[float] = Field(
        None, description="Recommendation ranking score (0.0 to 1.0)"
    )
    recommendation_reason: Optional[str] = Field(
        None, description="Human-readable reason for recommendation"
    )
    is_recommendation: Optional[bool] = Field(
        False, description="Whether this post was added as a recommendation"
    )
    is_real_mastodon_post: Optional[bool] = Field(
        True, description="Whether this is a real Mastodon post (vs. synthetic)"
    )
    is_synthetic: Optional[bool] = Field(
        False, description="Whether this is a synthetic post"
    )


class TimelineResponse(BaseModel):
    """Response model for timeline endpoints."""

    timeline: List[MastodonPost]
    injected_count: Optional[int] = Field(
        None, description="Number of recommendations injected"
    )


class PrivacySettings(BaseModel):
    """User privacy settings."""

    user_id: str = Field(..., description="User identifier")
    tracking_level: TrackingLevel = Field(
        ..., description="Privacy level controlling data collection and usage"
    )
    status: Optional[str] = Field("ok", description="Status of the operation")


# Define API routes
@app.post(
    "/api/v1/interactions",
    summary="Log a user interaction with a post",
    description="Records user actions like favorites, bookmarks, or post feedback. This data is used to improve future recommendations.",
)
async def log_interaction(interaction: InteractionRequest):
    """
    Log a user interaction with a post.

    - **user_alias**: Pseudonymized identifier for the user
    - **user_id**: Alternative direct user identifier (if user_alias not provided)
    - **post_id**: The post being interacted with
    - **action_type**: Type of interaction (favorite, bookmark, etc.)
    - **context**: Additional context about the interaction
    """
    # Implementation would go here
    return {"status": "ok", "interaction_id": "interaction_12345"}


@app.get(
    "/api/v1/interactions/{post_id}",
    summary="Get interactions for a specific post",
    description="Retrieves all recorded interactions for a single post",
)
async def get_post_interactions(
    post_id: str = Path(
        ..., description="The ID of the post to retrieve interactions for"
    )
):
    """
    Get all interactions for a specific post.

    Returns a breakdown of interactions by type and counts.
    """
    # Implementation would go here
    return {
        "post_id": post_id,
        "interaction_counts": {
            "favorites": 42,
            "reblogs": 7,
            "replies": 12,
            "bookmarks": 5,
        },
        "interactions": [
            {"action_type": "favorite", "count": 42},
            {"action_type": "reblog", "count": 7},
            {"action_type": "bookmark", "count": 5},
        ],
    }


@app.get(
    "/api/v1/timelines/home",
    summary="Get user's home timeline",
    description="""
         Returns the user's home timeline, similar to a Mastodon home timeline.
         For real users, the request is proxied to their Mastodon instance.
         For test/synthetic users, returns mock data.
         """,
)
async def get_home_timeline(
    user_id: Optional[str] = Query(
        None, description="The user ID to get timeline for (for testing/validation)"
    ),
    limit: int = Query(20, description="Maximum number of posts to return"),
):
    """
    Get a user's home timeline.

    For authenticated users, returns their Mastodon home timeline.
    For test/synthetic users, returns mock timeline data.
    """
    # Implementation would go here
    return {"timeline": []}  # Would return actual posts


@app.get(
    "/api/v1/timelines/home/augmented",
    summary="Get augmented home timeline with recommendations",
    description="""
         Returns the user's home timeline with personalized recommendations injected.
         Can blend real Mastodon posts with recommended posts based on user preferences.
         """,
)
async def get_augmented_timeline(
    user_id: Optional[str] = Query(
        None, description="The user ID to get timeline for (for testing/validation)"
    ),
    limit: int = Query(20, description="Maximum number of posts to return"),
    inject_recommendations: bool = Query(
        False,
        description="Whether to inject personalized recommendations into the timeline",
    ),
):
    """
    Get a user's augmented timeline with recommendations.

    Blends the user's regular home timeline with personalized post recommendations.
    Set inject_recommendations=true to include recommended posts.
    """
    # Implementation would go here
    return {
        "timeline": [],  # Would return actual posts
        "injected_count": 5 if inject_recommendations else 0,
    }


@app.get(
    "/api/v1/privacy",
    summary="Get user privacy settings",
    description="Retrieves the current privacy settings for a user",
)
async def get_privacy_settings(
    user_id: str = Query(..., description="The user ID to get privacy settings for")
):
    """
    Get privacy settings for a user.

    Returns the current tracking level and data collection settings.
    """
    # Implementation would go here
    return {"user_id": user_id, "tracking_level": "limited"}


@app.post(
    "/api/v1/privacy",
    summary="Update user privacy settings",
    description="""
          Updates a user's privacy settings, controlling how much data is collected
          and how it's used for recommendations.
          """,
)
async def update_privacy_settings(settings: PrivacySettings):
    """
    Update privacy settings for a user.

    - **user_id**: The user to update settings for
    - **tracking_level**: Privacy level (full, limited, none)
    """
    # Implementation would go here
    return {
        "user_id": settings.user_id,
        "tracking_level": settings.tracking_level,
        "status": "ok",
    }


if __name__ == "__main__":
    # Run the FastAPI app directly for development
    uvicorn.run(app, host="0.0.0.0", port=5001)
