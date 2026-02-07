import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class ItineraryBuilderAgent:
    """Agent to build comprehensive trip itinerary with budget validation"""

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
            hotel_result: Dict,
            budget_allocation: Optional[Dict] = None
    ) -> Dict:
        """
        Build comprehensive trip itinerary with budget validation

        Args:
            user_request: Original user request
            preferences: Analyzed preferences
            destination: Selected destination
            flight_result: Flight search results
            hotel_result: Hotel search results
            budget_allocation: Optional budget allocation from BudgetAllocationService

        Returns:
            Dict with complete trip plan including budget validation
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

            # Calculate comprehensive budget breakdown
            budget_breakdown = self._calculate_budget_with_validation(
                preferences,
                best_flight,
                best_hotel,
                daily_itinerary,
                budget_allocation
            )

            # Build planning notes for transparency
            planning_notes = self._build_planning_notes(
                preferences, destination, flight_result, hotel_result
            )

            # Format hotel alternatives - Filter out None values
            formatted_hotel_alternatives = []
            for h in hotel_result.get('hotels', [])[:5]:
                formatted = self._format_hotel(h)
                if formatted is not None:
                    formatted_hotel_alternatives.append(formatted)

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
                    "hotel_alternatives": formatted_hotel_alternatives,
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
        for hotel in hotels:
            if hotel.get('offers'):
                return hotel
        return None

    def _format_flight(self, flight: Dict, is_return: bool = False) -> Optional[Dict]:
        """Format flight information for display"""
        if not flight:
            return None

        try:
            price_info = flight.get('price', {})
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
                logger.info(f"Hotel {hotel_info.get('name', 'Unknown')} has no offers, skipping")
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
            return None

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
User's Budget Currency: {preferences.get('budget', {}).get('currency', 'USD')}

Provide a JSON array (no markdown, no code blocks) with one object per day:
[
  {{
    "day": 1,
    "title": "Arrival and Exploration",
    "activities": [
      {{"time": "Morning", "title": "Activity title", "description": "Activity description"}},
      {{"time": "Afternoon", "title": "Activity title", "description": "Activity description"}},
      {{"time": "Evening", "title": "Activity title", "description": "Activity description"}}
    ],
    "meals": {{"breakfast": "Suggestion", "lunch": "Suggestion", "dinner": "Suggestion"}},
    "estimated_cost": 100,
    "tips": ["Tip 1", "Tip 2"]
  }}
]

CRITICAL COST INSTRUCTIONS:
- estimated_cost MUST be in {preferences.get('budget', {}).get('currency', 'USD')} (user's budget currency)
- This is the DAILY cost for activities, entrance fees, local transport, and food (excluding hotel)
- Be realistic with costs - for example:
  - Budget trip: 50-80 {preferences.get('budget', {}).get('currency', 'USD')} per day
  - Mid-range trip: 80-150 {preferences.get('budget', {}).get('currency', 'USD')} per day
  - Luxury trip: 150-300+ {preferences.get('budget', {}).get('currency', 'USD')} per day
- DO NOT use local currency - use {preferences.get('budget', {}).get('currency', 'USD')} only
- Each activity must have "time", "title", and "description" fields

Include:
- Realistic timing and pacing
- Mix of activities matching interests
- Restaurant/food recommendations
- Practical tips for each day
- Accurate estimated daily costs in {preferences.get('budget', {}).get('currency', 'USD')}"""

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

    def _calculate_budget_with_validation(
            self,
            preferences: Dict,
            best_flight: Optional[Dict],
            best_hotel: Optional[Dict],
            daily_itinerary: List[Dict],
            budget_allocation: Optional[Dict]
    ) -> Dict:
        """
        Calculate comprehensive budget breakdown with validation against user budget
        
        Returns budget breakdown with validation results and disclaimers
        """
        try:
            # Get user currency
            user_currency = preferences.get('budget', {}).get('currency', 'USD')
            
            # Flight costs (for all travelers)
            flight_cost = 0
            if best_flight:
                try:
                    price_info = best_flight.get('price', {})
                    converted = price_info.get('converted', {})
                    if converted and converted.get('currency') == user_currency:
                        flight_cost = float(converted.get('amount', 0))
                    else:
                        flight_cost = float(price_info.get('total', 0))
                except Exception as e:
                    logger.error(f"Error extracting flight cost: {e}")

            # Hotel costs (total for all nights)
            hotel_cost = 0
            if best_hotel:
                try:
                    offers = best_hotel.get('offers', [])
                    if offers:
                        price_info = offers[0].get('price', {})
                        converted = price_info.get('converted', {})
                        if converted and converted.get('currency') == user_currency:
                            hotel_cost = float(converted.get('amount', 0))
                        else:
                            hotel_cost = float(price_info.get('total', 0))
                except Exception as e:
                    logger.error(f"Error extracting hotel cost: {e}")

            # Activities and food costs from daily itinerary
            activities_and_food_cost = sum(
                day.get('estimated_cost', 0) for day in daily_itinerary
            )

            # Total estimated cost
            total_estimated = flight_cost + hotel_cost + activities_and_food_cost

            # Build basic budget breakdown
            budget_breakdown = {
                "flights": round(flight_cost, 2),
                "accommodation": round(hotel_cost, 2),
                "food_and_activities": round(activities_and_food_cost, 2),
                "total_estimated": round(total_estimated, 2),
                "currency": user_currency,
                "budget_level": preferences.get('budget', {}).get('budget_level', 'mid-range'),
                "daily_breakdown": [
                    {
                        "day": day.get('day'),
                        "title": day.get('title', f"Day {day.get('day')}"),
                        "estimated_cost": day.get('estimated_cost', 0)
                    }
                    for day in daily_itinerary
                ]
            }

            # Validate against user budget if provided
            if budget_allocation:
                validation_result = self._validate_against_budget(
                    budget_allocation=budget_allocation,
                    actual_costs={
                        'flights': flight_cost,
                        'hotels': hotel_cost,
                        'food': activities_and_food_cost * 0.6,  # Estimate 60% for food
                        'activities': activities_and_food_cost * 0.4  # Estimate 40% for activities
                    }
                )
                
                # Add validation results directly to budget_breakdown
                budget_breakdown['is_within_budget'] = validation_result.get('is_within_budget')
                budget_breakdown['variance_percentage'] = validation_result.get('variance_percentage')
                budget_breakdown['total_budget'] = validation_result.get('total_budget')
                
                # Add disclaimer if present
                if validation_result.get('has_disclaimer'):
                    budget_breakdown['budget_disclaimer'] = validation_result.get('disclaimer')
                
                logger.info(
                    f"Budget validation - Within budget: {validation_result.get('is_within_budget')}, "
                    f"Variance: {validation_result.get('variance_percentage', 0):.1f}%"
                )

            logger.info(
                f"Budget calculated - Flights: {flight_cost}, Hotels: {hotel_cost}, "
                f"Activities/Food: {activities_and_food_cost}, Total: {total_estimated}"
            )

            return budget_breakdown

        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            return {"total_estimated": 0, "currency": "USD"}

    def _validate_against_budget(
        self,
        budget_allocation: Dict,
        actual_costs: Dict
    ) -> Dict:
        """
        Validate actual costs against allocated budget
        
        Uses BudgetAllocationService logic inline to avoid circular imports
        """
        try:
            total_budget = budget_allocation['total_budget']
            currency = budget_allocation['currency']
            components = budget_allocation['components']
            tolerance_percentage = 10.0

            # Calculate total actual cost
            total_actual = sum(actual_costs.values())
            variance = total_actual - total_budget
            variance_pct = (variance / total_budget) * 100

            # Check per-component variance
            component_issues = []
            for component, actual_cost in actual_costs.items():
                if component not in components:
                    continue

                allocated = components[component]['allocated']
                comp_variance = actual_cost - allocated
                comp_variance_pct = (comp_variance / allocated) * 100 if allocated > 0 else 0

                if abs(comp_variance_pct) > tolerance_percentage:
                    component_issues.append({
                        'component': component.capitalize(),
                        'allocated': round(allocated, 2),
                        'actual': round(actual_cost, 2),
                        'variance': round(comp_variance, 2),
                        'variance_pct': round(comp_variance_pct, 1),
                        'over_budget': comp_variance > 0
                    })

            # Determine if within budget
            is_within_budget = abs(variance_pct) <= tolerance_percentage

            result = {
                'is_within_budget': is_within_budget,
                'total_budget': round(total_budget, 2),
                'total_actual': round(total_actual, 2),
                'variance': round(variance, 2),
                'variance_percentage': round(variance_pct, 1),
                'currency': currency,
                'component_issues': component_issues,
                'has_disclaimer': not is_within_budget or len(component_issues) > 0
            }

            # Generate disclaimer if needed
            if result['has_disclaimer']:
                result['disclaimer'] = self._generate_budget_disclaimer(
                    variance_pct, component_issues, currency
                )

            return result

        except Exception as e:
            logger.error(f"Error validating budget: {e}")
            return {
                'is_within_budget': False,
                'has_disclaimer': True,
                'disclaimer': {
                    'severity': 'warning',
                    'message': 'Unable to validate budget. Please review costs carefully.',
                    'details': []
                }
            }

    def _generate_budget_disclaimer(
        self,
        variance_pct: float,
        component_issues: list,
        currency: str
    ) -> Dict:
        """Generate budget disclaimer with severity and recommendations"""

        severity = 'info'
        if abs(variance_pct) > 20:
            severity = 'error'
        elif abs(variance_pct) > 10:
            severity = 'warning'

        if variance_pct > 0:
            # Over budget
            message = f"⚠️ Trip cost exceeds your budget by {abs(variance_pct):.1f}%"

            if component_issues:
                primary_issue = max(component_issues, key=lambda x: abs(x['variance']))
                reason = f"primarily due to higher {primary_issue['component'].lower()} costs"
            else:
                reason = "across multiple components"

            details = [
                f"Your estimated total is higher than planned {reason}.",
                "Consider the following options:"
            ]

            # Add specific recommendations
            for issue in sorted(component_issues, key=lambda x: abs(x['variance']), reverse=True)[:3]:
                comp_name = issue['component']
                if issue['over_budget']:
                    if comp_name == 'Hotels':
                        details.append(
                            f"• {comp_name}: Consider accommodations in different areas or "
                            f"3-star alternatives (currently {currency} {issue['actual']} vs budgeted {currency} {issue['allocated']})"
                        )
                    elif comp_name == 'Flights':
                        details.append(
                            f"• {comp_name}: Look for flights on different dates or with connections "
                            f"(currently {currency} {issue['actual']} vs budgeted {currency} {issue['allocated']})"
                        )
                    elif comp_name == 'Food':
                        details.append(
                            f"• {comp_name}: Try local restaurants and street food instead of tourist areas"
                        )
                    elif comp_name == 'Activities':
                        details.append(
                            f"• {comp_name}: Prioritize must-see attractions and look for free walking tours"
                        )

            if severity == 'error':
                details.append("We strongly recommend adjusting your selections or increasing your budget.")

        else:
            # Under budget
            message = f"✓ Trip cost is {abs(variance_pct):.1f}% under budget"
            details = [
                f"You have room in your budget for upgrades or additional experiences.",
                "You could consider:"
            ]

            for issue in component_issues:
                if not issue['over_budget']:
                    details.append(f"• Upgrading your {issue['component'].lower()} options")

        return {
            'severity': severity,
            'message': message,
            'details': details,
            'component_breakdown': component_issues
        }

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

        return notes

    def _get_emergency_contacts(self, destination: Dict) -> Dict:
        """Provide emergency contact information"""
        return {
            "emergency_number": "Check local emergency services (911, 112, etc.)",
            "nearest_embassy": f"Contact your embassy in {destination.get('country', 'the destination')}",
            "travel_insurance": "Keep your travel insurance hotline number accessible",
            "local_police": "Note local police station location near your accommodation"
        }
