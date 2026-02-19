from typing import Dict, List, Optional
import logging
import json
import re
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)

# Comprehensive IATA code lookup used by the validate_airport_code tool.
# The LLM calls this instead of guessing from training data, eliminating
# the need for the Python airport-code cleaning post-processing.
IATA_LOOKUP = {
    # India
    "delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR",
    "chennai": "MAA", "madras": "MAA",
    "hyderabad": "HYD", "kolkata": "CCU",
    "calcutta": "CCU", "pune": "PNQ",
    "ahmedabad": "AMD", "jaipur": "JAI",
    "goa": "GOI", "kochi": "COK",
    "lucknow": "LKO", "varanasi": "VNS",
    # Southeast Asia
    "bangkok": "BKK", "singapore": "SIN",
    "kuala lumpur": "KUL", "jakarta": "CGK",
    "bali": "DPS", "denpasar": "DPS",
    "manila": "MNL", "hanoi": "HAN",
    "ho chi minh city": "SGN", "saigon": "SGN",
    "phuket": "HKT", "chiang mai": "CNX",
    "yangon": "RGN", "phnom penh": "PNH",
    "siem reap": "REP", "vientiane": "VTE",
    # East Asia
    "tokyo": "NRT", "osaka": "KIX",
    "seoul": "ICN", "beijing": "PEK",
    "shanghai": "PVG", "hong kong": "HKG",
    "taipei": "TPE",
    # South Asia
    "colombo": "CMB", "kathmandu": "KTM",
    "dhaka": "DAC", "karachi": "KHI",
    "lahore": "LHE", "islamabad": "ISB",
    # Middle East
    "dubai": "DXB", "abu dhabi": "AUH",
    "doha": "DOH", "riyadh": "RUH",
    "muscat": "MCT", "kuwait city": "KWI",
    "amman": "AMM", "beirut": "BEY",
    # Europe
    "london": "LHR", "paris": "CDG",
    "amsterdam": "AMS", "frankfurt": "FRA",
    "madrid": "MAD", "barcelona": "BCN",
    "rome": "FCO", "milan": "MXP",
    "zurich": "ZRH", "vienna": "VIE",
    "prague": "PRG", "warsaw": "WAW",
    "athens": "ATH", "istanbul": "IST",
    "lisbon": "LIS", "brussels": "BRU",
    "copenhagen": "CPH", "stockholm": "ARN",
    "oslo": "OSL", "helsinki": "HEL",
    # Americas
    "new york": "JFK", "los angeles": "LAX",
    "chicago": "ORD", "miami": "MIA",
    "toronto": "YYZ", "vancouver": "YVR",
    "mexico city": "MEX", "cancun": "CUN",
    "sao paulo": "GRU", "rio de janeiro": "GIG",
    "bogota": "BOG", "lima": "LIM",
    "buenos aires": "EZE", "santiago": "SCL",
    # Africa & Oceania
    "sydney": "SYD", "melbourne": "MEL",
    "auckland": "AKL", "nairobi": "NBO",
    "cairo": "CAI", "cape town": "CPT",
    "johannesburg": "JNB",
    # Common codes that might be passed directly
    "del": "DEL", "bom": "BOM", "blr": "BLR",
    "bkk": "BKK", "sin": "SIN", "kul": "KUL",
    "dxb": "DXB", "lhr": "LHR", "cdg": "CDG",
}


class DestinationResearchAgent:
    """Genuine ReAct agent to research and recommend travel destinations."""

    def __init__(self, gemini_api_key: str, amadeus_service=None):
        self.amadeus_service = amadeus_service
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key
        )
        tools = self._build_tools()
        self.agent = create_react_agent(self.llm, tools=tools)
        logger.info("DestinationResearchAgent initialized")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools(self):

        def validate_airport_code(city: str, country: str) -> str:
            """
            Validate and return the correct 3-letter IATA airport code for a city.
            Always call this for every destination before including it in your response,
            to ensure the airport code is correct and will work with the flight search API.
            Returns the verified 3-letter IATA code, or an empty string if not found.
            """
            key = city.lower().strip()
            if key in IATA_LOOKUP:
                return IATA_LOOKUP[key]
            # Try country-qualified lookup
            key2 = f"{city.lower().strip()}, {country.lower().strip()}"
            if key2 in IATA_LOOKUP:
                return IATA_LOOKUP[key2]
            # If already a valid 3-letter code, return it
            if len(city) == 3 and city.isalpha():
                return city.upper()
            logger.warning(f"validate_airport_code: no IATA code found for {city}, {country}")
            return ""

        return [StructuredTool.from_function(validate_airport_code)]

    # ------------------------------------------------------------------
    # Public interface — identical to original
    # ------------------------------------------------------------------

    def research(self, preferences: Dict) -> Dict:
        """
        Research and recommend destinations based on preferences.
        Runs the ReAct agent synchronously (called from a thread worker).
        """
        try:
            logger.info("Researching destinations based on preferences")

            messages = [
                SystemMessage(content=self._build_system_prompt()),
                HumanMessage(content=self._build_task_message(preferences)),
            ]

            result = self.agent.invoke({"messages": messages})
            final_text = self._extract_final_text(result["messages"])

            if not final_text:
                logger.error("DestinationResearchAgent: empty response from agent")
                return {"destinations": [], "reasoning": "No recommendations available"}

            parsed = self._parse_research_response(final_text)
            parsed = self._validate_destination_match(parsed, preferences)
            logger.info(f"Found {len(parsed.get('destinations', []))} destination recommendations")
            return parsed

        except Exception as e:
            logger.error(f"Destination research error: {e}")
            return {"destinations": [], "reasoning": f"Error: {str(e)}"}

    def select_best_destination(self, research_result: Dict) -> Optional[Dict]:
        """Select the best destination from research results — identical to original."""
        destinations = research_result.get("destinations", [])
        if not destinations:
            return None
        best = destinations[0]
        if research_result.get("fallback_detected"):
            best["_fallback_detected"] = True
            best["_requested_destination"] = research_result.get("requested_destination")
            best["_fallback_reason"] = research_result.get("fallback_reason")
        logger.info(f"Selected destination: {best.get('city', 'Unknown')} (score: {best.get('match_score', 0)})")
        return best

    # ------------------------------------------------------------------
    # Message extraction
    # ------------------------------------------------------------------

    def _extract_final_text(self, messages: list) -> str:
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue
            content = msg.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            text_parts.append(text)
                    elif isinstance(block, str) and block.strip():
                        text_parts.append(block.strip())
                combined = "\n".join(text_parts).strip()
                if combined:
                    return combined
        return ""

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert travel destination researcher.\n\n"
            "You have one tool: validate_airport_code.\n"
            "Call validate_airport_code for EVERY destination you plan to recommend "
            "before including it in your final response. Use the verified code returned "
            "by the tool — never guess an airport code from memory.\n\n"
            "After validating all airport codes, return ONLY a valid JSON object — "
            "no markdown fences, no code blocks, no explanation text."
        )

    def _build_task_message(self, preferences: Dict) -> str:
        origin = preferences.get("origin", "Not specified")
        destination_prefs = preferences.get("destination_preferences", [])
        destination_type = preferences.get("destination_type", "mixed")
        budget = preferences.get("budget", {})
        duration = preferences.get("duration", {})
        dates = preferences.get("dates", {})
        interests = preferences.get("interests", [])
        travel_style = preferences.get("travel_style", "comfort")

        if destination_prefs:
            destination_instruction = (
                f"CRITICAL: The user specifically requested: {', '.join(destination_prefs)}. "
                f"You MUST recommend the user's requested destination as your top choice unless "
                f"it is completely inaccessible from {origin}. If viable, it MUST be #1."
            )
        else:
            destination_instruction = "The user is open to destination suggestions."

        return f"""Research and recommend the top 2-3 most suitable travel destinations.

PREFERENCES:
- Origin: {origin}
- Preferred Destinations: {', '.join(destination_prefs) if destination_prefs else 'Open to suggestions'}
- Destination Type: {destination_type}
- Budget Level: {budget.get('budget_level', 'mid-range')}
- Total Budget: {budget.get('total', 'Not specified')} {budget.get('currency', '')}
- Duration: {duration.get('days', 7)} days
- Departure Date: {dates.get('departure', 'Flexible')}
- Interests: {', '.join(interests) if interests else 'General travel'}
- Travel Style: {travel_style}

{destination_instruction}

INSTRUCTIONS:
1. Decide which 2-3 destinations to recommend
2. Call validate_airport_code for each destination to get the correct IATA code
3. Use the code returned by the tool in your response — never a code from memory
4. Return ONLY a JSON object in this exact format:

{{
  "destinations": [
    {{
      "city": "City name",
      "country": "Country",
      "airport_code": "VERIFIED 3-letter IATA code from tool",
      "reasoning": "Why this fits the preferences",
      "match_score": 95,
      "highlights": ["attraction 1", "attraction 2", "attraction 3"],
      "best_for": ["interest1", "interest2"],
      "estimated_daily_cost": 120,
      "weather_info": "Weather during travel dates",
      "cultural_notes": "Important cultural considerations",
      "visa_requirements": "Visa requirements from origin"
    }}
  ],
  "overall_reasoning": "Summary of why these destinations were chosen",
  "alternative_suggestions": ["Alternative 1", "Alternative 2"]
}}"""

    # ------------------------------------------------------------------
    # Response parsing — identical output contract to original
    # ------------------------------------------------------------------

    def _parse_research_response(self, response_text: str) -> Dict:
        try:
            cleaned = response_text.strip()
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)

            result = json.loads(cleaned)

            if "destinations" not in result:
                result = {"destinations": [], "overall_reasoning": cleaned[:500]}

            # Ensure airport codes are clean 3-letter strings (defensive)
            for dest in result.get("destinations", []):
                code = dest.get("airport_code", "")
                if isinstance(code, str):
                    # Strip any trailing text the LLM may have added
                    code = re.sub(r'[^A-Za-z].*', '', code.strip())
                    dest["airport_code"] = code[:3].upper() if len(code) >= 3 else code.upper()

            # Sort by match_score descending
            if result.get("destinations"):
                result["destinations"] = sorted(
                    result["destinations"],
                    key=lambda x: x.get("match_score", 0),
                    reverse=True
                )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in research response: {e}")
            return {"destinations": [], "overall_reasoning": response_text[:500], "parse_error": str(e)}
        except Exception as e:
            logger.error(f"Research response parsing error: {e}")
            return {"destinations": [], "overall_reasoning": "Error parsing recommendations", "error": str(e)}

    def _validate_destination_match(self, result: Dict, preferences: Dict) -> Dict:
        """Identical logic to original — ensures user's requested destination is top result."""
        destination_prefs = preferences.get("destination_preferences", [])
        if not destination_prefs:
            return result

        requested = destination_prefs[0].lower()
        destinations = result.get("destinations", [])
        if not destinations:
            return result

        top = destinations[0]
        top_city = top.get("city", "").lower()
        top_country = top.get("country", "").lower()

        matches = (
            requested in top_city or top_city in requested or
            requested in top_country or top_country in requested
        )

        if not matches:
            logger.warning(f"Agent recommended '{top.get('city')}' but user requested '{destination_prefs[0]}'")
            result["fallback_detected"] = True
            result["requested_destination"] = destination_prefs[0]
            result["recommended_destination"] = top.get("city")
            result["fallback_reason"] = top.get("reasoning", "Unknown reason")

            for idx, dest in enumerate(destinations):
                dest_city = dest.get("city", "").lower()
                dest_country = dest.get("country", "").lower()
                if requested in dest_city or dest_city in requested or requested in dest_country:
                    destinations.insert(0, destinations.pop(idx))
                    result["destinations"] = destinations
                    result["fallback_corrected"] = True
                    logger.info(f"Moved user's requested destination to top position")
                    break
            else:
                result["user_destination_not_found"] = True
        else:
            result["fallback_detected"] = False

        return result
