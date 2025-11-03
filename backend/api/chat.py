"""
Chat API endpoints for conversational preference gathering
"""

from fastapi import APIRouter, HTTPException
from models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSession,
    ChatMessage
)
from services.conversational_agent import ConversationalAgent
from typing import Dict
from datetime import datetime
import uuid

router = APIRouter()

# In-memory storage for chat sessions (replace with database later)
chat_sessions: Dict[str, ChatSession] = {}

# Initialize conversational agent
agent = ConversationalAgent()


@router.post("/start")
async def start_chat_session():
    """Start a new chat session"""
    session_id = str(uuid.uuid4())
    session = ChatSession(session_id=session_id)

    # Add initial assistant message
    initial_message = agent.get_initial_message()
    session.messages.append(
        ChatMessage(role="assistant", content=initial_message, timestamp=datetime.now())
    )

    chat_sessions[session_id] = session

    return {
        "session_id": session_id,
        "message": initial_message
    }


@router.post("/{session_id}/message")
async def send_message(session_id: str, request: ChatMessageRequest):
    """Send a message to the conversational agent"""

    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[session_id]

    # Add user message to history
    user_msg = ChatMessage(
        role="user",
        content=request.message,
        timestamp=datetime.now()
    )
    session.messages.append(user_msg)

    # Get response from conversational agent
    assistant_response, preferences_complete = await agent.chat(
        user_message=request.message,
        conversation_history=session.messages[:-1]  # Exclude the message we just added
    )

    # Add assistant response to history
    assistant_msg = ChatMessage(
        role="assistant",
        content=assistant_response,
        timestamp=datetime.now()
    )
    session.messages.append(assistant_msg)

    # If preferences are complete, extract them
    if preferences_complete:
        session.preferences_complete = True
        extracted_prefs = await agent.extract_preferences(session.messages)
        if extracted_prefs:
            session.preferences = extracted_prefs

    # Update session
    chat_sessions[session_id] = session

    response = ChatMessageResponse(
        response=assistant_response,
        preferences_complete=session.preferences_complete,
        current_preferences=session.preferences
    )

    return response


@router.get("/{session_id}/preferences")
async def get_preferences(session_id: str):
    """Get the current extracted preferences from a chat session"""

    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session = chat_sessions[session_id]

    return {
        "preferences": session.preferences,
        "preferences_complete": session.preferences_complete
    }
