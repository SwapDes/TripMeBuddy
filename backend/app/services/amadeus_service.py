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
        Search for hotel offers by city

        Args:
            city_code: IATA city code (e.g., 'BKK')
            check_in_date: Check-in date in YYYY-MM-DD format
            check_out_date: Check-out date in YYYY-MM-DD format
            adults: Number of adult guests
            radius: Search radius
            radius_unit: Unit for radius (KM or MILE)
            max_results: Maximum number of results

        Returns:
            Dict containing hotel offers
        """
        try:
            logger.info(f"Searching hotels in {city_code}")

            # First, get hotel IDs in the city
            hotels_response = self.client.reference_data.locations.hotels.by_city.get(
                cityCode=city_code,
                radius=radius,
                radiusUnit=radius_unit
            )

            if not hotels_response.data or len(hotels_response.data) == 0:
                logger.info(f"No hotels found in city {city_code}")
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "message": f"No hotels found in city {city_code}"
                }

            # Get hotel IDs (limit to max_results)
            hotel_ids = [hotel['hotelId'] for hotel in hotels_response.data[:max_results]]
            logger.info(f"Found {len(hotel_ids)} hotels in {city_code}")

            # Search for offers for these hotels
            offers_response = self.client.shopping.hotel_offers_search.get(
                hotelIds=','.join(hotel_ids),
                checkInDate=check_in_date,
                checkOutDate=check_out_date,
                adults=adults
            )

            logger.info(f"Hotel search successful: {len(offers_response.data) if offers_response.data else 0} results")
            return {
                "success": True,
                "data": offers_response.data if offers_response.data else [],
                "count": len(offers_response.data) if offers_response.data else 0
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": []
            }

    def search_locations(
            self,
            keyword: str,
            subtype: str = "CITY,AIRPORT",
            max_results: int = 10
    ) -> Dict:
        """
        Search for airports and cities (autocomplete)

        Args:
            keyword: Search keyword
            subtype: Location types to search (CITY, AIRPORT, etc.)
            max_results: Maximum number of results

        Returns:
            Dict containing location suggestions
        """
        try:
            logger.info(f"Searching locations for keyword: {keyword}")
            response = self.client.reference_data.locations.get(
                keyword=keyword,
                subType=subtype,
                page={'limit': max_results}
            )

            # Format response for easier consumption
            locations = []
            if response.data:
                for location in response.data:
                    locations.append({
                        "id": location.get('id'),
                        "name": location.get('name'),
                        "iata_code": location.get('iataCode'),
                        "type": location.get('subType'),
                        "city_name": location.get('address', {}).get('cityName'),
                        "country_name": location.get('address', {}).get('countryName'),
                        "country_code": location.get('address', {}).get('countryCode')
                    })

            logger.info(f"Location search successful: {len(locations)} results")
            return {
                "success": True,
                "data": locations,
                "count": len(locations)
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
        Get price analysis and insights for a route

        Args:
            origin: Origin IATA code
            destination: Destination IATA code
            departure_date: Departure date in YYYY-MM-DD format

        Returns:
            Dict containing price insights
        """
        try:
            logger.info(f"Getting price analysis for {origin} -> {destination}")
            response = self.client.analytics.itinerary_price_metrics.get(
                originIataCode=origin,
                destinationIataCode=destination,
                departureDate=departure_date
            )

            return {
                "success": True,
                "data": response.data if response.data else {},
                "has_data": bool(response.data)
            }

        except ResponseError as error:
            error_details = f"[{error.response.status_code}] {error.response.result if hasattr(error.response, 'result') else error.description}"
            logger.error(f"Amadeus API error: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "data": {}
            }
