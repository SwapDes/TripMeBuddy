import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class ItineraryBuilderAgent:
    """Agent to build comprehensive trip itinerary from all gathered information"""

    def __init__(self, gemini_api_key: str):
        """Initialize with Gemini API key"""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        logger.info("ItineraryBuilderAgent initialized")

    def build(
            self,
            user_request: str,
            preferences: Dict,
            destination: Dict,
            flight_result: Dict,
            hotel_result: Dict
    ) -> Dict:
        """
        Build comprehensive trip itinerary

        Args:
            user_request: Original user request
            preferences: Analyzed preferences
            destination: Selected destination
            flight_result: Flight search results
            hotel_result: Hotel search results

        Returns:
            Dict with complete trip plan
        """
        try:
            logger.info("Building comprehensive trip itinerary")

            # Get best options
            best_flight = self._get_best_flight(flight_result)
            best_hotel = self._get_best_hotel(hotel_result)

            # Build day-by-day itinerary using AI
            daily_itinerary = self._generate_daily_itinerary(
                preferences, destination, flight_result, hotel_result
            )

            # Calculate budget breakdown
            budget_breakdown = self._calculate_budget(
                preferences, best_flight, best_hotel, destination
            )

            # Build planning notes for transparency
            planning_notes = self._build_planning_notes(
                preferences, destination, flight_result, hotel_result
            )

            # Compile complete trip plan
            trip_plan = {
                "trip_summary": {
                    "destination": destination.get('city', 'Unknown'),
                    "country": destination.get('country', 'Unknown'),
                    "duration_days": preferences.get('duration', {}).get('days', 7),
                    "travel_dates": {
                        "departure": flight_result.get('search_params', {}).get('departure_date'),
                        "return": flight_result.get('search_params', {}).get('return_date')
                    },
                    "travelers": preferences.get('travelers', {}).get('adults', 1),
                    "travel_style": preferences.get('travel_style', 'comfort')
                },
                "planning_notes": planning_notes,
                "destination_info": {
                    "description": destination.get('reasoning', ''),
                    "highlights": destination.get('highlights', []),
                    "weather": destination.get('weather_info', ''),
                    "cultural_notes": destination.get('cultural_notes', ''),
                    "visa_requirements": destination.get('visa_requirements', '')
                },
                "transportation": {
                    "outbound_flight": self._format_flight(best_flight) if best_flight else None,
                    "return_flight": self._format_flight(best_flight, is_return=True) if best_flight else None,
                    "flight_alternatives": [self._format_flight(f) for f in flight_result.get('flights', [])[:3]],
                    "local_transport_tips": self._get_local_transport_tips(destination)
                },
                "accommodation": {
                    "recommended_hotel": self._format_hotel(best_hotel) if best_hotel else None,
                    "hotel_alternatives": [self._format_hotel(h) for h in hotel_result.get('hotels', [])[:5]],
                    "accommodation_tips": self._get_accommodation_tips(preferences, destination)
                },
                "daily_itinerary": daily_itinerary,
                "budget_breakdown": budget_breakdown,
                "packing_list": self._generate_packing_list(preferences, destination),
                "travel_tips": self._generate_travel_tips(preferences, destination),
                "emergency_contacts": self._get_emergency_contacts(destination)
            }

            logger.info("Trip itinerary built successfully")
            return {
                "success": True,
                "trip_plan": trip_plan
            }

        except Exception as e:
            logger.error(f"Itinerary building error: {e}")
            return {
                "success": False,
                "error": str(e),
                "trip_plan": None
            }

    def _get_best_flight(self, flight_result: Dict) -> Optional[Dict]:
        """Extract best flight from results"""
        flights = flight_result.get('flights', [])
        return flights[0] if flights else None

    def _get_best_hotel(self, hotel_result: Dict) -> Optional[Dict]:
        """Extract best hotel from results"""
        hotels = hotel_result.get('hotels', [])
        return hotels[0] if hotels else None

    def _format_flight(self, flight: Dict, is_return: bool = False) -> Optional[Dict]:
        """Format flight information for display"""
        if not flight:
            return None

        try:
            price_info = flight.get('price', {})

            # Get first itinerary (simplified for now)
            itineraries = flight.get('itineraries', [])
            if not itineraries:
                return None

            itinerary = itineraries[1] if is_return and len(itineraries) > 1 else itineraries[0]

            return {
                "price": f"{price_info.get('total', 0)} {price_info.get('currency', 'USD')}",
                "duration": itinerary.get('duration', 'N/A'),
                "segments": len(itinerary.get('segments', [])),
                "details": flight
            }
        except Exception as e:
            logger.error(f"Error formatting flight: {e}")
            return {"details": flight}

    def _format_hotel(self, hotel: Dict) -> Optional[Dict]:
        """Format hotel information for display"""
        if not hotel:
            return None

        try:
            hotel_info = hotel.get('hotel', {})
            offers = hotel.get('offers', [])

            if not offers:
                return None

            best_offer = offers[0]
            price_info = best_offer.get('price', {})

            return {
                "name": hotel_info.get('name', 'Unknown Hotel'),
                "rating": best_offer.get('rating', 'N/A'),
                "price_per_night": f"{price_info.get('total', 0)} {price_info.get('currency', 'USD')}",
                "room_type": best_offer.get('room', {}).get('typeEstimated', {}).get('category', 'Standard'),
                "address": hotel_info.get('address', {}),
                "details": hotel
            }
        except Exception as e:
            logger.error(f"Error formatting hotel: {e}")
            return {"details": hotel}

    def _generate_daily_itinerary(
            self,
            preferences: Dict,
            destination: Dict,
            flight_result: Dict,
            hotel_result: Dict
    ) -> List[Dict]:
        """Generate AI-powered day-by-day itinerary"""
        try:
            duration = preferences.get('duration', {}).get('days', 7)
            interests = preferences.get('interests', [])

            prompt = f"""Create a detailed day-by-day itinerary for a {duration}-day trip to {destination.get('city', 'the destination')}.

Interests: {', '.join(interests) if interests else 'General sightseeing'}
Travel Style: {preferences.get('travel_style', 'comfort')}

Provide a JSON array (no markdown, no code blocks) with one object per day:
[
  {{
    "day": 1,
    "title": "Arrival and Exploration",
    "activities": [
      {{"time": "Morning", "activity": "Activity description", "location": "Location name"}},
      {{"time": "Afternoon", "activity": "Activity description", "location": "Location name"}},
      {{"time": "Evening", "activity": "Activity description", "location": "Location name"}}
    ],
    "meals": {{"breakfast": "Suggestion", "lunch": "Suggestion", "dinner": "Suggestion"}},
    "estimated_cost": 100,
    "tips": ["Tip 1", "Tip 2"]
  }}
]

Include:
- Realistic timing and pacing
- Mix of activities matching interests
- Restaurant/food recommendations
- Practical tips for each day
- Estimated daily costs"""

            response = self.model.generate_content(prompt)

            if response and response.text:
                itinerary = self._parse_itinerary_response(response.text)
                return itinerary if itinerary else self._get_default_itinerary(duration)

            return self._get_default_itinerary(duration)

        except Exception as e:
            logger.error(f"Error generating daily itinerary: {e}")
            return self._get_default_itinerary(preferences.get('duration', {}).get('days', 7))

    def _parse_itinerary_response(self, response_text: str) -> List[Dict]:
        """Parse AI-generated itinerary"""
        try:
            cleaned = response_text.strip()
            if "```json" in cleaned:
                cleaned = re.search(r'```json\s*(.*?)\s*```', cleaned, re.DOTALL)
                if cleaned:
                    cleaned = cleaned.group(1)
            elif "```" in cleaned:
                cleaned = re.search(r'```\s*(.*?)\s*```', cleaned, re.DOTALL)
                if cleaned:
                    cleaned = cleaned.group(1)

            itinerary = json.loads(cleaned)
            return itinerary if isinstance(itinerary, list) else []

        except Exception as e:
            logger.error(f"Error parsing itinerary: {e}")
            return []

    def _get_default_itinerary(self, days: int) -> List[Dict]:
        """Provide default itinerary structure"""
        return [
            {
                "day": i + 1,
                "title": f"Day {i + 1}",
                "activities": [],
                "meals": {},
                "estimated_cost": 100,
                "tips": []
            }
            for i in range(days)
        ]

    def _calculate_budget(
            self,
            preferences: Dict,
            best_flight: Optional[Dict],
            best_hotel: Optional[Dict],
            destination: Dict
    ) -> Dict:
        """Calculate comprehensive budget breakdown"""
        try:
            # Flight costs
            flight_cost = 0
            if best_flight:
                try:
                    flight_cost = float(best_flight.get('price', {}).get('total', 0))
                except:
                    pass

            # Hotel costs
            hotel_cost = 0
            if best_hotel:
                try:
                    offers = best_hotel.get('offers', [])
                    if offers:
                        hotel_cost = float(offers[0].get('price', {}).get('total', 0))
                except:
                    pass

            # Daily expenses estimate
            duration = preferences.get('duration', {}).get('days', 7)
            daily_cost = destination.get('estimated_daily_cost', 100)
            food_and_activities = daily_cost * duration

            total = flight_cost + hotel_cost + food_and_activities

            return {
                "flights": flight_cost,
                "accommodation": hotel_cost,
                "food_and_activities": food_and_activities,
                "total_estimated": total,
                "currency": "USD",
                "budget_level": preferences.get('budget', {}).get('budget_level', 'mid-range'),
                "notes": "Estimates based on average costs and selected options"
            }

        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            return {"total_estimated": 0, "currency": "USD"}

    def _generate_packing_list(self, preferences: Dict, destination: Dict) -> List[str]:
        """Generate relevant packing list"""
        base_items = [
            "Passport and visa documents",
            "Travel insurance documents",
            "Credit cards and some local currency",
            "Phone and chargers",
            "Medications and prescriptions"
        ]

        destination_type = preferences.get('destination_type', 'mixed')

        if 'beach' in destination_type:
            base_items.extend(["Swimwear", "Sunscreen", "Beach towel", "Sunglasses"])

        if 'mountain' in destination_type or 'adventure' in destination_type:
            base_items.extend(["Hiking boots", "Light jacket", "Water bottle"])

        return base_items

    def _generate_travel_tips(self, preferences: Dict, destination: Dict) -> List[str]:
        """Generate contextual travel tips"""
        return [
            "Book attractions and tours in advance during peak season",
            "Download offline maps before arriving",
            "Learn a few basic phrases in the local language",
            "Keep copies of important documents",
            "Stay hydrated and aware of local food safety",
            f"Check weather forecast before departure - {destination.get('weather_info', 'varies')}"
        ]

    def _get_local_transport_tips(self, destination: Dict) -> List[str]:
        """Get local transportation tips"""
        return [
            "Use ride-hailing apps for convenience",
            "Public transport is often the most economical option",
            "Consider renting a scooter or car for flexibility",
            "Always agree on taxi fares before starting the journey"
        ]

    def _get_accommodation_tips(self, preferences: Dict, destination: Dict) -> List[str]:
        """Get accommodation-specific tips"""
        return [
            "Book accommodations in central locations for easy access",
            "Read recent reviews before booking",
            "Confirm amenities like WiFi, air conditioning before arrival",
            "Consider the neighborhood safety and proximity to attractions"
        ]

    def _build_planning_notes(
            self,
            preferences: Dict,
            destination: Dict,
            flight_result: Dict,
            hotel_result: Dict
    ) -> Dict:
        """Build transparency notes about planning decisions and defaults used"""
        notes = {
            "defaults_used": [],
            "limitations": [],
            "alternatives_available": []
        }

        # Check for date defaults
        if not preferences.get('dates', {}).get('departure'):
            notes["defaults_used"].append(
                f"Travel dates set to 30 days from today ({flight_result.get('search_params', {}).get('departure_date')}) as no specific dates were provided"
            )

        # Check for hotel search issues
        if not hotel_result.get('success'):
            hotel_msg = hotel_result.get('message', '')
            city_code = hotel_result.get('search_params', {}).get('city_code', 'destination')
            notes["limitations"].append(
                f"Hotel availability limited in {city_code}. {hotel_msg}"
            )
            notes["alternatives_available"].append(
                "Consider searching hotels directly or specifying an alternative nearby city"
            )

        # Check for flight search issues
        if not flight_result.get('success'):
            notes["limitations"].append(
                f"Flight search encountered issues: {flight_result.get('error', 'Unknown error')}"
            )

        # Note if budget was not specified
        if not preferences.get('budget', {}).get('total'):
            notes["defaults_used"].append(
                "Budget estimates provided as no specific budget was mentioned"
            )

        # Add alternative destinations if available
        # This would come from the research phase
        notes["alternatives_available"].append(
            "For different experiences, consider exploring alternative destinations or adjusting travel dates"
        )

        return notes

    def _get_emergency_contacts(self, destination: Dict) -> Dict:
        """Provide emergency contact information"""
        return {
            "emergency_number": "Check local emergency services (911, 112, etc.)",
            "nearest_embassy": f"Contact your embassy in {destination.get('country', 'the destination')}",
            "travel_insurance": "Keep your travel insurance hotline number accessible",
            "local_police": "Note local police station location near your accommodation"
        }
