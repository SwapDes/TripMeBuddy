import google.generativeai as genai
from typing import Dict, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class PreferencesAnalyzerAgent:
    """Agent to analyze and extract structured travel preferences from natural language"""

    def __init__(self, gemini_api_key: str, currency_service=None):
        """
        Initialize with Gemini API key and optional currency service

        Args:
            gemini_api_key: Google Gemini API key
            currency_service: CurrencyService instance for currency inference
        """
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        self.currency_service = currency_service
        logger.info("PreferencesAnalyzerAgent initialized")

    async def analyze(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """
        Extract structured preferences from natural language request

        Args:
            user_request: Natural language trip description
            context: Optional additional context

        Returns:
            Dict with structured preferences including assumptions
        """
        try:
            logger.info("Analyzing user preferences from natural language input")

            # Import DateParser here to avoid circular imports
            from app.utils.date_parser import DateParser

            prompt = self._build_analysis_prompt(user_request, context)
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                logger.error("Empty response from Gemini")
                return await self._get_default_preferences(user_request)

            # Parse the structured response
            preferences = self._parse_preferences(response.text)

            # Post-process: Enhanced date parsing
            duration_days = preferences.get('duration', {}).get('days', 7)
            gemini_dates = preferences.get('dates', {})

            parsed_dates = DateParser.parse_travel_dates(
                user_request=user_request,
                gemini_dates=gemini_dates,
                duration_days=duration_days
            )

            preferences['dates']['departure'] = parsed_dates['departure']
            preferences['dates']['return'] = parsed_dates['return']

            # Track date assumption
            if '_assumptions' not in preferences:
                preferences['_assumptions'] = []
            preferences['_assumptions'].append(parsed_dates['assumption'])

            # Post-process: Enhanced currency inference
            if self.currency_service:
                budget = preferences.get('budget', {})
                origin = preferences.get('origin')

                # If currency not clearly specified, infer it
                if not budget.get('currency') or budget.get('currency') == 'USD':
                    # Try to infer from request text
                    currency, assumption = await self.currency_service.infer_currency(
                        budget_text=user_request,
                        origin_code=self._get_origin_code(origin)
                    )

                    preferences['budget']['currency'] = currency
                    preferences['_assumptions'].append(assumption)

            logger.info(f"Preferences extracted: {preferences.get('destination_type', 'unknown')}")
            return preferences

        except Exception as e:
            logger.error(f"Preferences analysis error: {e}", exc_info=True)
            return await self._get_default_preferences(user_request)

    def _build_analysis_prompt(self, user_request: str, context: Optional[Dict]) -> str:
        """Build enhanced prompt for preference extraction"""

        prompt = f"""You are a travel planning assistant. Analyze the following travel request and extract structured information.

User Request: "{user_request}"

Extract and return ONLY a JSON object with the following structure (no markdown, no code blocks):
{{
  "origin": "Origin city or airport code (e.g., Delhi, DEL, Mumbai)",
  "destination_preferences": ["List of preferred destinations or regions"],
  "destination_type": "beach/mountain/city/cultural/adventure/mixed",
  "budget": {{
    "total": 0,
    "currency": "USD/INR/EUR/etc or null if not specified",
    "budget_level": "budget/mid-range/luxury"
  }},
  "duration": {{
    "days": 0,
    "nights": 0
  }},
  "dates": {{
    "departure": "YYYY-MM-DD or 'March 2026' or null",
    "return": "YYYY-MM-DD or null",
    "flexible": true
  }},
  "travelers": {{
    "adults": 1,
    "children": 0,
    "infants": 0
  }},
  "interests": ["beach", "culture", "food", "adventure", "nightlife", "shopping", "nature", "history"],
  "travel_style": "luxury/comfort/budget/backpacker/family/solo/couple/group",
  "accommodation_preferences": ["hotel", "resort", "hostel", "airbnb", "guesthouse"],
  "special_requirements": ["Any dietary, accessibility, or other requirements"],
  "priorities": ["cost", "comfort", "experience", "authenticity"]
}}

CRITICAL INSTRUCTIONS FOR DATE EXTRACTION:
- If user says "March 2026" or "in March 2026", set departure to "March 2026" (not a specific day)
- If user says "March 15, 2026", set departure to "2026-03-15"
- If user says "next month", set departure to "next month"
- DO NOT default to current date - use null if no date mentioned
- Preserve the user's phrasing for dates - we'll parse them later

CURRENCY EXTRACTION:
- If user says "2000 USD", set currency to "USD"
- If user says "50000 rupees" or "50000 INR", set currency to "INR"
- If currency not specified, set to null (do NOT default to USD)

TRAVELER COUNT:
- "couple" or "2 adults" → adults: 2
- "family" → adults: 2, children: 2 (unless specified)
- "solo" → adults: 1

Important:
- Extract ALL mentioned information accurately
- Use null for missing information (don't make up data)
- For dates, preserve user's phrasing ("March 2026", not "2026-03-XX")
- For currency, only set if explicitly mentioned or clearly inferrable
- Return ONLY the JSON object, no other text"""

        return prompt

    def _parse_preferences(self, response_text: str) -> Dict:
        """Parse Gemini response into structured preferences"""
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if "```json" in cleaned:
                match = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r'```\s*(.*?)\s*```', cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)

            # Parse JSON
            preferences = json.loads(cleaned)

            # Validate and set defaults
            return self._validate_preferences(preferences)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return self._get_default_preferences_sync()
        except Exception as e:
            logger.error(f"Preference parsing error: {e}")
            return self._get_default_preferences_sync()

    def _validate_preferences(self, preferences: Dict) -> Dict:
        """Validate and set defaults for extracted preferences"""

        # Ensure required fields exist
        defaults = self._get_default_preferences_sync()

        # Merge with defaults
        result = {**defaults, **preferences}

        # Validate nested structures
        if not isinstance(result.get('budget'), dict):
            result['budget'] = defaults['budget']

        if not isinstance(result.get('duration'), dict):
            result['duration'] = defaults['duration']

        if not isinstance(result.get('dates'), dict):
            result['dates'] = defaults['dates']

        if not isinstance(result.get('travelers'), dict):
            result['travelers'] = defaults['travelers']

        # Ensure lists
        if not isinstance(result.get('interests'), list):
            result['interests'] = []

        if not isinstance(result.get('destination_preferences'), list):
            result['destination_preferences'] = []

        return result

    def _get_origin_code(self, origin: Optional[str]) -> Optional[str]:
        """Convert origin city name to IATA code"""
        if not origin:
            return None

        # If already an IATA code (3 letters)
        if len(origin) == 3 and origin.isalpha():
            return origin.upper()

        # Common city to code mappings
        city_codes = {
            'delhi': 'DEL', 'new delhi': 'DEL',
            'mumbai': 'BOM', 'bombay': 'BOM',
            'bangalore': 'BLR', 'bengaluru': 'BLR',
            'chennai': 'MAA', 'madras': 'MAA',
            'hyderabad': 'HYD',
            'kolkata': 'CCU', 'calcutta': 'CCU',
            'pune': 'PNQ',
            'ahmedabad': 'AMD',
            'jaipur': 'JAI',
            'goa': 'GOI',
            'bangkok': 'BKK',
            'singapore': 'SIN',
            'kuala lumpur': 'KUL',
            'jakarta': 'CGK',
            'dubai': 'DXB',
            'london': 'LHR',
            'new york': 'JFK',
            'paris': 'CDG',
            'tokyo': 'NRT'
        }

        origin_lower = origin.lower()
        return city_codes.get(origin_lower)

    async def _get_default_preferences(self, user_request: str = "") -> Dict:
        """Return default preferences structure with assumptions"""
        prefs = self._get_default_preferences_sync()
        prefs['_assumptions'] = ["No preferences extracted - using defaults"]
        return prefs

    def _get_default_preferences_sync(self) -> Dict:
        """Return default preferences structure (synchronous)"""
        return {
            "origin": None,
            "destination_preferences": [],
            "destination_type": "mixed",
            "budget": {
                "total": 0,
                "currency": None,
                "budget_level": "mid-range"
            },
            "duration": {
                "days": 7,
                "nights": 6
            },
            "dates": {
                "departure": None,
                "return": None,
                "flexible": True
            },
            "travelers": {
                "adults": 1,
                "children": 0,
                "infants": 0
            },
            "interests": [],
            "travel_style": "comfort",
            "accommodation_preferences": ["hotel"],
            "special_requirements": [],
            "priorities": ["experience", "value"],
            "_assumptions": []
        }
