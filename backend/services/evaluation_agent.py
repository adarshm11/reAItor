"""
Evaluation Agent using Claude API
Analyzes property listings with RAG from past evaluations
"""

from anthropic import Anthropic
from models.schemas import Listing, UserPreferences, EvaluationReport
from services.chromadb_service import ChromaDBService
from services.external_data_service import ExternalDataService
from typing import List, Dict, Optional
import json
import os


class EvaluationAgent:
    """Claude-powered agent for evaluating property listings"""

    def __init__(self):
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

        # Initialize ChromaDB service
        self.chromadb = ChromaDBService()

        # Initialize External Data service
        self.external_data = ExternalDataService()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the evaluation agent"""
        return """You are a real estate evaluation expert. Your job is to analyze property listings and provide comprehensive evaluations.

You should consider:
1. How well the property matches the user's explicit preferences (budget, location, size, features)
2. Additional factors like crime rates, school quality, walkability, and local amenities
3. Past evaluations of similar properties to provide context
4. Both strengths and concerns about the property

Provide balanced, data-driven evaluations that help users make informed decisions.

When evaluating, assign scores from 0-10 for different factors:
- Preference Match Score: How well it matches stated preferences
- Crime Score: Safety of the neighborhood (10 = very safe)
- School Score: Quality of nearby schools (10 = excellent schools)
- Walkability Score: Pedestrian friendliness (10 = highly walkable)
- Affordability Score: Value for money (10 = excellent value)

Also provide:
- List of strengths (positive aspects)
- List of concerns (potential issues)
- Additional notes with context"""

    async def evaluate_listing(
        self,
        listing: Listing,
        preferences: UserPreferences
    ) -> EvaluationReport:
        """
        Evaluate a property listing

        Args:
            listing: The property listing to evaluate
            preferences: User's preferences

        Returns:
            Evaluation report
        """
        # Find similar past evaluations
        similar_evals = self.chromadb.find_similar_evaluations(
            listing,
            preferences.dict(),
            n_results=5
        )

        # Get external data (mock for now)
        external_data = self._get_external_data(listing)

        # Create evaluation prompt
        evaluation_prompt = self._create_evaluation_prompt(
            listing,
            preferences,
            similar_evals,
            external_data
        )

        # Send to Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self._get_system_prompt(),
            messages=[{
                "role": "user",
                "content": evaluation_prompt
            }]
        )

        # Parse response into EvaluationReport
        evaluation = self._parse_evaluation_response(response, listing.id)

        # Store evaluation in ChromaDB for future RAG
        self.chromadb.store_evaluation(listing, evaluation, preferences.dict())

        return evaluation

    def _get_external_data(self, listing: Listing) -> Dict:
        """
        Get external data about the property location
        Uses ExternalDataService to fetch real data from APIs
        Falls back to mock data if API keys are not configured
        """
        try:
            # Get comprehensive location data
            location_data = self.external_data.get_location_data(listing)

            # Format for evaluation
            formatted_data = self.external_data.format_for_evaluation(location_data)

            return formatted_data

        except Exception as e:
            print(f"Error fetching external data: {e}")
            # Fallback to basic mock data
            return {
                "crime_rate": "Unknown",
                "crime_index": 50,
                "crime_description": "Crime data unavailable",
                "nearby_schools": [],
                "walkability_score": 50,
                "walk_description": "Walkability data unavailable",
                "transit_score": 50,
                "transit_access": "Transit data unavailable",
                "local_amenities": "Amenity data unavailable"
            }

    def _create_evaluation_prompt(
        self,
        listing: Listing,
        preferences: UserPreferences,
        similar_evals: List[Dict],
        external_data: Dict
    ) -> str:
        """Create prompt for the evaluation agent"""

        # Helper function to format optional numeric fields
        def format_number(value, format_str=","):
            if value is None:
                return "Not specified"
            return f"{value:{format_str}}"

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

        prompt = f"""
Please evaluate this property listing:

PROPERTY DETAILS:
- Address: {listing.address}
- Price: ${listing.price:,}
- Bedrooms: {listing.bedrooms}
- Bathrooms: {listing.bathrooms}
- Square Feet: {listing.sqft:,}
- Property Type: {listing.property_type}
- Description: {listing.description}
- Days on Market: {listing.days_on_market or 'N/A'}

USER PREFERENCES:
- Budget: {budget_str}
- Location: {preferences.location or 'Not specified'}
- Bedrooms: {bedroom_str}
- Bathrooms: {bathroom_str}
- Must-Have Features: {', '.join(preferences.must_have_features or []) or 'None specified'}
- Deal Breakers: {', '.join(preferences.deal_breakers or []) or 'None specified'}
- Lifestyle Priorities: {', '.join(preferences.lifestyle_priorities or []) or 'None specified'}

NEIGHBORHOOD DATA:
{json.dumps(external_data, indent=2)}

SIMILAR PAST EVALUATIONS:
{self._format_similar_evaluations(similar_evals)}

Please provide a comprehensive evaluation with:
1. Preference Match Score (0-10)
2. Crime Score (0-10)
3. School Score (0-10)
4. Walkability Score (0-10)
5. Affordability Score (0-10)
6. List of Strengths (bullet points)
7. List of Concerns (bullet points)
8. Additional Notes

Format your response as JSON:
{{
  "preference_match_score": <number>,
  "crime_score": <number>,
  "school_score": <number>,
  "walkability_score": <number>,
  "affordability_score": <number>,
  "strengths": [<list of strings>],
  "concerns": [<list of strings>],
  "additional_notes": "<string>"
}}
"""
        return prompt.strip()

    def _format_similar_evaluations(self, similar_evals: List[Dict]) -> str:
        """Format similar evaluations for the prompt"""
        if not similar_evals:
            return "No similar evaluations found."

        formatted = []
        for i, eval in enumerate(similar_evals, 1):
            formatted.append(f"\n{i}. {eval['document'][:300]}...")

        return "\n".join(formatted)

    def _parse_evaluation_response(self, response, listing_id: str) -> EvaluationReport:
        """Parse Claude API response into EvaluationReport"""
        try:
            # Extract message content from Claude API response
            message_content = ""
            for block in response.content:
                if block.type == "text":
                    message_content += block.text

            # Try to extract JSON from response
            # Look for JSON block
            import re
            json_match = re.search(r'\{[\s\S]*\}', message_content)

            if json_match:
                eval_data = json.loads(json_match.group())
            else:
                # Fallback: create default evaluation
                eval_data = self._create_default_evaluation()

            # Create EvaluationReport
            return EvaluationReport(
                listing_id=listing_id,
                preference_match_score=float(eval_data.get('preference_match_score', 5.0)),
                crime_score=float(eval_data.get('crime_score', 5.0)),
                school_score=float(eval_data.get('school_score', 5.0)),
                walkability_score=float(eval_data.get('walkability_score', 5.0)),
                affordability_score=float(eval_data.get('affordability_score', 5.0)),
                similar_evaluations=[],
                strengths=eval_data.get('strengths', []),
                concerns=eval_data.get('concerns', []),
                additional_notes=eval_data.get('additional_notes', '')
            )

        except Exception as e:
            print(f"Error parsing evaluation response: {e}")
            # Return default evaluation
            return EvaluationReport(
                listing_id=listing_id,
                preference_match_score=5.0,
                crime_score=5.0,
                school_score=5.0,
                walkability_score=5.0,
                affordability_score=5.0,
                similar_evaluations=[],
                strengths=["Property matches basic requirements"],
                concerns=["Evaluation failed - manual review recommended"],
                additional_notes="Automated evaluation encountered an error"
            )

    def _create_default_evaluation(self) -> Dict:
        """Create a default evaluation when parsing fails"""
        return {
            "preference_match_score": 5.0,
            "crime_score": 5.0,
            "school_score": 5.0,
            "walkability_score": 5.0,
            "affordability_score": 5.0,
            "strengths": ["Property available for viewing"],
            "concerns": ["Requires further evaluation"],
            "additional_notes": "Standard evaluation"
        }
