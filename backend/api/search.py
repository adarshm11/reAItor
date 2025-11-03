"""
Search API endpoints for listing search and results
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import (
    SearchStartRequest,
    SearchStatusResponse,
    FinalReport,
    FeedbackRequest,
    Listing
)
from services.scraper_orchestrator import ScraperOrchestrator
from services.evaluation_agent import EvaluationAgent
from services.argumentative_agents import ArgumentativeAgents
from services.compilation_agent import CompilationAgent
from services.recommendation_service import RecommendationService
from api.chat import chat_sessions  # Import chat sessions
from typing import Dict, List
import uuid
import asyncio

router = APIRouter()

# In-memory storage for search sessions (replace with database later)
search_sessions: Dict[str, dict] = {}

# In-memory storage for seen listings per session
seen_listings: Dict[str, List[str]] = {}

# Initialize services
orchestrator = ScraperOrchestrator()
evaluation_agent = EvaluationAgent()
argumentative_agents = ArgumentativeAgents()
compilation_agent = CompilationAgent()
recommendation_service = RecommendationService()


async def run_search_pipeline(session_id: str, chat_session_id: str):
    """Background task to run the search pipeline"""
    try:
        # Get preferences from chat session
        if chat_session_id not in chat_sessions:
            search_sessions[session_id]["status"] = "error"
            search_sessions[session_id]["message"] = "Chat session not found"
            return

        chat_session = chat_sessions[chat_session_id]
        preferences = chat_session.preferences

        if not preferences:
            search_sessions[session_id]["status"] = "error"
            search_sessions[session_id]["message"] = "No preferences found"
            return

        # Update status: scraping
        search_sessions[session_id]["status"] = "scraping"
        search_sessions[session_id]["message"] = "Searching real estate platforms..."
        search_sessions[session_id]["progress"] = 20.0

        # Run scrapers
        listings = await orchestrator.search_all_platforms(preferences)
        print(f"Search {session_id}: Found {len(listings)} listings from scrapers")

        # Update status: evaluating
        search_sessions[session_id]["status"] = "evaluating"
        search_sessions[session_id]["message"] = "Evaluating listings..."
        search_sessions[session_id]["progress"] = 50.0

        # Evaluate each listing
        evaluated_listings = []
        for i, listing in enumerate(listings):
            try:
                evaluation = await evaluation_agent.evaluate_listing(listing, preferences)
                evaluated_listings.append({
                    "listing": listing,
                    "evaluation": evaluation
                })

                # Update progress (50-70%)
                progress = 50.0 + (20.0 * (i + 1) / len(listings))
                search_sessions[session_id]["progress"] = progress

                print(f"Evaluated listing {i+1}/{len(listings)}: {listing.address}")
            except Exception as e:
                print(f"Error evaluating listing {listing.id}: {e}")
                # Continue with other listings

        # Update status: arguing
        search_sessions[session_id]["status"] = "evaluating"
        search_sessions[session_id]["message"] = "Generating pro/con arguments..."
        search_sessions[session_id]["progress"] = 70.0

        # Generate pro/con arguments for each listing
        argued_listings = []
        for i, eval_listing in enumerate(evaluated_listings):
            try:
                arguments = await argumentative_agents.generate_arguments(
                    eval_listing["listing"],
                    eval_listing["evaluation"],
                    preferences
                )
                argued_listings.append({
                    "listing": eval_listing["listing"],
                    "evaluation": eval_listing["evaluation"],
                    "arguments": arguments
                })

                # Update progress (70-85%)
                progress = 70.0 + (15.0 * (i + 1) / len(evaluated_listings))
                search_sessions[session_id]["progress"] = progress

                print(f"Generated arguments {i+1}/{len(evaluated_listings)}: {eval_listing['listing'].address}")
            except Exception as e:
                print(f"Error generating arguments for {eval_listing['listing'].id}: {e}")
                # Continue with other listings

        # Update status: compiling
        search_sessions[session_id]["status"] = "evaluating"
        search_sessions[session_id]["message"] = "Compiling final reports..."
        search_sessions[session_id]["progress"] = 85.0

        # Compile final reports
        final_reports = []
        for i, argued_listing in enumerate(argued_listings):
            try:
                final_report = await compilation_agent.compile_report(
                    argued_listing["listing"],
                    argued_listing["evaluation"],
                    argued_listing["arguments"],
                    preferences
                )
                final_reports.append(final_report)

                # Update progress (85-95%)
                progress = 85.0 + (10.0 * (i + 1) / len(argued_listings))
                search_sessions[session_id]["progress"] = progress

                print(f"Compiled report {i+1}/{len(argued_listings)}: {argued_listing['listing'].address} - Score: {final_report.final_score:.1f}/10")
            except Exception as e:
                print(f"Error compiling report for {argued_listing['listing'].id}: {e}")
                # Continue with other listings

        # Sort by final score (highest first)
        final_reports.sort(key=lambda x: x.final_score, reverse=True)

        # Update status: complete
        search_sessions[session_id]["status"] = "complete"
        search_sessions[session_id]["message"] = "Analysis complete"
        search_sessions[session_id]["progress"] = 100.0
        search_sessions[session_id]["listings"] = listings
        search_sessions[session_id]["evaluated_listings"] = evaluated_listings
        search_sessions[session_id]["argued_listings"] = argued_listings
        search_sessions[session_id]["final_reports"] = final_reports

        print(f"Search {session_id}: Completed {len(final_reports)} final reports (sorted by score)")

    except Exception as e:
        print(f"Search pipeline error: {e}")
        search_sessions[session_id]["status"] = "error"
        search_sessions[session_id]["message"] = str(e)


@router.post("/start")
async def start_search(request: SearchStartRequest, background_tasks: BackgroundTasks):
    """Start a search based on chat session preferences"""

    search_session_id = str(uuid.uuid4())

    # Initialize search session
    search_sessions[search_session_id] = {
        "status": "pending",
        "chat_session_id": request.chat_session_id,
        "message": "Initializing search...",
        "progress": 0.0,
        "listings": []
    }

    # Start search pipeline in background
    background_tasks.add_task(run_search_pipeline, search_session_id, request.chat_session_id)

    return {
        "search_session_id": search_session_id,
        "status": "pending"
    }


@router.get("/{session_id}/status")
async def get_search_status(session_id: str):
    """Get the status of a search session"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    return SearchStatusResponse(
        status=session.get("status", "pending"),
        progress=session.get("progress", 0.0),
        message=session.get("message", "Processing..."),
        listings_found=len(session.get("listings", [])),
        listings_evaluated=len(session.get("evaluated_listings", []))
    )


@router.get("/{session_id}/results")
async def get_search_results(session_id: str) -> List[Listing]:
    """Get the final results from a search session"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(
            status_code=400,
            detail="Search is not complete yet"
        )

    # Return listings (for now, before we have full FinalReport with evaluation/arguments)
    return session.get("listings", [])


@router.get("/{session_id}/evaluated-results")
async def get_evaluated_results(session_id: str):
    """Get the evaluated results from a search session"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(
            status_code=400,
            detail="Search is not complete yet"
        )

    # Return evaluated listings with evaluations
    return session.get("evaluated_listings", [])


@router.get("/{session_id}/final-results")
async def get_final_results(session_id: str):
    """Get the final results with evaluations, arguments, and final scores"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(
            status_code=400,
            detail="Search is not complete yet"
        )

    # Return final reports sorted by score (highest first)
    return session.get("final_reports", [])


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback (like/dislike) on a listing"""

    # Find the listing and final report from the session
    session_id = request.session_id

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Search not complete yet")

    # Find the listing and final report
    final_reports = session.get("final_reports", [])
    listing = None
    final_report = None

    for report in final_reports:
        if report.listing.id == request.listing_id:
            listing = report.listing
            final_report = report
            break

    if not listing or not final_report:
        raise HTTPException(status_code=404, detail="Listing not found in this session")

    # Record feedback in recommendation service
    recommendation_service.record_feedback(request, listing, final_report)

    # Track that this listing has been seen
    if session_id not in seen_listings:
        seen_listings[session_id] = []

    if request.listing_id not in seen_listings[session_id]:
        seen_listings[session_id].append(request.listing_id)

    # Get learning insights
    insights = recommendation_service.get_learning_insights(session_id)

    return {
        "status": "success",
        "message": "Feedback recorded and preferences updated",
        "learning_insights": insights
    }


@router.get("/{session_id}/next")
async def get_next_listing(session_id: str):
    """Get the next best listing based on learned preferences"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Search not complete yet")

    # Get all final reports
    final_reports = session.get("final_reports", [])

    if not final_reports:
        raise HTTPException(status_code=404, detail="No listings available")

    # Get seen listings for this session
    seen = seen_listings.get(session_id, [])

    # Get next best listing using recommendation service
    next_listing = recommendation_service.get_next_listing(
        session_id=session_id,
        available_listings=final_reports,
        seen_listing_ids=seen
    )

    if not next_listing:
        return {
            "message": "No more unseen listings available",
            "listing": None,
            "all_seen": True
        }

    return {
        "message": "Next recommended listing",
        "listing": next_listing,
        "all_seen": False
    }


@router.get("/{session_id}/insights")
async def get_learning_insights(session_id: str):
    """Get insights about learned user preferences"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    # Get learning insights from recommendation service
    insights = recommendation_service.get_learning_insights(session_id)

    return {
        "session_id": session_id,
        "insights": insights
    }


@router.get("/{session_id}/ranked-results")
async def get_ranked_results(session_id: str):
    """Get all results re-ranked based on learned preferences"""

    if session_id not in search_sessions:
        raise HTTPException(status_code=404, detail="Search session not found")

    session = search_sessions[session_id]

    if session.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Search not complete yet")

    # Get all final reports
    final_reports = session.get("final_reports", [])

    if not final_reports:
        return []

    # Re-rank using recommendation service
    ranked_reports = recommendation_service.get_ranked_listings(session_id, final_reports)

    return ranked_reports
