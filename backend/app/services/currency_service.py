import aiohttp
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from datetime import date, datetime
import json

logger = logging.getLogger(__name__)


class CurrencyService:
    """Handle currency detection, inference, and conversion with caching"""

    # Free API - no key required for basic usage
    API_URL = "https://api.exchangerate-api.com/v4/latest/{base}"

    # Origin location to default currency mapping
    ORIGIN_CURRENCY_MAP = {
        # India
        'DEL': 'INR', 'BOM': 'INR', 'BLR': 'INR', 'MAA': 'INR',
        'CCU': 'INR', 'HYD': 'INR', 'PNQ': 'INR', 'AMD': 'INR',
        'JAI': 'INR', 'GOI': 'INR',
        # Southeast Asia
        'BKK': 'THB', 'SIN': 'SGD', 'KUL': 'MYR', 'CGK': 'IDR',
        'MNL': 'PHP', 'HAN': 'VND', 'SGN': 'VND',
        # Middle East
        'DXB': 'AED', 'DOH': 'QAR', 'AUH': 'AED',
        # Europe
        'LHR': 'GBP', 'CDG': 'EUR', 'FRA': 'EUR', 'AMS': 'EUR',
        # Americas
        'JFK': 'USD', 'LAX': 'USD', 'YYZ': 'CAD', 'MEX': 'MXN',
        # East Asia
        'NRT': 'JPY', 'HND': 'JPY', 'PVG': 'CNY', 'ICN': 'KRW',
    }

    # Ambiguous currency terms
    CURRENCY_TERMS = {
        'rupees': ['INR', 'NPR', 'IDR', 'PKR', 'LKR', 'MUR', 'SCR'],
        'rupee': ['INR', 'NPR', 'IDR', 'PKR', 'LKR', 'MUR', 'SCR'],
        'dollars': ['USD', 'CAD', 'AUD', 'SGD', 'HKD', 'NZD'],
        'dollar': ['USD', 'CAD', 'AUD', 'SGD', 'HKD', 'NZD'],
        'pounds': ['GBP', 'EGP', 'LBP', 'SYP'],
        'pound': ['GBP', 'EGP', 'LBP', 'SYP'],
    }

    def __init__(self, redis_client=None):
        """
        Initialize currency service

        Args:
            redis_client: Optional Redis client for caching
        """
        self.redis = redis_client
        self.cache_ttl = 86400  # 24 hours

    async def infer_currency(
            self,
            budget_text: str,
            origin_code: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Infer currency from budget text and origin location

        Args:
            budget_text: Original budget text from user
            origin_code: IATA code of origin (e.g., 'DEL')

        Returns:
            (currency_code, assumption_note)
        """
        budget_lower = budget_text.lower() if budget_text else ""

        # Check for explicit currency codes (USD, INR, EUR, etc.)
        explicit_match = self._extract_explicit_currency(budget_lower)
        if explicit_match:
            return (explicit_match, f"Currency explicitly specified: {explicit_match}")

        # Check for ambiguous terms like "rupees", "dollars"
        for term, possible_currencies in self.CURRENCY_TERMS.items():
            if term in budget_lower:
                # Resolve ambiguity using origin
                if origin_code and origin_code in self.ORIGIN_CURRENCY_MAP:
                    origin_currency = self.ORIGIN_CURRENCY_MAP[origin_code]
                    if origin_currency in possible_currencies:
                        return (
                            origin_currency,
                            f"Inferred {origin_currency} from '{term}' based on {origin_code} origin"
                        )

                # Default to most common (first in list)
                default_currency = possible_currencies[0]
                return (
                    default_currency,
                    f"Assumed {default_currency} from '{term}' (origin not specified or ambiguous)"
                )

        # Fall back to origin-based currency
        if origin_code and origin_code in self.ORIGIN_CURRENCY_MAP:
            currency = self.ORIGIN_CURRENCY_MAP[origin_code]
            return (currency, f"Defaulted to {currency} based on {origin_code} origin")

        # Ultimate fallback
        return ('USD', 'Defaulted to USD (no currency or origin information)')

    def _extract_explicit_currency(self, text: str) -> Optional[str]:
        """Extract explicit currency code from text"""
        # Common currency codes
        currencies = ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'CNY', 'AUD', 'CAD',
                      'SGD', 'THB', 'MYR', 'IDR', 'PHP', 'VND', 'AED', 'QAR']

        text_upper = text.upper()
        for currency in currencies:
            if currency in text_upper:
                return currency

        return None

    async def get_exchange_rate(
            self,
            from_currency: str,
            to_currency: str
    ) -> Optional[Dict]:
        """
        Get exchange rate with caching

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            {
                "rate": Decimal,
                "last_updated": "YYYY-MM-DD",
                "source": "cache/api"
            }
        """
        if from_currency == to_currency:
            return {
                "rate": Decimal("1.0"),
                "last_updated": date.today().isoformat(),
                "source": "direct"
            }

        # Try cache first
        if self.redis:
            cached = await self._get_from_cache(from_currency, to_currency)
            if cached:
                return cached

        # Fetch from API
        try:
            rate_data = await self._fetch_from_api(from_currency, to_currency)

            # Cache the result
            if self.redis and rate_data:
                await self._save_to_cache(from_currency, to_currency, rate_data)

            return rate_data

        except Exception as e:
            logger.error(f"Failed to fetch exchange rate {from_currency}/{to_currency}: {e}")
            return None

    async def _get_from_cache(
            self,
            from_currency: str,
            to_currency: str
    ) -> Optional[Dict]:
        """Get rate from Redis cache"""
        try:
            cache_key = f"currency:{from_currency}:{to_currency}:{date.today().isoformat()}"
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"Currency rate cache hit: {from_currency}/{to_currency}")
                return {
                    "rate": Decimal(str(data["rate"])),
                    "last_updated": data["last_updated"],
                    "source": "cache"
                }
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _save_to_cache(
            self,
            from_currency: str,
            to_currency: str,
            rate_data: Dict
    ):
        """Save rate to Redis cache"""
        try:
            cache_key = f"currency:{from_currency}:{to_currency}:{date.today().isoformat()}"
            cache_value = json.dumps({
                "rate": str(rate_data["rate"]),
                "last_updated": rate_data["last_updated"]
            })
            await self.redis.setex(cache_key, self.cache_ttl, cache_value)
            logger.info(f"Cached currency rate: {from_currency}/{to_currency}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def _fetch_from_api(
            self,
            from_currency: str,
            to_currency: str
    ) -> Optional[Dict]:
        """Fetch exchange rate from API"""
        try:
            url = self.API_URL.format(base=from_currency)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()

                        rates = data.get('rates', {})
                        if to_currency in rates:
                            rate = Decimal(str(rates[to_currency]))

                            logger.info(f"Fetched exchange rate from API: {from_currency}/{to_currency} = {rate}")

                            return {
                                "rate": rate,
                                "last_updated": date.today().isoformat(),
                                "source": "api"
                            }
                    else:
                        logger.error(f"API returned status {response.status}")

        except Exception as e:
            logger.error(f"API fetch error: {e}")

        return None

    async def convert_amount(
            self,
            amount: float,
            from_currency: str,
            to_currency: str
    ) -> Optional[Dict]:
        """
        Convert amount between currencies

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            {
                "original_amount": float,
                "original_currency": str,
                "converted_amount": float,
                "converted_currency": str,
                "rate": Decimal,
                "formatted": str,
                "last_updated": str
            }
        """
        rate_data = await self.get_exchange_rate(from_currency, to_currency)

        if not rate_data:
            return None

        rate = rate_data["rate"]
        converted = float(Decimal(str(amount)) * rate)

        # Format currency symbols
        symbols = {
            'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹', 'JPY': '¥',
            'CNY': '¥', 'THB': '฿', 'SGD': 'S$'
        }

        from_symbol = symbols.get(from_currency, from_currency)
        to_symbol = symbols.get(to_currency, to_currency)

        formatted = f"{from_symbol}{amount:,.0f} {from_currency} (~{to_symbol}{converted:,.2f} {to_currency} at 1 {to_currency} = {1 / rate:.4f} {from_currency})"

        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "converted_amount": round(converted, 2),
            "converted_currency": to_currency,
            "rate": float(rate),
            "formatted": formatted,
            "last_updated": rate_data["last_updated"]
        }
