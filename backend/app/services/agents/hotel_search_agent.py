from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class HotelSearchAgent:
    """Agent to search hotels using Amadeus API with currency conversion"""

    def __init__(self, amadeus_service, currency_service=None):
        """
        Initialize with Amadeus service and optional currency service

        Args:
            amadeus_service: Instance of AmadeusService
            currency_service: Optional CurrencyService for price conversion
        """
        self.amadeus = amadeus_service
        self.currency_service = currency_service
        logger.info("HotelSearchAgent initialized")

    def search(self, preferences: Dict, destination: Dict, flight_result: Dict) -> Dict:
        """
        Search for hotels based on preferences, destination, and flight dates

        Args:
            preferences: User preferences from PreferencesAnalyzerAgent
            destination: Selected destination from DestinationResearchAgent
            flight_result: Flight search results with dates

        Returns:
            Dict with hotel search results
        """
        try:
            logger.info("Searching hotels for trip plan")

            # Extract search parameters
            city_code = destination.get('airport_code')

            # Get dates from flight search
            search_params = flight_result.get('search_params', {})
            check_in = search_params.get('departure_date')
            check_out = search_params.get('return_date')

            # Fallback to preferences if not in flight results
            if not check_in or not check_out:
                dates = preferences.get('dates', {})
                duration = preferences.get('duration', {})
                check_in, check_out = self._get_hotel_dates(dates, duration)

            travelers = preferences.get('travelers', {})
            adults = travelers.get('adults', 1)

            if not city_code:
                logger.error("Missing destination city code")
                return {
                    "success": False,
                    "hotels": [],
                    "error": "Missing destination city code"
                }

            if not check_in or not check_out:
                logger.error("Could not determine check-in/check-out dates")
                return {
                    "success": False,
                    "hotels": [],
                    "error": "Could not determine hotel dates"
                }

            logger.info(f"Searching hotels in {city_code}, {check_in} to {check_out}, {adults} adults")

            # Search hotels
            result = self.amadeus.search_hotels(
                city_code=city_code,
                check_in_date=check_in,
                check_out_date=check_out,
                adults=adults,
                radius=10,  # 10 km radius
                radius_unit="KM",
                max_results=10
            )

            if result.get('data'):
                # Check for success flag or data presence
                success = result.get('success', False)

                # Rank hotels based on preferences
                ranked_hotels = self._rank_hotels(result['data'], preferences)

                # Add currency conversion
                user_currency = preferences.get('budget', {}).get('currency', 'USD')
                if self.currency_service and user_currency:
                    ranked_hotels = self._add_currency_conversions(ranked_hotels, user_currency)

                return {
                    "success": success,
                    "hotels": ranked_hotels,
                    "search_params": {
                        "city_code": city_code,
                        "check_in": check_in,
                        "check_out": check_out,
                        "adults": adults
                    },
                    "count": len(ranked_hotels),
                    "error": result.get('error'),
                    "message": result.get('message'),
                    "planning_note": result.get('planning_note')
                }
            else:
                logger.warning(f"No hotels found in {city_code}: {result.get('error')}")

                # Return failure with clear message
                return {
                    "success": False,
                    "hotels": [],
                    "error": result.get('error', 'No hotels found'),
                    "message": result.get('message',
                                          f"Limited hotel availability in {city_code}. Consider nearby cities or adjust search parameters."),
                    "planning_note": result.get('planning_note'),
                    "search_params": {
                        "city_code": city_code,
                        "check_in": check_in,
                        "check_out": check_out
                    }
                }

        except Exception as e:
            logger.error(f"Hotel search error: {e}")
            return {
                "success": False,
                "hotels": [],
                "error": str(e)
            }

    def _add_currency_conversions(self, hotels: List[Dict], target_currency: str) -> List[Dict]:
        """Add converted prices to hotel results"""

        # Run async conversion in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._add_currency_conversions_async(hotels, target_currency))
        finally:
            loop.close()

    async def _add_currency_conversions_async(self, hotels: List[Dict], target_currency: str) -> List[Dict]:
        """Async version of currency conversion"""

        for hotel in hotels:
            try:
                offers = hotel.get('offers', [])
                if not offers:
                    continue

                # Convert price for the first (best) offer
                for offer in offers:
                    price_info = offer.get('price', {})
                    original_currency = price_info.get('currency', 'USD')
                    total_price = float(price_info.get('total', 0))

                    # Skip conversion if already in target currency
                    if original_currency == target_currency:
                        offer['price']['converted'] = {
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
                        offer['price']['converted'] = {
                            'amount': conversion['converted_amount'],
                            'currency': target_currency,
                            'original_amount': total_price,
                            'original_currency': original_currency,
                            'rate': conversion['rate'],
                            'formatted': conversion['formatted'],
                            'rate_date': conversion['last_updated']
                        }
                        logger.info(
                            f"Converted hotel price: {original_currency} {total_price} → {target_currency} {conversion['converted_amount']}")
                    else:
                        logger.warning(f"Could not convert {original_currency} to {target_currency}")
                        offer['price']['converted'] = {
                            'error': 'Conversion failed',
                            'original_amount': total_price,
                            'original_currency': original_currency
                        }

            except Exception as e:
                logger.error(f"Error converting hotel price: {e}")

        return hotels

    def _get_hotel_dates(self, dates: Dict, duration: Dict) -> tuple:
        """Determine check-in and check-out dates"""

        departure_str = dates.get('departure')
        return_str = dates.get('return')

        # If dates are specified, use them
        if departure_str and departure_str != 'null':
            try:
                check_in = departure_str

                if return_str and return_str != 'null':
                    check_out = return_str
                else:
                    # Calculate from duration
                    days = duration.get('days', 7)
                    check_in_dt = datetime.strptime(departure_str, '%Y-%m-%d')
                    check_out_dt = check_in_dt + timedelta(days=days)
                    check_out = check_out_dt.strftime('%Y-%m-%d')

                return check_in, check_out

            except Exception as e:
                logger.error(f"Date parsing error: {e}")

        # Default: 30 days from now
        now = datetime.now()
        check_in_dt = now + timedelta(days=30)
        days = duration.get('days', 7)
        check_out_dt = check_in_dt + timedelta(days=days)

        check_in = check_in_dt.strftime('%Y-%m-%d')
        check_out = check_out_dt.strftime('%Y-%m-%d')

        logger.info(f"Using default hotel dates: {check_in} to {check_out}")
        return check_in, check_out

    def _rank_hotels(self, hotels: List[Dict], preferences: Dict) -> List[Dict]:
        """Rank hotels based on preferences and price"""

        budget_level = preferences.get('budget', {}).get('budget_level', 'mid-range')
        accommodation_prefs = preferences.get('accommodation_preferences', ['hotel'])

        # Extract prices for normalization
        prices = []
        for hotel in hotels:
            try:
                offers = hotel.get('offers', [])
                if offers:
                    price = float(offers[0].get('price', {}).get('total', 0))
                    if price > 0:
                        prices.append(price)
            except:
                pass

        # Handle hotels without offers (fallback case)
        scored_hotels = []
        for hotel in hotels:
            offers = hotel.get('offers', [])

            if not offers:
                # Hotel has no offers (fallback case) - still include it
                hotel['ranking_score'] = 0
                scored_hotels.append(hotel)
                continue

            try:
                price = float(offers[0].get('price', {}).get('total', 0))

                if not prices:
                    # No valid prices at all - give neutral score
                    hotel['ranking_score'] = 50
                    scored_hotels.append(hotel)
                    continue

                min_price = min(prices)
                max_price = max(prices)

                # Normalize price (0-100, lower is better)
                if max_price > min_price:
                    price_score = 100 - ((price - min_price) / (max_price - min_price)) * 100
                else:
                    price_score = 50

                # Weight by budget level
                if budget_level == 'budget':
                    weight = 0.8  # Price matters most
                elif budget_level == 'luxury':
                    weight = 0.2  # Price matters least
                else:
                    weight = 0.5  # Balanced

                final_score = price_score * weight + 50 * (1 - weight)

                hotel['ranking_score'] = final_score
                scored_hotels.append(hotel)

            except Exception as e:
                logger.error(f"Error scoring hotel: {e}")
                hotel['ranking_score'] = 0
                scored_hotels.append(hotel)

        # Sort by score
        scored_hotels.sort(key=lambda x: x.get('ranking_score', 0), reverse=True)

        # Return top 5
        return scored_hotels[:5]

    def get_best_hotel(self, search_result: Dict) -> Optional[Dict]:
        """Get the best hotel from search results"""
        hotels = search_result.get('hotels', [])

        if not hotels:
            return None

        # Return highest ranked hotel
        return hotels[0]
