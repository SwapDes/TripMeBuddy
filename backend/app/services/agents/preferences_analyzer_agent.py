from typing import Dict, Optional
import logging
import json
import re
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class PreferencesAnalyzerAgent:
    """Genuine ReAct agent to analyze and extract structured travel preferences from natural language."""

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
        self.currency_service = currency_service
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key
        )
        tools = self._build_tools()
        self.agent = create_react_agent(self.llm, tools=tools)
        logger.info("PreferencesAnalyzerAgent initialized with ReAct loop")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools(self):

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
            without specifying which country's currency, or when no explicit
            currency code appears in the text and origin context is needed.
            Do NOT call this if the user already stated an explicit code like
            'USD', 'INR', or 'EUR'.
            Returns the resolved ISO currency code, e.g. 'INR', 'USD', 'GBP'.
            """
            text = budget_text.lower() if budget_text else ""

            for code in explicit_currencies:
                if code in text.upper():
                    return code

            for term, candidates in currency_terms.items():
                if term in text:
                    if origin_code and origin_code in origin_map:
                        origin_currency = origin_map[origin_code]
                        if origin_currency in candidates:
                            return origin_currency
                    return candidates[0]

            if origin_code and origin_code in origin_map:
                return origin_map[origin_code]

            return "USD"

        return [
            StructuredTool.from_function(parse_travel_dates),
            StructuredTool.from_function(resolve_currency),
        ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def analyze(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        try:
            logger.info("PreferencesAnalyzerAgent: starting ReAct analysis")

            messages = [
                SystemMessage(content=self._build_system_prompt()),
                HumanMessage(content=self._build_task_message(user_request, context)),
            ]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent.invoke({"messages": messages})
            )

            final_text = self._extract_final_text(result["messages"])

            if not final_text:
                logger.error("PreferencesAnalyzerAgent: empty final text from agent, using defaults")
                return await self._get_default_preferences(user_request)

            preferences = self._parse_preferences(final_text)
            logger.info(f"Preferences extracted: destination_type={preferences.get('destination_type', 'unknown')}")
            return preferences

        except Exception as e:
            logger.error(f"PreferencesAnalyzerAgent error: {e}", exc_info=True)
            return await self._get_default_preferences(user_request)

    # ------------------------------------------------------------------
    # Message extraction — handles both plain text and tool-call content
    # ------------------------------------------------------------------

    def _extract_final_text(self, messages: list) -> str:
        """
        Extract the final plain-text response from the agent message list.
        When the ReAct agent uses tools, intermediate AIMessages contain
        content as a list of dicts (tool_use blocks) rather than a string.
        We skip those and find the last AIMessage whose content is a
        non-empty plain string — that is the final answer.
        """
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue

            content = msg.content

            # Plain string content — this is what we want
            if isinstance(content, str) and content.strip():
                return content.strip()

            # List content — may be tool call blocks or a mix
            if isinstance(content, list):
                # Collect only text-type entries
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
            "You are a travel planning assistant that extracts structured preferences "
            "from user trip requests.\n\n"
            "You have access to two tools:\n"
            "- parse_travel_dates: call this when the user mentions any date or time reference "
            "(e.g. 'March 2026', 'next month', 'in 3 weeks', '1st March 2026')\n"
            "- resolve_currency: call this when the user's currency is ambiguous "
            "(e.g. 'rupees') — skip if an explicit code like USD or INR is already present\n\n"
            "After using any necessary tools, return ONLY a valid JSON object — "
            "no markdown fences, no code blocks, no explanation text."
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
- Call parse_travel_dates if any date or time reference is present
- Call resolve_currency only if currency is ambiguous — not needed if user said 'INR' or 'USD'
- Use null for missing information; do not invent data
- "couple" -> adults: 2 | "family" -> adults: 2, children: 2 | "solo" -> adults: 1
- budget_level: total < 1000 USD equivalent = budget, 1000-5000 = mid-range, > 5000 = luxury
- _assumptions must list every default or inference made
- origin must map city names correctly: "Delhi" and "New Delhi" both map to "DEL\""""

    # ------------------------------------------------------------------
    # Parsing and validation
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
            logger.error(f"Response text was: {response_text[:300]}")
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
        # Ensure currency is never None — fallback to USD to satisfy Pydantic schema
        if not result.get('budget', {}).get('currency'):
            result['budget']['currency'] = 'USD'
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
            "budget": {"total": 0, "currency": "USD", "budget_level": "mid-range"},
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
