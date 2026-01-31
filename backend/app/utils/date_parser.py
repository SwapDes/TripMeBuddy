from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class DateParser:
    """Parse dates from natural language and AI responses"""

    MONTHS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }

    @staticmethod
    def parse_travel_dates(
            user_request: str,
            gemini_dates: Optional[Dict] = None,
            duration_days: int = 7
    ) -> Dict:
        """
        Parse travel dates from user request and/or Gemini extraction

        Args:
            user_request: Original user input
            gemini_dates: Dates extracted by Gemini AI
            duration_days: Trip duration in days

        Returns:
            {
                "departure": "YYYY-MM-DD",
                "return": "YYYY-MM-DD",
                "confidence": "high/medium/low",
                "assumption": "explanation of how dates were determined"
            }
        """
        # Try Gemini extraction first
        if gemini_dates:
            parsed = DateParser._parse_gemini_dates(gemini_dates, user_request, duration_days)
            if parsed and parsed.get("departure"):
                return parsed

        # Try parsing from raw user request
        parsed = DateParser._parse_from_text(user_request, duration_days)
        if parsed and parsed.get("departure"):
            return parsed

        # Default: 30 days from now
        return DateParser._get_default_dates(duration_days)

    @staticmethod
    def _parse_gemini_dates(gemini_dates: Dict, user_request: str, duration_days: int) -> Optional[Dict]:
        """Parse dates from Gemini AI extraction"""
        departure = gemini_dates.get('departure')
        return_date = gemini_dates.get('return')

        if not departure or departure == 'null':
            return None

        # Handle valid ISO date
        if re.match(r'^\d{4}-\d{2}-\d{2}$', str(departure)):
            dep_date = datetime.strptime(departure, '%Y-%m-%d')

            if return_date and re.match(r'^\d{4}-\d{2}-\d{2}$', str(return_date)):
                ret_date = datetime.strptime(return_date, '%Y-%m-%d')
            else:
                ret_date = dep_date + timedelta(days=duration_days)

            return {
                "departure": dep_date.strftime('%Y-%m-%d'),
                "return": ret_date.strftime('%Y-%m-%d'),
                "confidence": "high",
                "assumption": "Dates extracted from request"
            }

        # Handle partial dates (e.g., "2026-03-XX" or just text)
        return DateParser._parse_from_text(user_request, duration_days)

    @staticmethod
    def _parse_from_text(text: str, duration_days: int) -> Optional[Dict]:
        """Parse dates directly from text"""
        text_lower = text.lower()

        # Pattern: "March 2026" or "in March 2026"
        month_year_pattern = r'\b(in\s+)?(' + '|'.join(DateParser.MONTHS.keys()) + r')\s+(\d{4})\b'
        match = re.search(month_year_pattern, text_lower)

        if match:
            month_name = match.group(2)
            year = int(match.group(3))
            month = DateParser.MONTHS[month_name]

            # Use mid-month (15th) as departure
            dep_date = datetime(year, month, 15)
            ret_date = dep_date + timedelta(days=duration_days)

            return {
                "departure": dep_date.strftime('%Y-%m-%d'),
                "return": ret_date.strftime('%Y-%m-%d'),
                "confidence": "medium",
                "assumption": f"Interpreted '{match.group(0)}' as mid-month departure on {dep_date.strftime('%B %d, %Y')}"
            }

        # Pattern: "March 15, 2026" or "15 March 2026"
        full_date_pattern = r'\b(' + '|'.join(DateParser.MONTHS.keys()) + r')\s+(\d{1,2}),?\s+(\d{4})\b'
        match = re.search(full_date_pattern, text_lower)

        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3))
            month = DateParser.MONTHS[month_name]

            dep_date = datetime(year, month, day)
            ret_date = dep_date + timedelta(days=duration_days)

            return {
                "departure": dep_date.strftime('%Y-%m-%d'),
                "return": ret_date.strftime('%Y-%m-%d'),
                "confidence": "high",
                "assumption": f"Extracted exact departure date: {dep_date.strftime('%B %d, %Y')}"
            }

        # Pattern: "next month"
        if 'next month' in text_lower:
            today = datetime.now()
            next_month = today + timedelta(days=30)
            dep_date = datetime(next_month.year, next_month.month, 15)
            ret_date = dep_date + timedelta(days=duration_days)

            return {
                "departure": dep_date.strftime('%Y-%m-%d'),
                "return": ret_date.strftime('%Y-%m-%d'),
                "confidence": "medium",
                "assumption": f"Interpreted 'next month' as {dep_date.strftime('%B %Y')}"
            }

        return None

    @staticmethod
    def _get_default_dates(duration_days: int) -> Dict:
        """Return default dates (30 days from now)"""
        today = datetime.now()
        dep_date = today + timedelta(days=30)
        ret_date = dep_date + timedelta(days=duration_days)

        return {
            "departure": dep_date.strftime('%Y-%m-%d'),
            "return": ret_date.strftime('%Y-%m-%d'),
            "confidence": "low",
            "assumption": f"No dates specified in request - defaulted to {dep_date.strftime('%B %d, %Y')} (30 days from today)"
        }
