from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class HotelSearchAgent:
    # Agent to search hotels using Amadeus API with currency conversion and budget constraints

    def __init__(self, amadeus_service, currency_service=None):

        self.amadeus = amadeus_service
        self.currency_service = currency_service
        logger.info("HotelSearchAgent initialized")

    def search(
        self,
        preferences: Dict,
        destination: Dict,
        flight_result: Dict,
        budget_allocation: Optional[Dict] = None
    ) -> Dict:

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

            # Extract budget constraint if available
            max_price_per_night = None
            budget_currency = None
            if budget_allocation:
                hotels_budget = budget_allocation.get('components', {}).get('hotels', {})
                max_price_per_night = hotels_budget.get('max_per_night')
                budget_currency = budget_allocation.get('currency')
                if max_price_per_night:
                    logger.info(f"Hotel search constrained to max {budget_currency} {max_price_per_night:.2f} per night")

            logger.info(f"Searching hotels in {city_code}, {check_in} to {check_out}, {adults} adults")

            # Search hotels
            result = self.amadeus.search_hotels(
                city_code=city_code,
                check_in_date=check_in,
                check_out_date=check_out,
                adults=adults,
                radius=10,  # 10 km radius
                radius_unit="KM",
                max_results=30  # Get more results to filter by budget (increased from 20)
            )

            if result.get('data'):
                # Check for success flag or data presence
                success = result.get('success', False)
                
                hotels = result['data']
                
                # Add currency conversion first
                user_currency = preferences.get('budget', {}).get('currency', 'USD')
                if self.currency_service and user_currency:
                    hotels = self._add_currency_conversions(hotels, user_currency)
                
                # Filter by budget if allocation provided
                filtered_count = 0
                planning_note = None
                
                if budget_allocation and max_price_per_night:
                    hotels_before_filter = hotels.copy()
                    hotels = self._filter_by_budget(hotels, max_price_per_night, budget_currency)
                    filtered_count = len(hotels_before_filter) - len(hotels)
                    
                    # Smart fallback: If ALL hotels filtered out, show cheapest 2-3 anyway
                    if len(hotels) == 0 and len(hotels_before_filter) > 0:
                        logger.warning(
                            f"All {len(hotels_before_filter)} hotels exceeded budget "
                            f"of {budget_currency} {max_price_per_night:.0f}/night. "
                            "Showing cheapest options with disclaimer."
                        )
                        
                        # Sort by price and take 2-3 cheapest
                        hotels_sorted = self._sort_hotels_by_price(hotels_before_filter, budget_currency)
                        hotels = hotels_sorted[:min(3, len(hotels_sorted))]
                        filtered_count = len(hotels_before_filter) - len(hotels)
                        
                        planning_note = (
                            f"All available hotels exceed your allocated budget of "
                            f"{budget_currency} {max_price_per_night:.0f} per night. "
                            f"Showing the {len(hotels)} most affordable options. "
                            f"Consider increasing your budget or adjusting travel dates."
                        )
                    elif filtered_count > 0:
                        planning_note = (
                            f"We filtered {filtered_count} hotel options that exceeded your allocated "
                            f"hotel budget of {budget_currency} {max_price_per_night:.0f} per night to show you the best affordable options."
                        )

                # Rank hotels based on preferences
                ranked_hotels = self._rank_hotels(hotels, preferences, budget_allocation)

                return {
                    "success": success,
                    "hotels": ranked_hotels,
                    "search_params": {
                        "city_code": city_code,
                        "check_in": check_in,
                        "check_out": check_out,
                        "adults": adults,
                        "max_price_per_night": max_price_per_night
                    },
                    "count": len(ranked_hotels),
                    "filtered_count": filtered_count,
                    "error": result.get('error'),
                    "message": result.get('message'),
                    "planning_note": planning_note
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

    def _filter_by_budget(
        self,
        hotels: List[Dict],
        max_price_per_night: float,
        currency: str
    ) -> List[Dict]:
        """Filter hotels that exceed nightly budget allocation"""
        
        filtered_hotels = []
        for hotel in hotels:
            try:
                offers = hotel.get('offers', [])
                if not offers:
                    # No offers - skip this hotel
                    continue
                
                # Get price from first offer
                price_info = offers[0].get('price', {})
                converted = price_info.get('converted', {})
                
                # Use converted price if available and in correct currency
                if converted and converted.get('currency') == currency:
                    hotel_price = converted.get('amount', 0)
                else:
                    hotel_price = float(price_info.get('total', 0))
                
                # Check if within budget (allow 30% margin for flexibility)
                if hotel_price <= max_price_per_night * 1.30:
                    filtered_hotels.append(hotel)
                else:
                    logger.debug(
                        f"Filtered hotel {hotel.get('name', 'Unknown')}: "
                        f"{currency} {hotel_price:.2f} exceeds budget {max_price_per_night:.2f}"
                    )
            
            except Exception as e:
                logger.error(f"Error filtering hotel by budget: {e}")
                # Include hotel if we can't determine price
                filtered_hotels.append(hotel)
        
        logger.info(f"Budget filter: {len(filtered_hotels)}/{len(hotels)} hotels within budget")
        return filtered_hotels

    def _sort_hotels_by_price(self, hotels: List[Dict], currency: str) -> List[Dict]:
        """Sort hotels by price (lowest first) for fallback when all exceed budget"""
        
        def get_hotel_price(hotel):
            try:
                offers = hotel.get('offers', [])
                if not offers:
                    return float('inf')  # Hotels without offers go to end
                
                price_info = offers[0].get('price', {})
                converted = price_info.get('converted', {})
                
                if converted and converted.get('currency') == currency:
                    return converted.get('amount', float('inf'))
                else:
                    return float(price_info.get('total', float('inf')))
            except:
                return float('inf')
        
        return sorted(hotels, key=get_hotel_price)

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

    def _rank_hotels(
        self,
        hotels: List[Dict],
        preferences: Dict,
        budget_allocation: Optional[Dict] = None
    ) -> List[Dict]:
        """Rank hotels based on preferences, price, and budget adherence"""

        budget_level = preferences.get('budget', {}).get('budget_level', 'mid-range')
        accommodation_prefs = preferences.get('accommodation_preferences', ['hotel'])

        # Extract prices for normalization
        prices = []
        for hotel in hotels:
            try:
                offers = hotel.get('offers', [])
                if offers:
                    price_info = offers[0].get('price', {})
                    converted = price_info.get('converted', {})
                    if converted and 'amount' in converted:
                        price = float(converted.get('amount', 0))
                    else:
                        price = float(price_info.get('total', 0))
                    
                    if price > 0:
                        prices.append(price)
            except:
                pass

        # Handle hotels without offers (fallback case)
        scored_hotels = []
        for hotel in hotels:
            offers = hotel.get('offers', [])

            if not offers:
                # Hotel has no offers (fallback case) - still include it with low score
                hotel['ranking_score'] = 0
                scored_hotels.append(hotel)
                continue

            try:
                price_info = offers[0].get('price', {})
                converted = price_info.get('converted', {})
                if converted and 'amount' in converted:
                    price = float(converted.get('amount', 0))
                else:
                    price = float(price_info.get('total', 0))

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

                # Bonus for being within budget allocation
                budget_bonus = 0
                if budget_allocation:
                    max_price_per_night = budget_allocation.get('components', {}).get('hotels', {}).get('max_per_night', 0)
                    if max_price_per_night and price <= max_price_per_night:
                        # Give 20 point bonus for being within allocated budget
                        budget_bonus = 20

                # Weight by budget level
                if budget_level == 'budget':
                    weight = 0.8  # Price matters most
                elif budget_level == 'luxury':
                    weight = 0.2  # Price matters least
                else:
                    weight = 0.5  # Balanced

                final_score = (price_score * weight + 50 * (1 - weight)) + budget_bonus

                hotel['ranking_score'] = final_score
                hotel['price_score'] = price_score
                hotel['budget_bonus'] = budget_bonus
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

        # Return highest ranked hotel that has offers
        for hotel in hotels:
            if hotel.get('offers'):
                return hotel
        
        return None
