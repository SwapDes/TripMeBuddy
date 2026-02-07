import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class DestinationResearchAgent:
    """Agent to research and recommend travel destinations based on preferences"""

    def __init__(self, gemini_api_key: str):
        """Initialize with Gemini API key"""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        logger.info("DestinationResearchAgent initialized")

    def research(self, preferences: Dict) -> Dict:
        """
        Research and recommend destinations based on preferences

        Args:
            preferences: Structured preferences from PreferencesAnalyzerAgent

        Returns:
            Dict with destination recommendations
        """
        try:
            logger.info("Researching destinations based on preferences")

            prompt = self._build_research_prompt(preferences)
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                logger.error("Empty response from Gemini")
                return {"destinations": [], "reasoning": "No recommendations available"}

            # Parse recommendations
            result = self._parse_research_response(response.text)

            # FIXED: Validate destination matches user preferences
            result = self._validate_destination_match(result, preferences)

            logger.info(f"Found {len(result.get('destinations', []))} destination recommendations")
            return result

        except Exception as e:
            logger.error(f"Destination research error: {e}")
            return {"destinations": [], "reasoning": f"Error: {str(e)}"}

    def _build_research_prompt(self, preferences: Dict) -> str:
        """Build research prompt based on preferences"""

        # Extract key information
        origin = preferences.get('origin', 'Not specified')
        destination_prefs = preferences.get('destination_preferences', [])
        destination_type = preferences.get('destination_type', 'mixed')
        budget = preferences.get('budget', {})
        duration = preferences.get('duration', {})
        dates = preferences.get('dates', {})
        interests = preferences.get('interests', [])
        travel_style = preferences.get('travel_style', 'comfort')

        # FIXED: Emphasize the requested destination if specified
        if destination_prefs:
            destination_instruction = f"""CRITICAL: The user specifically requested: {', '.join(destination_prefs)}
You MUST recommend the user's requested destination as your top choice unless it is:
1. Completely inaccessible from {origin} (no flights exist)
2. Has a travel ban or is unsafe due to conflict/natural disaster
3. Requires a visa that cannot be obtained

If the requested destination is viable, it MUST be your #1 recommendation.
Only suggest alternatives if the requested destination is truly impossible."""
        else:
            destination_instruction = "The user is open to destination suggestions."

        prompt = f"""You are an expert travel destination researcher. Based on the following preferences, recommend the top 3 most suitable destinations.

PREFERENCES:
- Origin: {origin}
- Preferred Destinations: {', '.join(destination_prefs) if destination_prefs else 'Open to suggestions'}
- Destination Type: {destination_type}
- Budget Level: {budget.get('budget_level', 'mid-range')}
- Total Budget: ${budget.get('total', 'Not specified')}
- Duration: {duration.get('days', 7)} days
- Departure Date: {dates.get('departure', 'Flexible')}
- Interests: {', '.join(interests) if interests else 'General travel'}
- Travel Style: {travel_style}

{destination_instruction}

Provide recommendations in JSON format (no markdown, no code blocks):
{{
  "destinations": [
    {{
      "city": "City name",
      "country": "Country",
      "airport_code": "IATA code (ONLY 3 LETTERS, no additional text)",
      "reasoning": "Why this destination fits the preferences",
      "match_score": 95,
      "highlights": ["Key attraction 1", "Key attraction 2", "Key attraction 3"],
      "best_for": ["interest1", "interest2"],
      "estimated_daily_cost": 120,
      "weather_info": "Weather during travel dates",
      "cultural_notes": "Important cultural considerations",
      "visa_requirements": "Visa requirements from origin"
    }}
  ],
  "overall_reasoning": "Summary of why these destinations were chosen",
  "alternative_suggestions": ["Alternative destination 1", "Alternative destination 2"]
}}

CRITICAL AIRPORT CODE RULES:
- airport_code MUST be EXACTLY 3 letters (e.g., "BKK", "MNL", "SIN")
- DO NOT include descriptive text like "MNL (Manila gateway)" or "BKK - Bangkok"
- DO NOT include any parentheses, dashes, or additional explanation
- Examples of CORRECT format: "BKK", "SIN", "MNL", "KBV", "LHR", "CDG"
- Examples of WRONG format: "MNL (Manila)", "BKK - Bangkok", "SIN gateway"

Important:
- Recommend 2-3 destinations maximum
- Consider flight accessibility from origin
- Match budget level and interests
- Consider seasonality and weather
- Provide practical information
- Rank by match_score (0-100)"""

        return prompt

    def _parse_research_response(self, response_text: str) -> Dict:
        """Parse research response into structured format"""
        try:
            # Clean response
            cleaned = response_text.strip()
            if "```json" in cleaned:
                cleaned = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
                if cleaned:
                    cleaned = cleaned.group(1)
            elif "```" in cleaned:
                cleaned = re.search(r'```\s*(.*?)\s*```', cleaned, re.DOTALL)
                if cleaned:
                    cleaned = cleaned.group(1)

            # Parse JSON
            result = json.loads(cleaned)

            # Validate structure
            if 'destinations' not in result:
                result = {'destinations': [], 'overall_reasoning': cleaned[:500]}

            # Clean airport codes from each destination
            for destination in result.get('destinations', []):
                if 'airport_code' in destination:
                    airport_code = destination['airport_code']

                    # Extract only the 3-letter IATA code
                    # Remove anything after space, parenthesis, or dash
                    cleaned_code = airport_code.strip()

                    # Extract first 3 letters if there's additional text
                    if '(' in cleaned_code:
                        cleaned_code = cleaned_code.split('(')[0].strip()
                    if '-' in cleaned_code:
                        cleaned_code = cleaned_code.split('-')[0].strip()
                    if ' ' in cleaned_code:
                        cleaned_code = cleaned_code.split(' ')[0].strip()

                    # Ensure it's exactly 3 uppercase letters
                    if len(cleaned_code) >= 3:
                        cleaned_code = cleaned_code[:3].upper()
                    else:
                        logger.warning(f"Invalid airport code '{airport_code}' - using first 3 chars")
                        cleaned_code = airport_code[:3].upper() if len(airport_code) >= 3 else airport_code.upper()

                    destination['airport_code'] = cleaned_code

                    if airport_code != cleaned_code:
                        logger.info(f"Cleaned airport code: '{airport_code}' → '{cleaned_code}'")

            # Sort by match_score
            if result.get('destinations'):
                result['destinations'] = sorted(
                    result['destinations'],
                    key=lambda x: x.get('match_score', 0),
                    reverse=True
                )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                'destinations': [],
                'overall_reasoning': response_text[:500],
                'parse_error': str(e)
            }
        except Exception as e:
            logger.error(f"Research response parsing error: {e}")
            return {
                'destinations': [],
                'overall_reasoning': 'Error parsing recommendations',
                'error': str(e)
            }

    def _validate_destination_match(self, result: Dict, preferences: Dict) -> Dict:
        """
        FIXED: Validate that recommended destinations match user's request
        Only allow fallback if requested destination is truly inaccessible
        """
        destination_prefs = preferences.get('destination_preferences', [])
        
        if not destination_prefs:
            # User didn't specify destination, any recommendation is fine
            return result

        requested_destination = destination_prefs[0].lower()
        destinations = result.get('destinations', [])

        if not destinations:
            logger.warning("No destinations returned by AI")
            return result

        top_destination = destinations[0]
        top_city = top_destination.get('city', '').lower()
        top_country = top_destination.get('country', '').lower()

        # Check if top recommendation matches user request
        matches = (
            requested_destination in top_city or 
            top_city in requested_destination or
            requested_destination in top_country or
            top_country in requested_destination
        )

        if not matches:
            # AI recommended different destination - this is a fallback
            logger.warning(
                f"AI recommended '{top_destination.get('city')}' but user requested '{destination_prefs[0]}'"
            )
            
            # Add warning to result
            result['fallback_detected'] = True
            result['requested_destination'] = destination_prefs[0]
            result['recommended_destination'] = top_destination.get('city')
            result['fallback_reason'] = top_destination.get('reasoning', 'Unknown reason')

            # Check if user's requested destination exists in the list at all
            user_destination_found = False
            for idx, dest in enumerate(destinations):
                dest_city = dest.get('city', '').lower()
                dest_country = dest.get('country', '').lower()
                if (requested_destination in dest_city or 
                    dest_city in requested_destination or
                    requested_destination in dest_country):
                    user_destination_found = True
                    # Move user's requested destination to top
                    logger.info(
                        f"Found user's requested destination '{dest.get('city')}' at position {idx}, moving to top"
                    )
                    destinations.insert(0, destinations.pop(idx))
                    result['destinations'] = destinations
                    result['fallback_corrected'] = True
                    break

            if not user_destination_found:
                logger.warning(
                    f"User's requested destination '{destination_prefs[0]}' not found in AI recommendations"
                )
                # Keep AI's recommendation but flag it clearly
                result['user_destination_not_found'] = True

        else:
            # AI correctly recommended user's destination
            logger.info(f"AI correctly recommended user's requested destination: {top_destination.get('city')}")
            result['fallback_detected'] = False

        return result

    def select_best_destination(self, research_result: Dict) -> Optional[Dict]:
        """Select the best destination from research results"""
        destinations = research_result.get('destinations', [])

        if not destinations:
            return None

        # Return highest match score destination (which should be user's request if specified)
        best = destinations[0]
        
        # Add fallback metadata if present
        if research_result.get('fallback_detected'):
            best['_fallback_detected'] = True
            best['_requested_destination'] = research_result.get('requested_destination')
            best['_fallback_reason'] = research_result.get('fallback_reason')
        
        logger.info(f"Selected destination: {best.get('city', 'Unknown')} (score: {best.get('match_score', 0)})")

        return best
