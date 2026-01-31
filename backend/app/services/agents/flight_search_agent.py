from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class FlightSearchAgent:
    """Agent to search flights using Amadeus API with currency conversion"""

    def __init__(self, amadeus_service, currency_service=None):
        """
        Initialize with Amadeus service and optional currency service

        Args:
            amadeus_service: Instance of AmadeusService
            currency_service: Optional CurrencyService for price conversion
        """
        self.amadeus = amadeus_service
        self.currency_service = currency_service
        logger.info("FlightSearchAgent initialized")

    def search(self, preferences: Dict, destination: Dict) -> Dict:
        """
        Search for flights based on preferences and selected destination

        Args:
            preferences: User preferences from PreferencesAnalyzerAgent
            destination: Selected destination from DestinationResearchAgent

        Returns:
            Dict with flight search results
        """
        try:
            logger.info("Searching flights for trip plan")

            # Extract search parameters
            origin = self._get_origin_code(preferences)
            destination_code = destination.get('airport_code')
            dates = preferences.get('dates', {})
            travelers = preferences.get('travelers', {})

            if not origin or not destination_code:
                logger.error(f"Missing origin or destination: {origin} -> {destination_code}")
                return {
                    "success": False,
                    "flights": [],
                    "error": "Missing origin or destination airport code"
                }

            # Get departure and return dates
            departure_date, return_date = self._get_travel_dates(dates, preferences.get('duration', {}))

            if not departure_date:
                logger.error("Could not determine departure date")
                return {
                    "success": False,
                    "flights": [],
                    "error": "Could not determine travel dates"
                }

            # Search flights
            adults = travelers.get('adults', 1)

            logger.info(
                f"Searching: {origin} -> {destination_code}, {departure_date} to {return_date}, {adults} adults")

            result = self.amadeus.search_flights(
                origin=origin,
                destination=destination_code,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                max_results=5  # Get top 5 options
            )

            if result.get('success') and result.get('data'):
                # Analyze and rank flights
                ranked_flights = self._rank_flights(result['data'], preferences)

                # Add currency conversion
                user_currency = preferences.get('budget', {}).get('currency', 'USD')
                if self.currency_service and user_currency:
                    ranked_flights = self._add_currency_conversions(ranked_flights, user_currency)

                return {
                    "success": True,
                    "flights": ranked_flights,
                    "search_params": {
                        "origin": origin,
                        "destination": destination_code,
                        "departure_date": departure_date,
                        "return_date": return_date,
                        "adults": adults
                    },
                    "count": len(ranked_flights)
                }
            else:
                logger.warning(f"No flights found or search failed: {result.get('error')}")
                return {
                    "success": False,
                    "flights": [],
                    "error": result.get('error', 'No flights found'),
                    "search_params": {
                        "origin": origin,
                        "destination": destination_code,
                        "departure_date": departure_date,
                        "return_date": return_date
                    }
                }

        except Exception as e:
            logger.error(f"Flight search error: {e}")
            return {
                "success": False,
                "flights": [],
                "error": str(e)
            }

    def _add_currency_conversions(self, flights: List[Dict], target_currency: str) -> List[Dict]:
        """Add converted prices to flight results"""

        # Run async conversion in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._add_currency_conversions_async(flights, target_currency))
        finally:
            loop.close()

    async def _add_currency_conversions_async(self, flights: List[Dict], target_currency: str) -> List[Dict]:
        """Async version of currency conversion"""

        for flight in flights:
            try:
                price_info = flight.get('price', {})
                original_currency = price_info.get('currency', 'USD')
                total_price = float(price_info.get('total', 0))

                # Skip conversion if already in target currency
                if original_currency == target_currency:
                    flight['price']['converted'] = {
                        'amount': total_price,
                        'currency': target_currency,
                        'note': f"Price already in {target_currency}"
                    }
                    continue

                # Convert currency
                conversion = await self.currency_service.convert_amount(
                    amount=total_price,
                    from_currency=original_currency,
                    to_currency=target_currency
                )

                if conversion:
                    flight['price']['converted'] = {
                        'amount': conversion['converted_amount'],
                        'currency': target_currency,
                        'original_amount': total_price,
                        'original_currency': original_currency,
                        'rate': conversion['rate'],
                        'formatted': conversion['formatted'],
                        'rate_date': conversion['last_updated']
                    }
                    logger.info(
                        f"Converted flight price: {original_currency} {total_price} → {target_currency} {conversion['converted_amount']}")
                else:
                    logger.warning(f"Could not convert {original_currency} to {target_currency}")
                    flight['price']['converted'] = {
                        'error': 'Conversion failed',
                        'original_amount': total_price,
                        'original_currency': original_currency
                    }

            except Exception as e:
                logger.error(f"Error converting flight price: {e}")

        return flights

    def _get_origin_code(self, preferences: Dict) -> Optional[str]:
        """Extract origin airport code from preferences"""
        origin = preferences.get('origin')

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
            'manila': 'MNL',
            'hanoi': 'HAN',
            'ho chi minh': 'SGN',
            'dubai': 'DXB',
            'london': 'LHR',
            'new york': 'JFK',
            'paris': 'CDG'
        }

        origin_lower = origin.lower()
        return city_codes.get(origin_lower, origin[:3].upper() if len(origin) >= 3 else None)

    def _get_travel_dates(self, dates: Dict, duration: Dict) -> tuple:
        """Determine departure and return dates"""

        departure_str = dates.get('departure')
        return_str = dates.get('return')

        # If dates are specified, use them
        if departure_str and departure_str != 'null':
            try:
                departure_date = departure_str

                # If return date specified, use it
                if return_str and return_str != 'null':
                    return_date = return_str
                else:
                    # Calculate return date from duration
                    days = duration.get('days', 7)
                    dep_dt = datetime.strptime(departure_str, '%Y-%m-%d')
                    ret_dt = dep_dt + timedelta(days=days)
                    return_date = ret_dt.strftime('%Y-%m-%d')

                return departure_date, return_date

            except Exception as e:
                logger.error(f"Date parsing error: {e}")

        # Default: 30 days from now
        now = datetime.now()
        departure_dt = now + timedelta(days=30)
        days = duration.get('days', 7)
        return_dt = departure_dt + timedelta(days=days)

        departure_date = departure_dt.strftime('%Y-%m-%d')
        return_date = return_dt.strftime('%Y-%m-%d')

        logger.info(f"Using default dates: {departure_date} to {return_date}")
        return departure_date, return_date

    def _rank_flights(self, flights: List[Dict], preferences: Dict) -> List[Dict]:
        """Rank flights based on preferences (price, duration, stops)"""

        budget_level = preferences.get('budget', {}).get('budget_level', 'mid-range')

        # Extract prices and durations for normalization
        prices = []
        for flight in flights:
            try:
                price = float(flight.get('price', {}).get('total', 0))
                if price > 0:
                    prices.append(price)
            except:
                pass

        if not prices:
            return flights[:3]  # Return first 3 if no valid prices

        min_price = min(prices)
        max_price = max(prices)

        # Score each flight
        scored_flights = []
        for flight in flights:
            try:
                price = float(flight.get('price', {}).get('total', 0))

                # Normalize price (0-100, lower is better)
                if max_price > min_price:
                    price_score = 100 - ((price - min_price) / (max_price - min_price)) * 100
                else:
                    price_score = 50

                # Weight by budget level
                if budget_level == 'budget':
                    weight = 0.7  # Price matters most
                elif budget_level == 'luxury':
                    weight = 0.3  # Price matters least
                else:
                    weight = 0.5  # Balanced

                final_score = price_score * weight + 50 * (1 - weight)

                flight['ranking_score'] = final_score
                scored_flights.append(flight)

            except Exception as e:
                logger.error(f"Error scoring flight: {e}")
                flight['ranking_score'] = 0
                scored_flights.append(flight)

        # Sort by score
        scored_flights.sort(key=lambda x: x.get('ranking_score', 0), reverse=True)

        # Return top 3
        return scored_flights[:3]

    def get_best_flight(self, search_result: Dict) -> Optional[Dict]:
        """Get the best flight from search results"""
        flights = search_result.get('flights', [])

        if not flights:
            return None

        # Return highest ranked flight
        return flights[0]
