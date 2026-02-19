from typing import Dict, Optional
import logging
import json
import re
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class PreferencesAnalyzerAgent:
    """Genuine ReAct agent to analyze and extract structured travel preferences from natural language."""

    # Mirrors CurrencyService constants — used in the sync resolve_currency tool
    _ORIGIN_CURRENCY_MAP = {
        'DEL': 'INR', 'BOM': 'INR', 'BLR': 'INR', 'MAA': 'INR',
        'CCU': 'INR', 'HYD': 'INR', 'PNQ': 'INR', 'AMD': 'INR',
        'JAI': 'INR', 'GOI': 'INR',
        'BKK': 'THB', 'SIN': 'SGD', 'KUL': 'MYR', 'CGK': 'IDR',
        'MNL': 'PHP', 'HAN': 'VND', 'SGN': 'VND',
        'DXB': 'AED', 'DOH': 'QAR', 'AUH': 'AED',
        'LHR': 'GBP', 'CDG': 'EUR', 'FRA': 'EUR', 'AMS': 'EUR',
        'JFK': 'USD', 'LAX': 'USD', 'YYZ': 'CAD', 'MEX': 'MXN',
        'NRT': 'JPY', 'HND': 'JPY', 'PVG': 'CNY', 'ICN': 'KRW',
    }

    _CURRENCY_TERMS = {
        'rupees': ['INR', 'NPR', 'IDR', 'PKR', 'LKR'],
        'rupee':  ['INR', 'NPR', 'IDR', 'PKR', 'LKR'],
        'dollars': ['USD', 'CAD', 'AUD', 'SGD', 'HKD'],
        'dollar':  ['USD', 'CAD', 'AUD', 'SGD', 'HKD'],
        'pounds':  ['GBP', 'EGP', 'LBP'],
        'pound':   ['GBP', 'EGP', 'LBP'],
    }

    _EXPLICIT_CURRENCIES = [
        'USD', 'EUR', 'GBP', 'INR', 'JPY', 'CNY', 'AUD', 'CAD',
        'SGD', 'THB', 'MYR', 'IDR', 'PHP', 'VND', 'AED', 'QAR',
    ]

    _CITY_CODE_MAP = {
        'delhi': 'DEL', 'new delhi': 'DEL',
        'mumbai': 'BOM', 'bombay': 'BOM',
        'bangalore': 'BLR', 'bengaluru': 'BLR',
        'chennai': 'MAA', 'madras': 'MAA',
        'hyderabad': 'HYD',
        'kolkata': 'CCU', 'calcutta': 'CCU',
        'pune': 'PNQ', 'ahmedabad': 'AMD',
        'jaipur': 'JAI', 'goa': 'GOI',
        'bangkok': 'BKK', 'singapore': 'SIN',
        'kuala lumpur': 'KUL', 'jakarta': 'CGK',
        'dubai': 'DXB', 'london': 'LHR',
        'new york': 'JFK', 'paris': 'CDG',
        'tokyo': 'NRT',
    }

    def __init__(self, gemini_api_key: str, currency_service=None):
        # currency_service kept in signature for backward compatibility;
        # the tool uses inline sync logic so no async bridging is needed.
        self.currency_service = currency_service
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key
        )
        tools = self._build_tools()
        self.agent = create_react_agent(self.llm, tools=tools)
        logger.info("PreferencesAnalyzerAgent initialized with ReAct loop")

    # ------------------------------------------------------------------
    # Tool definitions — the LLM decides when to call these
    # ------------------------------------------------------------------

    def _build_tools(self):

        # Capture class-level constants via closure
        origin_map = self._ORIGIN_CURRENCY_MAP
        currency_terms = self._CURRENCY_TERMS
        explicit_currencies = self._EXPLICIT_CURRENCIES

        def parse_travel_dates(user_request: str, duration_days: int) -> dict:
            """
            Parse travel dates from natural language.
            Use this when the user mentions dates like 'March 2026', 'next month',
            'in 3 weeks', 'next week', or any relative or partial date expression.
            Returns a dict with 'departure' and 'return' keys in YYYY-MM-DD format,
            plus an 'assumption' string describing any default applied.
            """
            from app.utils.date_parser import DateParser
            return DateParser.parse_travel_dates(
                user_request=user_request,
                gemini_dates={},
                duration_days=duration_days
            )

        def resolve_currency(budget_text: str, origin_code: str) -> str:
            """
            Resolve an ambiguous currency term to an ISO currency code.
            Use this when the user says 'rupees', 'dollars', or 'pounds'
            without specifying which country's currency, or when no currency
            code appears in the text and origin context is needed to decide.
            Do NOT call this if the user already stated an explicit code like
            'USD', 'INR', or 'EUR'.
            Returns the resolved ISO currency code, e.g. 'INR', 'USD', 'GBP'.
            """
            text = budget_text.lower() if budget_text else ""

            # Check for explicit currency code first
            for code in explicit_currencies:
                if code in text.upper():
                    return code

            # Resolve ambiguous term using origin
            for term, candidates in currency_terms.items():
                if term in text:
                    if origin_code and origin_code in origin_map:
                        origin_currency = origin_map[origin_code]
                        if origin_currency in candidates:
                            return origin_currency
                    return candidates[0]  # most common fallback

            # Fall back to origin-based default
            if origin_code and origin_code in origin_map:
                return origin_map[origin_code]

            return "USD"

        return [
            StructuredTool.from_function(parse_travel_dates),
            StructuredTool.from_function(resolve_currency),
        ]

    # ------------------------------------------------------------------
    # Public interface — identical signature to original
    # ------------------------------------------------------------------

    async def analyze(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """
        Extract structured preferences from a natural language trip request.
        Runs the ReAct agent in a thread executor to avoid blocking the
        FastAPI event loop (agent.invoke is synchronous).
        """
        try:
            logger.info("PreferencesAnalyzerAgent: starting ReAct analysis")

            system_prompt = self._build_system_prompt()
            task_message = self._build_task_message(user_request, context)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_message),
            ]

            # Run synchronous agent.invoke in a thread to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent.invoke({"messages": messages})
            )

            # Extract the final text response from the last AI message
            final_text = ""
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.content:
                    content = msg.content
                    final_text = content if isinstance(content, str) else str(content)
                    break

            preferences = self._parse_preferences(final_text)
            logger.info(f"Preferences extracted: destination_type={preferences.get('destination_type', 'unknown')}")
            return preferences

        except Exception as e:
            logger.error(f"PreferencesAnalyzerAgent error: {e}", exc_info=True)
            return await self._get_default_preferences(user_request)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        return (
            "You are a travel planning assistant that extracts structured preferences "
            "from user trip requests.\n\n"
            "You have access to two tools:\n"
            "- parse_travel_dates: call this when the user mentions any date or time reference "
            "(e.g. 'March 2026', 'next month', 'in 3 weeks', 'next week')\n"
            "- resolve_currency: call this when the user's currency is ambiguous "
            "(e.g. 'rupees' could be INR/NPR/IDR) — skip this if an explicit code like USD or INR is present\n\n"
            "After using any necessary tools, return ONLY a valid JSON object with the extracted "
            "preferences — no markdown, no code blocks, no explanation."
        )

    def _build_task_message(self, user_request: str, context: Optional[Dict]) -> str:
        context_str = f"\nAdditional context: {json.dumps(context)}" if context else ""
        return f"""Extract structured travel preferences from this request:

\"{user_request}\"{context_str}

Return ONLY a JSON object with this exact structure:
{{
  "origin": "Origin city or airport code",
  "destination_preferences": ["list of preferred destinations"],
  "destination_type": "beach/mountain/city/cultural/adventure/mixed",
  "budget": {{
    "total": 0,
    "currency": "USD/INR/EUR/etc or null",
    "budget_level": "budget/mid-range/luxury"
  }},
  "duration": {{
    "days": 7,
    "nights": 6
  }},
  "dates": {{
    "departure": "YYYY-MM-DD or null",
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
  "accommodation_preferences": ["hotel"],
  "special_requirements": [],
  "priorities": ["experience", "value"],
  "_assumptions": ["any defaults or assumptions made"]
}}

Rules:
- Call parse_travel_dates if any date or time reference is present in the request
- Call resolve_currency only if currency is ambiguous (e.g. 'rupees') — not needed if user said 'USD' or 'INR'
- Use null for missing information; do not invent data
- "couple" -> adults: 2 | "family" -> adults: 2, children: 2 | "solo" -> adults: 1
- budget_level: total < 1000 USD equivalent = budget, 1000-5000 = mid-range, > 5000 = luxury
- _assumptions must list every default or inference made"""

    # ------------------------------------------------------------------
    # Response parsing — identical output contract to original
    # ------------------------------------------------------------------

    def _parse_preferences(self, response_text: str) -> Dict:
        try:
            cleaned = response_text.strip()
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            preferences = json.loads(cleaned)
            return self._validate_preferences(preferences)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in preferences: {e}")
            return self._get_default_preferences_sync()
        except Exception as e:
            logger.error(f"Preference parsing error: {e}")
            return self._get_default_preferences_sync()

    def _validate_preferences(self, preferences: Dict) -> Dict:
        defaults = self._get_default_preferences_sync()
        result = {**defaults, **preferences}
        for key in ('budget', 'duration', 'dates', 'travelers'):
            if not isinstance(result.get(key), dict):
                result[key] = defaults[key]
        if not isinstance(result.get('interests'), list):
            result['interests'] = []
        if not isinstance(result.get('destination_preferences'), list):
            result['destination_preferences'] = []
        if not isinstance(result.get('_assumptions'), list):
            result['_assumptions'] = []
        return result

    def _get_origin_code(self, origin: Optional[str]) -> Optional[str]:
        if not origin:
            return None
        if len(origin) == 3 and origin.isalpha():
            return origin.upper()
        return self._CITY_CODE_MAP.get(origin.lower())

    async def _get_default_preferences(self, user_request: str = "") -> Dict:
        prefs = self._get_default_preferences_sync()
        prefs['_assumptions'] = ["No preferences extracted - using defaults"]
        return prefs

    def _get_default_preferences_sync(self) -> Dict:
        return {
            "origin": None,
            "destination_preferences": [],
            "destination_type": "mixed",
            "budget": {"total": 0, "currency": None, "budget_level": "mid-range"},
            "duration": {"days": 7, "nights": 6},
            "dates": {"departure": None, "return": None, "flexible": True},
            "travelers": {"adults": 1, "children": 0, "infants": 0},
            "interests": [],
            "travel_style": "comfort",
            "accommodation_preferences": ["hotel"],
            "special_requirements": [],
            "priorities": ["experience", "value"],
            "_assumptions": [],
        }
