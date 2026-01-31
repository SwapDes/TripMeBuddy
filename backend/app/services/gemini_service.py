import google.generativeai as genai
from typing import Dict, Optional, List
import logging
import json

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API for AI recommendations"""

    def __init__(self, api_key: str):
        """Initialize Gemini client"""
        logger.info("Initializing Gemini AI client")

        genai.configure(api_key=api_key)

        # Use Gemini 2.0 Flash (optimized for speed and quality)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

        logger.info("Gemini client initialized successfully")

    def generate_travel_recommendations(
            self,
            budget: Optional[float] = None,
            budget_min: Optional[float] = None,
            budget_max: Optional[float] = None,
            interests: List[str] = None,
            travel_style: Optional[str] = None,
            duration_days: Optional[int] = None,
            departure_date: Optional[str] = None,
            return_date: Optional[str] = None,
            origin: Optional[str] = None,
            preferred_destinations: Optional[List[str]] = None,
            additional_requirements: Optional[str] = None
    ) -> Dict:
        """
        Generate AI-powered travel recommendations using Gemini

        Args:
            budget: Total trip budget (if single value)
            budget_min: Minimum budget
            budget_max: Maximum budget
            interests: List of travel interests (e.g., ['beach', 'culture', 'adventure'])
            travel_style: Travel style (e.g., 'luxury', 'budget', 'backpacker')
            duration_days: Number of days for the trip
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD)
            origin: Origin city/airport (e.g., 'Delhi', 'DEL')
            preferred_destinations: List of preferred destinations
            additional_requirements: Any additional requirements or preferences

        Returns:
            Dict containing AI-generated recommendations
        """
        try:
            logger.info("Generating travel recommendations with Gemini AI")

            # Build the prompt based on provided preferences
            prompt = self._build_recommendation_prompt(
                budget=budget,
                budget_min=budget_min,
                budget_max=budget_max,
                interests=interests,
                travel_style=travel_style,
                duration_days=duration_days,
                departure_date=departure_date,
                return_date=return_date,
                origin=origin,
                preferred_destinations=preferred_destinations,
                additional_requirements=additional_requirements
            )

            logger.info(f"Prompt length: {len(prompt)} characters")

            # Generate response
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                return {
                    "success": False,
                    "error": "No response from AI model",
                    "recommendation": {}
                }

            logger.info("Gemini response received successfully")

            # Try to parse JSON response, fallback to text if parsing fails
            recommendation_data = self._parse_recommendation_response(response.text)

            return {
                "success": True,
                "recommendation": recommendation_data,
                "model": "gemini-2.0-flash-exp",
                "raw_response": response.text[:500]  # Store first 500 chars for debugging
            }

        except Exception as error:
            logger.error(f"Gemini API error: {str(error)}")
            return {
                "success": False,
                "error": str(error),
                "recommendation": {}
            }

    def _build_recommendation_prompt(
            self,
            budget: Optional[float],
            budget_min: Optional[float],
            budget_max: Optional[float],
            interests: Optional[List[str]],
            travel_style: Optional[str],
            duration_days: Optional[int],
            departure_date: Optional[str],
            return_date: Optional[str],
            origin: Optional[str],
            preferred_destinations: Optional[List[str]],
            additional_requirements: Optional[str]
    ) -> str:
        """Build a detailed prompt for Gemini based on user preferences"""

        prompt_parts = [
            "You are an expert travel advisor. Generate personalized travel destination recommendations based on the following preferences:",
            ""
        ]

        # Budget information
        if budget:
            prompt_parts.append(f"- Total Budget: ${budget:.2f}")
        elif budget_min and budget_max:
            prompt_parts.append(f"- Budget Range: ${budget_min:.2f} - ${budget_max:.2f}")
        elif budget_min:
            prompt_parts.append(f"- Minimum Budget: ${budget_min:.2f}")
        elif budget_max:
            prompt_parts.append(f"- Maximum Budget: ${budget_max:.2f}")

        # Travel details
        if origin:
            prompt_parts.append(f"- Starting Location: {origin}")

        if duration_days:
            prompt_parts.append(f"- Trip Duration: {duration_days} days")

        if departure_date:
            prompt_parts.append(f"- Departure Date: {departure_date}")

        if return_date:
            prompt_parts.append(f"- Return Date: {return_date}")

        # Preferences
        if interests and len(interests) > 0:
            prompt_parts.append(f"- Interests: {', '.join(interests)}")

        if travel_style:
            prompt_parts.append(f"- Travel Style: {travel_style}")

        if preferred_destinations and len(preferred_destinations) > 0:
            prompt_parts.append(f"- Preferred Destinations: {', '.join(preferred_destinations)}")

        if additional_requirements:
            prompt_parts.append(f"- Additional Requirements: {additional_requirements}")

        prompt_parts.extend([
            "",
            "Please provide recommendations in JSON format with the following structure:",
            "{",
            '  "destinations": [',
            '    {',
            '      "name": "Destination name",',
            '      "country": "Country",',
            '      "description": "Why this destination is recommended",',
            '      "best_for": ["interest1", "interest2"],',
            '      "estimated_daily_cost": 100,',
            '      "best_time_to_visit": "Season/months",',
            '      "highlights": ["attraction1", "attraction2"]',
            '    }',
            '  ],',
            '  "budget_breakdown": {',
            '    "flights": "Estimated flight cost",',
            '    "accommodation": "Estimated accommodation cost",',
            '    "daily_expenses": "Estimated daily expenses",',
            '    "activities": "Estimated activity costs"',
            '  },',
            '  "travel_tips": ["tip1", "tip2"],',
            '  "summary": "Overall recommendation summary"',
            "}"
        ])

        return "\n".join(prompt_parts)

    def _parse_recommendation_response(self, response_text: str) -> Dict:
        """Parse Gemini's response, attempting JSON parsing first"""
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
                return json.loads(json_text)

            # Try to find JSON object directly
            if response_text.strip().startswith("{"):
                return json.loads(response_text)

            # Fallback: return structured text response
            logger.warning("Could not parse JSON, returning text response")
            return {
                "destinations": [],
                "summary": response_text[:1000],  # First 1000 chars
                "formatted_response": response_text,
                "parse_error": "Could not extract structured JSON"
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "destinations": [],
                "summary": response_text[:500],
                "formatted_response": response_text,
                "parse_error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return {
                "destinations": [],
                "summary": "Error parsing AI response",
                "error": str(e)
            }
