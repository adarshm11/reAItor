"""
Conversational Intake Agent
Uses Anthropic Claude to gather user preferences through natural conversation
"""

from anthropic import Anthropic
from models.schemas import UserPreferences, ChatMessage
from typing import List, Tuple, Optional
import os
import json
import re


class ConversationalAgent:
    """Agent for conversational preference gathering"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"  # Claude Sonnet 4.5

    def get_system_prompt(self) -> str:
        """Returns the system prompt for the conversational agent"""
        return """You are a friendly and knowledgeable real estate assistant helping users find their perfect home. Your goal is to gather their home preferences through natural conversation.

You should ask about:
1. Budget (price range)
2. Location preferences (city, neighborhood, proximity to work)
3. Property specifications (bedrooms, bathrooms, square footage)
4. Property type (house, condo, townhouse, apartment)
5. Must-have features (garage, pool, yard, etc.)
6. Deal-breakers (things they absolutely don't want)
7. Lifestyle priorities (walkability, schools, nightlife, quiet neighborhood, etc.)

Guidelines:
- Be conversational and friendly, not robotic
- Ask one or two questions at a time, don't overwhelm
- Listen to their answers and ask follow-up questions naturally
- If they're vague, ask clarifying questions
- Accept ranges and flexibility (e.g., "3-4 bedrooms is fine")
- Once you have enough information to start a meaningful search, let them know you're ready to find homes
- Keep responses concise (2-3 sentences max per message)

When you have gathered sufficient information (at minimum: location, price range, and bedrooms), end your message with the exact phrase: "[PREFERENCES_COMPLETE]"

Do NOT mention the [PREFERENCES_COMPLETE] marker to the user - it's just a signal for the system."""

    def extract_preferences_prompt(self, conversation_history: List[ChatMessage]) -> str:
        """Creates a prompt to extract structured preferences from conversation"""

        conversation_text = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in conversation_history
        ])

        return f"""Based on the following conversation, extract the user's home preferences into a structured JSON format.

Conversation:
{conversation_text}

Extract the following information (use null for any information not mentioned):
- price_min: minimum price (integer)
- price_max: maximum price (integer)
- bedrooms_min: minimum bedrooms (integer)
- bedrooms_max: maximum bedrooms (integer)
- bathrooms_min: minimum bathrooms (float)
- bathrooms_max: maximum bathrooms (float)
- sqft_min: minimum square feet (integer)
- sqft_max: maximum square feet (integer)
- location: city, zip code, or neighborhood (string)
- property_types: list of property types (array of strings: "house", "condo", "townhouse", "apartment")
- must_have_features: features they must have (array of strings)
- deal_breakers: things they don't want (array of strings)
- lifestyle_priorities: what matters most to them (array of strings)

Return ONLY a valid JSON object with these fields. Do not include any explanation or markdown formatting."""

    async def chat(
        self,
        user_message: str,
        conversation_history: List[ChatMessage]
    ) -> Tuple[str, bool]:
        """
        Process a user message and return assistant response

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation

        Returns:
            Tuple of (assistant_response, preferences_complete)
        """

        # Build message history for Claude
        messages = []
        for msg in conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.get_system_prompt(),
            messages=messages
        )

        # Extract response text
        assistant_message = response.content[0].text

        # Check if preferences are complete
        preferences_complete = "[PREFERENCES_COMPLETE]" in assistant_message

        # Remove the marker from the response
        assistant_message = assistant_message.replace("[PREFERENCES_COMPLETE]", "").strip()

        return assistant_message, preferences_complete

    async def extract_preferences(
        self,
        conversation_history: List[ChatMessage]
    ) -> Optional[UserPreferences]:
        """
        Extract structured preferences from conversation history

        Args:
            conversation_history: All messages in the conversation

        Returns:
            UserPreferences object or None if extraction fails
        """

        if not conversation_history:
            return None

        # Create extraction prompt
        extraction_prompt = self.extract_preferences_prompt(conversation_history)

        # Call Claude to extract preferences
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": extraction_prompt
            }]
        )

        # Parse JSON response
        try:
            response_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)

            preferences_dict = json.loads(response_text)

            # Convert to UserPreferences model
            preferences = UserPreferences(**preferences_dict)
            return preferences

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to extract preferences: {e}")
            print(f"Response was: {response_text}")
            return None

    def get_initial_message(self) -> str:
        """Returns the initial greeting message"""
        return "Hello! I'm here to help you find your perfect home. Let's start by understanding what you're looking for. What's your budget for your new home?"
