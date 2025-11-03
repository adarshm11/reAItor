"""
Compilation Agent using Claude API
Synthesizes evaluation and arguments into final score and recommendation
"""

from anthropic import Anthropic
from models.schemas import Listing, UserPreferences, EvaluationReport, ArgumentReport, FinalReport
import json
import re
import os


class CompilationAgent:
    """Claude-powered agent for compiling final reports"""

    def __init__(self):
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def _get_system_prompt(self) -> str:
        """System prompt for the compilation agent"""
        return """You are a real estate decision advisor. Your job is to synthesize all available information about a property into a final recommendation.

You will receive:
1. Property details and listing information
2. Evaluation scores (preference match, crime, schools, walkability, affordability)
3. Pro arguments (reasons to buy)
4. Con arguments (reasons not to buy)
5. User preferences

Your task is to:
1. Calculate a final score (0-10) using weighted scoring:
   - Preference match: 40%
   - Additional factors (crime, schools, walkability, affordability): 30%
   - Pro/Con balance: 20%
   - Overall analysis: 10%

2. Write a concise executive summary (2-3 sentences) that captures:
   - Key strengths
   - Key concerns
   - Overall fit for the buyer

3. Make a recommendation:
   - "Strong Buy" (score 8-10): Excellent match, highly recommended
   - "Consider" (score 5-7): Good option worth viewing, some trade-offs
   - "Pass" (score 0-4): Significant issues or mismatches

Be objective, balanced, and data-driven. Consider both quantitative scores and qualitative arguments."""

    async def compile_report(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        arguments: ArgumentReport,
        preferences: UserPreferences
    ) -> FinalReport:
        """
        Compile final report with score and recommendation

        Args:
            listing: The property listing
            evaluation: Evaluation report
            arguments: Pro/con arguments
            preferences: User preferences

        Returns:
            FinalReport with final score, summary, and recommendation
        """
        # Create compilation prompt
        prompt = self._create_compilation_prompt(
            listing,
            evaluation,
            arguments,
            preferences
        )

        # Send to Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self._get_system_prompt(),
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        final_score, executive_summary, recommendation = self._parse_compilation_response(
            response,
            evaluation
        )

        # Create FinalReport
        return FinalReport(
            listing=listing,
            evaluation=evaluation,
            arguments=arguments,
            final_score=final_score,
            executive_summary=executive_summary,
            recommendation=recommendation
        )

    def _create_compilation_prompt(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        arguments: ArgumentReport,
        preferences: UserPreferences
    ) -> str:
        """Create prompt for compilation"""
        return f"""
Please compile a final report for this property:

PROPERTY:
Address: {listing.address}
Price: ${listing.price:,}
Type: {listing.property_type}
Specs: {listing.bedrooms} bed, {listing.bathrooms} bath, {listing.sqft:,} sqft

BUYER PREFERENCES:
Budget: ${preferences.price_min:,} - ${preferences.price_max:,}
Location: {preferences.location}
Size: {preferences.bedrooms_min}-{preferences.bedrooms_max} bedrooms
Must-Have: {', '.join(preferences.must_have_features or ['None'])}
Deal Breakers: {', '.join(preferences.deal_breakers or ['None'])}

EVALUATION SCORES:
Preference Match: {evaluation.preference_match_score}/10 (40% weight)
Crime Score: {evaluation.crime_score or 'N/A'}/10
School Score: {evaluation.school_score or 'N/A'}/10
Walkability: {evaluation.walkability_score or 'N/A'}/10
Affordability: {evaluation.affordability_score or 'N/A'}/10
Additional Factors Average: {self._calculate_additional_factors_score(evaluation)}/10 (30% weight)

Strengths: {', '.join(evaluation.strengths)}
Concerns: {', '.join(evaluation.concerns)}

PRO ARGUMENTS ({len(arguments.pro_arguments)} arguments):
{self._format_arguments(arguments.pro_arguments)}

CON ARGUMENTS ({len(arguments.con_arguments)} arguments):
{self._format_arguments(arguments.con_arguments)}

Pro/Con Balance (20% weight): {self._calculate_procon_balance(arguments)}/10

Please provide:
1. Final Score (0-10, weighted calculation)
2. Executive Summary (2-3 concise sentences)
3. Recommendation ("Strong Buy", "Consider", or "Pass")

Format as JSON:
{{
  "final_score": <number between 0-10>,
  "executive_summary": "<string>",
  "recommendation": "<Strong Buy|Consider|Pass>"
}}
"""

    def _calculate_additional_factors_score(self, evaluation: EvaluationReport) -> float:
        """Calculate average of additional factors"""
        scores = [
            evaluation.crime_score,
            evaluation.school_score,
            evaluation.walkability_score,
            evaluation.affordability_score
        ]
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 5.0

    def _calculate_procon_balance(self, arguments: ArgumentReport) -> float:
        """
        Calculate pro/con balance score
        More pros vs cons = higher score
        """
        pro_count = len(arguments.pro_arguments)
        con_count = len(arguments.con_arguments)

        if pro_count == 0 and con_count == 0:
            return 5.0

        # Simple ratio-based scoring
        # More pros relative to cons = higher score
        ratio = pro_count / (pro_count + con_count)
        return ratio * 10

    def _format_arguments(self, arguments: list) -> str:
        """Format arguments as bullet points"""
        if not arguments:
            return "- None"
        return "\n".join([f"- {arg}" for arg in arguments])

    def _parse_compilation_response(
        self,
        response,
        evaluation: EvaluationReport
    ) -> tuple:
        """
        Parse Claude API response into final score, summary, and recommendation

        Returns:
            Tuple of (final_score, executive_summary, recommendation)
        """
        try:
            # Extract message content
            message_content = ""
            for block in response.content:
                if block.type == "text":
                    message_content += block.text

            # Try to extract JSON
            json_match = re.search(r'\{[\s\S]*?\}', message_content)

            if json_match:
                result = json.loads(json_match.group())

                final_score = float(result.get('final_score', 5.0))
                final_score = max(0.0, min(10.0, final_score))  # Clamp to 0-10

                executive_summary = result.get('executive_summary', '')
                recommendation = result.get('recommendation', 'Consider')

                # Validate recommendation
                if recommendation not in ['Strong Buy', 'Consider', 'Pass']:
                    recommendation = self._score_to_recommendation(final_score)

                return final_score, executive_summary, recommendation

            # Fallback: calculate from scores
            return self._fallback_compilation(evaluation)

        except Exception as e:
            print(f"Error parsing compilation response: {e}")
            return self._fallback_compilation(evaluation)

    def _fallback_compilation(self, evaluation: EvaluationReport) -> tuple:
        """Fallback compilation when parsing fails"""
        # Calculate weighted score
        preference_weight = 0.4
        additional_weight = 0.3
        balance_weight = 0.2
        baseline_weight = 0.1

        final_score = (
            evaluation.preference_match_score * preference_weight +
            self._calculate_additional_factors_score(evaluation) * additional_weight +
            5.0 * balance_weight +  # Neutral pro/con balance
            5.0 * baseline_weight   # Baseline
        )

        final_score = max(0.0, min(10.0, final_score))

        # Generate summary
        executive_summary = f"Property scores {final_score:.1f}/10 overall. " \
                          f"Preference match: {evaluation.preference_match_score}/10. " \
                          f"Key strengths: {', '.join(evaluation.strengths[:2])}."

        # Determine recommendation
        recommendation = self._score_to_recommendation(final_score)

        return final_score, executive_summary, recommendation

    def _score_to_recommendation(self, score: float) -> str:
        """Convert numeric score to recommendation"""
        if score >= 8.0:
            return "Strong Buy"
        elif score >= 5.0:
            return "Consider"
        else:
            return "Pass"
