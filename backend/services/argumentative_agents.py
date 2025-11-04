"""
Pro/Con Argumentative Agents using Claude API
Two agents that debate about each property listing
"""

from anthropic import Anthropic
from models.schemas import Listing, UserPreferences, EvaluationReport, ArgumentReport
from typing import List
import json
import re
import os


class ArgumentativeAgents:
    """Manages Pro and Con agents for property debate"""

    def __init__(self):
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def _get_pro_system_prompt(self) -> str:
        """System prompt for the Pro (advocate) agent"""
        return """You are an enthusiastic real estate advocate. Your job is to make the strongest possible case FOR purchasing a property.

You should:
- Highlight strengths and opportunities
- Emphasize how the property matches the buyer's preferences
- Find silver linings in potential concerns
- Point out value propositions and investment potential
- Be persuasive but honest - don't fabricate facts
- Focus on long-term benefits and lifestyle advantages

Structure your arguments as clear, compelling bullet points.
Each argument should be specific and reference actual property features or data."""

    def _get_con_system_prompt(self) -> str:
        """System prompt for the Con (critic) agent"""
        return """You are a critical real estate analyst. Your job is to identify potential issues and reasons NOT to purchase a property.

You should:
- Point out flaws, risks, and red flags
- Identify mismatches with buyer preferences
- Question value for money
- Highlight potential future problems
- Consider opportunity costs
- Be skeptical but fair - don't be unnecessarily negative
- Focus on practical concerns buyers should consider

Structure your arguments as clear, specific points.
Each argument should reference actual property features, data, or market considerations."""

    async def generate_arguments(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        preferences: UserPreferences
    ) -> ArgumentReport:
        """
        Generate pro and con arguments for a listing

        Args:
            listing: The property listing
            evaluation: The evaluation report
            preferences: User's preferences

        Returns:
            ArgumentReport with pro and con arguments
        """
        # Create context for both agents
        context = self._create_argument_context(listing, evaluation, preferences)

        # Get pro arguments
        pro_prompt = f"{context}\n\nProvide 3-5 compelling arguments FOR buying this property. Format as a JSON array of strings."
        pro_response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self._get_pro_system_prompt(),
            messages=[{
                "role": "user",
                "content": pro_prompt
            }]
        )
        pro_arguments = self._parse_arguments(pro_response)

        # Get con arguments
        con_prompt = f"{context}\n\nProvide 3-5 critical arguments AGAINST buying this property. Format as a JSON array of strings."
        con_response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self._get_con_system_prompt(),
            messages=[{
                "role": "user",
                "content": con_prompt
            }]
        )
        con_arguments = self._parse_arguments(con_response)

        return ArgumentReport(
            listing_id=listing.id,
            pro_arguments=pro_arguments,
            con_arguments=con_arguments
        )

    def _create_argument_context(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        preferences: UserPreferences
    ) -> str:
        """Create context for argumentation"""

        # Format budget range
        budget_str = "Not specified"
        if preferences.price_min is not None or preferences.price_max is not None:
            min_str = f"${preferences.price_min:,}" if preferences.price_min is not None else "No minimum"
            max_str = f"${preferences.price_max:,}" if preferences.price_max is not None else "No maximum"
            budget_str = f"{min_str} - {max_str}"

        # Format bedroom range
        bedroom_str = "Not specified"
        if preferences.bedrooms_min is not None or preferences.bedrooms_max is not None:
            min_bed = preferences.bedrooms_min if preferences.bedrooms_min is not None else "Any"
            max_bed = preferences.bedrooms_max if preferences.bedrooms_max is not None else "Any"
            bedroom_str = f"{min_bed}-{max_bed}"

        # Format bathroom minimum
        bathroom_str = f"{preferences.bathrooms_min}+" if preferences.bathrooms_min is not None else "Not specified"

        return f"""
PROPERTY LISTING:
Address: {listing.address}
Price: ${listing.price:,}
Type: {listing.property_type}
Specs: {listing.bedrooms} bed, {listing.bathrooms} bath, {listing.sqft:,} sqft
Description: {listing.description}
Days on Market: {listing.days_on_market or 'N/A'}

BUYER PREFERENCES:
Budget: {budget_str}
Location: {preferences.location or 'Not specified'}
Desired Size: {bedroom_str} bedrooms, {bathroom_str} bathrooms
Must-Have Features: {', '.join(preferences.must_have_features or ['None specified'])}
Deal Breakers: {', '.join(preferences.deal_breakers or ['None specified'])}
Lifestyle Priorities: {', '.join(preferences.lifestyle_priorities or ['None specified'])}

EVALUATION SCORES:
Preference Match: {evaluation.preference_match_score}/10
Crime Score: {evaluation.crime_score or 'N/A'}/10
School Score: {evaluation.school_score or 'N/A'}/10
Walkability: {evaluation.walkability_score or 'N/A'}/10
Affordability: {evaluation.affordability_score or 'N/A'}/10

IDENTIFIED STRENGTHS:
{self._format_list(evaluation.strengths)}

IDENTIFIED CONCERNS:
{self._format_list(evaluation.concerns)}

ADDITIONAL CONTEXT:
{evaluation.additional_notes or 'None'}
"""

    def _format_list(self, items: List[str]) -> str:
        """Format a list of items as bullet points"""
        if not items:
            return "- None"
        return "\n".join([f"- {item}" for item in items])

    def _parse_arguments(self, response) -> List[str]:
        """Parse arguments from Claude API response"""
        try:
            # Extract message content
            message_content = ""
            for block in response.content:
                if block.type == "text":
                    message_content += block.text

            # Try to extract JSON array
            json_match = re.search(r'\[[\s\S]*?\]', message_content)

            if json_match:
                arguments = json.loads(json_match.group())
                if isinstance(arguments, list):
                    return [str(arg) for arg in arguments]

            # Fallback: split by bullet points or newlines
            lines = message_content.split('\n')
            arguments = []
            for line in lines:
                line = line.strip()
                # Remove bullet points and numbering
                line = re.sub(r'^[-*•]\s*', '', line)
                line = re.sub(r'^\d+\.\s*', '', line)
                if line and len(line) > 10:  # Skip very short lines
                    arguments.append(line)

            if arguments:
                return arguments[:5]  # Max 5 arguments

            # Last resort fallback
            return [message_content[:500]]

        except Exception as e:
            print(f"Error parsing arguments: {e}")
            return ["Unable to generate structured arguments - please review manually"]

    def _create_default_arguments(self, is_pro: bool) -> List[str]:
        """Create default arguments when parsing fails"""
        if is_pro:
            return [
                "Property meets basic requirements",
                "Location is accessible",
                "Standard market pricing"
            ]
        else:
            return [
                "Requires thorough inspection",
                "Market conditions should be considered",
                "Additional due diligence recommended"
            ]
