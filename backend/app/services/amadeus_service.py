from amadeus import Client, ResponseError
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AmadeusService:
    """Service for interacting with Amadeus Self-Service API"""

    def __init__(self, api_key: str, api_secret: str):
        """Initialize Amadeus client"""
        logger.info(f"Initializing Amadeus client (test environment)")

        self.client = Client(
            client_id=api_key,
            client_secret=api_secret,
            hostname='test'  # Use test environment
        )
        logger.info("Amadeus client initialized successfully")

    def search_flights(
            self,
            origin: str,
            destination: str,
            departure_date: str,
            return_date: Optional[str] = None,
            adults: int = 1,
            max_results: int = 10
    ) -> Dict:
        """
        Search for flight offers

        Args:
            origin: IATA code for origin (e.g., 'DEL')
            destination: IATA code for destination (e.g., 'BKK')
            departure_date: Date in YYYY-MM-DD format
            return_date: Optional return date in YYYY-MM-DD format
            adults: Number of adult passengers
            max_results: Maximum number of results to return

        Returns:
            Dict containing flight offers
        """
        try:
            logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")

            # Build params dict, only include returnDate if provided
            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'max': max_results
            }

            # Only add returnDate if it's not None (for round-trip searches)
            if return_date:
                params['returnDate'] = return_date
                logger.info(f"Round-trip search with return date: {return_date}")

            response = self.client.shopping.flight_offers_search.get(**params)

            logger.info(f"Flight search successful: {len(response.data) if response.data else 0} results")
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data) if response.data else 0
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": []
            }

    def search_hotels(
            self,
            city_code: str,
            check_in_date: str,
            check_out_date: str,
            adults: int = 1,
            radius: int = 5,
            radius_unit: str = "KM",
            max_results: int = 10
    ) -> Dict:
        """
        Search for hotel offers by city with improved error handling

        Args:
            city_code: IATA city code (e.g., 'BKK')
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adult guests
            radius: Search radius
            radius_unit: Unit for radius (KM or MILE)
            max_results: Maximum number of results

        Returns:
            Dict containing hotel offers or fallback hotel list
        """
        try:
            logger.info(f"Searching hotels in {city_code}")
            logger.info(f"Dates: {check_in_date} to {check_out_date}, Adults: {adults}")

            # First, get hotel IDs in the city
            hotels_response = self.client.reference_data.locations.hotels.by_city.get(
                cityCode=city_code,
                radius=radius,
                radiusUnit=radius_unit
            )

            if not hotels_response.data or len(hotels_response.data) == 0:
                logger.warning(f"No hotels found in city {city_code}")
                return {
                    "success": False,
                    "data": [],
                    "count": 0,
                    "error": "No hotels found",
                    "message": f"No hotels available in {city_code}. Try a different destination or nearby city."
                }

            # Get hotel IDs (limit to max_results)
            hotel_ids = [hotel['hotelId'] for hotel in hotels_response.data[:max_results]]
            hotel_list = hotels_response.data[:max_results]  # Keep full hotel data
            logger.info(f"Found {len(hotel_ids)} hotels in {city_code}")

            # Search for offers for these hotels
            try:
                offers_response = self.client.shopping.hotel_offers_search.get(
                    hotelIds=','.join(hotel_ids),
                    checkInDate=check_in_date,
                    checkOutDate=check_out_date,
                    adults=adults
                )

                if offers_response.data and len(offers_response.data) > 0:
                    logger.info(f"Hotel search successful: {len(offers_response.data)} results with pricing")
                    return {
                        "success": True,
                        "data": offers_response.data,
                        "count": len(offers_response.data)
                    }
                else:
                    logger.warning(f"No hotel offers available for {check_in_date} to {check_out_date}")
                    # Fall through to fallback below

            except ResponseError as offers_error:
                logger.warning(f"Hotel offers API error: {offers_error.description}")
                # Fall through to fallback below

            # FALLBACK: Return hotel list without pricing when offers unavailable
            logger.info(f"Using fallback: returning hotel list without live pricing")

            # Format hotel list as basic hotel data
            fallback_hotels = []
            for hotel_data in hotel_list[:5]:  # Return top 5
                fallback_hotels.append({
                    "type": "hotel",
                    "hotel": {
                        "hotelId": hotel_data.get("hotelId"),
                        "name": hotel_data.get("name", "Hotel"),
                        "cityCode": city_code,
                        "latitude": hotel_data.get("geoCode", {}).get("latitude"),
                        "longitude": hotel_data.get("geoCode", {}).get("longitude"),
                    },
                    "offers": [],  # No pricing available
                    "available": False,  # Mark as unavailable for these dates
                    "self": f"No live pricing available for {check_in_date}"
                })

            return {
                "success": False,  # Mark as unsuccessful since no offers
                "data": fallback_hotels,
                "count": len(fallback_hotels),
                "error": "No hotel offers found",
                "message": f"Limited hotel availability in {city_code}. Consider nearby cities or adjust search parameters.",
                "search_params": {
                    "city_code": city_code,
                    "check_in": check_in_date,
                    "check_out": check_out_date
                },
                "planning_note": f"Hotels found in {city_code}, but no availability for {check_in_date} to {check_out_date}. This may be due to the date being too far in advance or limited test API data. For actual booking, search closer to travel dates or try booking sites directly."
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": [],
                "count": 0,
                "message": f"Hotel search failed for {city_code}. API error: {error_details}"
            }

        except Exception as e:
            logger.error(f"Unexpected hotel search error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0,
                "message": f"Hotel search failed due to unexpected error: {str(e)}"
            }

    def search_location(self, keyword: str, subtype: str = "CITY,AIRPORT") -> Dict:
        """
        Search for locations (cities/airports) by keyword

        Args:
            keyword: Search keyword (e.g., "Bangkok", "BKK")
            subtype: Type of locations to search (CITY, AIRPORT, etc.)

        Returns:
            Dict containing location search results
        """
        try:
            logger.info(f"Searching locations for keyword: {keyword}")

            response = self.client.reference_data.locations.get(
                keyword=keyword,
                subType=subtype
            )

            logger.info(f"Location search successful: {len(response.data) if response.data else 0} results")
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data) if response.data else 0
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": []
            }

    def get_flight_price_analysis(
            self,
            origin: str,
            destination: str,
            departure_date: str
    ) -> Dict:
        """
        Get flight price analysis and predictions

        Args:
            origin: Origin IATA code
            destination: Destination IATA code
            departure_date: Departure date in YYYY-MM-DD format

        Returns:
            Dict containing price analysis
        """
        try:
            logger.info(f"Getting price analysis: {origin} -> {destination}")

            response = self.client.analytics.itinerary_price_metrics.get(
                originIataCode=origin,
                destinationIataCode=destination,
                departureDate=departure_date
            )

            logger.info("Price analysis successful")
            return {
                "success": True,
                "data": response.data
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": None
            }
