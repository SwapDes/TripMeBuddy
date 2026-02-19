from typing import Dict, List, Optional
import logging
import json
import re
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class ItineraryBuilderAgent:
    """Genuine ReAct agent to build comprehensive trip itinerary with budget validation."""

    def __init__(self, gemini_api_key: str, currency_service=None, budget_service=None):
        self.currency_service = currency_service
        self.budget_service = budget_service
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key
        )
        tools = self._build_tools()
        self.agent = create_react_agent(self.llm, tools=tools)
        logger.info("ItineraryBuilderAgent initialized")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _build_tools(self):
        currency_service = self.currency_service

        def get_exchange_rate(from_currency: str, to_currency: str) -> float:
            """
            Get the current exchange rate between two currencies.
            Use this when you need to estimate activity or daily costs in the user's
            budget currency but local prices are in a different currency.
            For example, if the user's budget is in INR but destination costs are
            typically quoted in THB or USD, call this to get the conversion rate.
            Returns the rate as a float (1 unit of from_currency = X units of to_currency).
            Returns 1.0 if the currencies are the same or if the rate cannot be fetched.
            """
            if from_currency == to_currency:
                return 1.0
            if not currency_service:
                return 1.0
            try:
                loop = asyncio.new_event_loop()
                try:
                    rate_data = loop.run_until_complete(
                        currency_service.get_exchange_rate(from_currency, to_currency)
                    )
                    if rate_data and rate_data.get("rate"):
                        return float(rate_data["rate"])
                    return 1.0
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"get_exchange_rate tool error: {e}")
                return 1.0

        def validate_budget(
            flights_cost: float,
            hotels_cost: float,
            activities_cost: float,
            total_budget: float,
            currency: str
        ) -> dict:
            """
            Check whether the estimated trip costs are within the user's total budget.
            Call this after estimating all daily costs to confirm whether the activities
            fit within the user's budget, then adjust recommendations if over budget.
            Returns a dict with is_within_budget, variance_percentage, and a recommendation.
            """
            try:
                total_estimated = flights_cost + hotels_cost + activities_cost
                if total_budget <= 0:
                    return {
                        "is_within_budget": True,
                        "total_estimated": round(total_estimated, 2),
                        "total_budget": total_budget,
                        "variance_percentage": 0.0,
                        "recommendation": "No budget specified - costs shown for reference only."
                    }
                variance = total_estimated - total_budget
                variance_pct = (variance / total_budget) * 100
                is_within = abs(variance_pct) <= 10.0
                if variance_pct > 10:
                    recommendation = (
                        f"Estimated cost exceeds budget by {variance_pct:.1f}%. "
                        f"Consider reducing activity spend or choosing lower-cost options."
                    )
                elif variance_pct < -10:
                    recommendation = (
                        f"Estimated cost is {abs(variance_pct):.1f}% under budget. "
                        f"There is room for upgrades or additional experiences."
                    )
                else:
                    recommendation = "Trip is within budget."

                return {
                    "is_within_budget": is_within,
                    "total_estimated": round(total_estimated, 2),
                    "total_budget": round(total_budget, 2),
                    "variance": round(variance, 2),
                    "variance_percentage": round(variance_pct, 1),
                    "currency": currency,
                    "recommendation": recommendation
                }
            except Exception as e:
                logger.warning(f"validate_budget tool error: {e}")
                return {"is_within_budget": True, "recommendation": "Budget validation unavailable."}

        return [
            StructuredTool.from_function(get_exchange_rate),
            StructuredTool.from_function(validate_budget),
        ]

    # ------------------------------------------------------------------
    # Public interface - identical signature to original
    # ------------------------------------------------------------------

    def build(
        self,
        user_request: str,
        preferences: Dict,
        destination: Dict,
        flight_result: Dict,
        hotel_result: Dict,
        budget_allocation: Optional[Dict] = None
    ) -> Dict:
        try:
            logger.info("Building comprehensive trip itinerary")

            best_flight = self._get_best_flight(flight_result)
            best_hotel = self._get_best_hotel(hotel_result)

            daily_itinerary = self._generate_daily_itinerary(
                preferences, destination, budget_allocation
            )

            budget_breakdown = self._calculate_budget_with_validation(
                preferences, best_flight, best_hotel, daily_itinerary, budget_allocation
            )

            planning_notes = self._build_planning_notes(
                preferences, destination, flight_result, hotel_result
            )

            formatted_hotel_alternatives = []
            for h in hotel_result.get("hotels", [])[:5]:
                formatted = self._format_hotel(h)
                if formatted is not None:
                    formatted_hotel_alternatives.append(formatted)

            trip_plan = {
                "trip_summary": {
                    "destination": destination.get("city", "Unknown"),
                    "country": destination.get("country", "Unknown"),
                    "duration_days": preferences.get("duration", {}).get("days", 7),
                    "travel_dates": {
                        "departure": flight_result.get("search_params", {}).get("departure_date"),
                        "return": flight_result.get("search_params", {}).get("return_date")
                    },
                    "travelers": preferences.get("travelers", {}).get("adults", 1),
                    "travel_style": preferences.get("travel_style", "comfort")
                },
                "planning_notes": planning_notes,
                "destination_info": {
                    "description": destination.get("reasoning", ""),
                    "highlights": destination.get("highlights", []),
                    "weather": destination.get("weather_info", ""),
                    "cultural_notes": destination.get("cultural_notes", ""),
                    "visa_requirements": destination.get("visa_requirements", "")
                },
                "transportation": {
                    "outbound_flight": self._format_flight(best_flight) if best_flight else None,
                    "return_flight": self._format_flight(best_flight, is_return=True) if best_flight else None,
                    "flight_alternatives": [self._format_flight(f) for f in flight_result.get("flights", [])[:3]],
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
            return {"success": True, "trip_plan": trip_plan}

        except Exception as e:
            logger.error(f"Itinerary building error: {e}")
            return {"success": False, "error": str(e), "trip_plan": None}

    # ------------------------------------------------------------------
    # ReAct agent - daily itinerary generation
    # ------------------------------------------------------------------

    def _generate_daily_itinerary(
        self,
        preferences: Dict,
        destination: Dict,
        budget_allocation: Optional[Dict]
    ) -> List[Dict]:
        try:
            duration = preferences.get("duration", {}).get("days", 7)
            interests = preferences.get("interests", [])
            user_currency = preferences.get("budget", {}).get("currency", "USD")
            total_budget = preferences.get("budget", {}).get("total", 0)

            messages = [
                SystemMessage(content=self._build_itinerary_system_prompt()),
                HumanMessage(content=self._build_itinerary_task(
                    destination, duration, interests, preferences,
                    user_currency, total_budget, budget_allocation
                )),
            ]

            result = self.agent.invoke({"messages": messages})
            final_text = self._extract_final_text(result["messages"])

            if final_text:
                itinerary = self._parse_itinerary_response(final_text)
                if itinerary:
                    return itinerary

            return self._get_default_itinerary(duration)

        except Exception as e:
            logger.error(f"Error generating daily itinerary: {e}")
            return self._get_default_itinerary(
                preferences.get("duration", {}).get("days", 7)
            )

    def _build_itinerary_system_prompt(self) -> str:
        return (
            "You are an expert travel itinerary planner.\n\n"
            "You have two tools:\n"
            "- get_exchange_rate: call this when you need to convert activity costs "
            "from local currency to the user's budget currency\n"
            "- validate_budget: call this after estimating all daily costs to confirm "
            "whether the activities fit within the user's budget, then adjust if needed\n\n"
            "After using any necessary tools, return ONLY a valid JSON array - "
            "no markdown fences, no code blocks, no explanation text."
        )

    def _build_itinerary_task(
        self,
        destination: Dict,
        duration: int,
        interests: List[str],
        preferences: Dict,
        user_currency: str,
        total_budget: float,
        budget_allocation: Optional[Dict]
    ) -> str:
        activity_budget = ""
        if budget_allocation and budget_allocation.get("components"):
            allocated = budget_allocation["components"].get("activities", {}).get("allocated", 0)
            food_allocated = budget_allocation["components"].get("food", {}).get("allocated", 0)
            activity_budget = (
                f"Activities budget: {allocated} {user_currency}, "
                f"Food budget: {food_allocated} {user_currency}"
            )

        return f"""Create a detailed {duration}-day itinerary for {destination.get('city', 'the destination')}, {destination.get('country', '')}.

Traveler preferences:
- Interests: {', '.join(interests) if interests else 'General sightseeing'}
- Travel style: {preferences.get('travel_style', 'comfort')}
- Budget currency: {user_currency}
- Total budget: {total_budget if total_budget else 'Not specified'} {user_currency}
{activity_budget}

Instructions:
1. If activity costs at the destination are typically in a currency other than {user_currency}, call get_exchange_rate first to get the conversion rate, then use it to estimate costs in {user_currency}
2. Estimate realistic daily costs in {user_currency} for activities, entrance fees, local transport, and food
3. Call validate_budget with your estimated costs to confirm they fit the budget - adjust activity recommendations if over budget
4. Return a JSON array with one object per day

Each day object must have this structure:
{{
  "day": 1,
  "title": "Arrival and First Impressions",
  "activities": [
    {{"time": "Morning", "title": "Activity name", "description": "What to do and why"}},
    {{"time": "Afternoon", "title": "Activity name", "description": "What to do and why"}},
    {{"time": "Evening", "title": "Activity name", "description": "What to do and why"}}
  ],
  "meals": {{"breakfast": "Suggestion", "lunch": "Suggestion", "dinner": "Suggestion"}},
  "estimated_cost": 120,
  "tips": ["Practical tip 1", "Practical tip 2"]
}}

The estimated_cost must be in {user_currency} and cover activities, food, and local transport for that day (not hotel)."""

    # ------------------------------------------------------------------
    # Message extraction
    # ------------------------------------------------------------------

    def _extract_final_text(self, messages: list) -> str:
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue
            content = msg.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
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
    # All methods below are identical to the original
    # ------------------------------------------------------------------

    def _get_best_flight(self, flight_result: Dict) -> Optional[Dict]:
        flights = flight_result.get("flights", [])
        return flights[0] if flights else None

    def _get_best_hotel(self, hotel_result: Dict) -> Optional[Dict]:
        hotels = hotel_result.get("hotels", [])
        for hotel in hotels:
            if hotel.get("offers"):
                return hotel
        return None

    def _format_flight(self, flight: Dict, is_return: bool = False) -> Optional[Dict]:
        if not flight:
            return None
        try:
            price_info = flight.get("price", {})
            itineraries = flight.get("itineraries", [])
            if not itineraries:
                return None
            itinerary = itineraries[1] if is_return and len(itineraries) > 1 else itineraries[0]
            return {
                "price": f"{price_info.get('total', 0)} {price_info.get('currency', 'USD')}",
                "duration": itinerary.get("duration", "N/A"),
                "segments": len(itinerary.get("segments", [])),
                "details": flight
            }
        except Exception as e:
            logger.error(f"Error formatting flight: {e}")
            return {"details": flight}

    def _format_hotel(self, hotel: Dict) -> Optional[Dict]:
        if not hotel:
            return None
        try:
            hotel_info = hotel.get("hotel", {})
            offers = hotel.get("offers", [])
            if not offers:
                return None
            best_offer = offers[0]
            price_info = best_offer.get("price", {})
            return {
                "name": hotel_info.get("name", "Unknown Hotel"),
                "rating": best_offer.get("rating", "N/A"),
                "price_per_night": f"{price_info.get('total', 0)} {price_info.get('currency', 'USD')}",
                "room_type": best_offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard"),
                "address": hotel_info.get("address", {}),
                "details": hotel
            }
        except Exception as e:
            logger.error(f"Error formatting hotel: {e}")
            return None

    def _parse_itinerary_response(self, response_text: str) -> List[Dict]:
        try:
            cleaned = response_text.strip()
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            itinerary = json.loads(cleaned)
            return itinerary if isinstance(itinerary, list) else []
        except Exception as e:
            logger.error(f"Error parsing itinerary: {e}")
            return []

    def _get_default_itinerary(self, days: int) -> List[Dict]:
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
        try:
            user_currency = preferences.get("budget", {}).get("currency", "USD")

            flight_cost = 0
            if best_flight:
                try:
                    price_info = best_flight.get("price", {})
                    converted = price_info.get("converted", {})
                    if converted and converted.get("currency") == user_currency:
                        flight_cost = float(converted.get("amount", 0))
                    else:
                        flight_cost = float(price_info.get("total", 0))
                except Exception as e:
                    logger.error(f"Error extracting flight cost: {e}")

            hotel_cost = 0
            if best_hotel:
                try:
                    offers = best_hotel.get("offers", [])
                    if offers:
                        price_info = offers[0].get("price", {})
                        converted = price_info.get("converted", {})
                        if converted and converted.get("currency") == user_currency:
                            hotel_cost = float(converted.get("amount", 0))
                        else:
                            hotel_cost = float(price_info.get("total", 0))
                except Exception as e:
                    logger.error(f"Error extracting hotel cost: {e}")

            activities_and_food_cost = sum(
                day.get("estimated_cost", 0) for day in daily_itinerary
            )
            total_estimated = flight_cost + hotel_cost + activities_and_food_cost

            budget_breakdown = {
                "flights": round(flight_cost, 2),
                "accommodation": round(hotel_cost, 2),
                "food_and_activities": round(activities_and_food_cost, 2),
                "total_estimated": round(total_estimated, 2),
                "currency": user_currency,
                "budget_level": preferences.get("budget", {}).get("budget_level", "mid-range"),
                "daily_breakdown": [
                    {
                        "day": day.get("day"),
                        "title": day.get("title", f"Day {day.get('day')}"),
                        "estimated_cost": day.get("estimated_cost", 0)
                    }
                    for day in daily_itinerary
                ]
            }

            if budget_allocation:
                validation_result = self._validate_against_budget(
                    budget_allocation=budget_allocation,
                    actual_costs={
                        "flights": flight_cost,
                        "hotels": hotel_cost,
                        "food": activities_and_food_cost * 0.6,
                        "activities": activities_and_food_cost * 0.4
                    }
                )
                budget_breakdown["is_within_budget"] = validation_result.get("is_within_budget")
                budget_breakdown["variance_percentage"] = validation_result.get("variance_percentage")
                budget_breakdown["total_budget"] = validation_result.get("total_budget")
                if validation_result.get("has_disclaimer"):
                    budget_breakdown["budget_disclaimer"] = validation_result.get("disclaimer")

            logger.info(
                f"Budget calculated - Flights: {flight_cost}, Hotels: {hotel_cost}, "
                f"Activities/Food: {activities_and_food_cost}, Total: {total_estimated}"
            )
            return budget_breakdown

        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            return {"total_estimated": 0, "currency": "USD"}

    def _validate_against_budget(self, budget_allocation: Dict, actual_costs: Dict) -> Dict:
        try:
            total_budget = budget_allocation["total_budget"]
            currency = budget_allocation["currency"]
            components = budget_allocation["components"]
            tolerance_percentage = 10.0

            total_actual = sum(actual_costs.values())
            variance = total_actual - total_budget
            variance_pct = (variance / total_budget) * 100

            component_issues = []
            for component, actual_cost in actual_costs.items():
                if component not in components:
                    continue
                allocated = components[component]["allocated"]
                comp_variance = actual_cost - allocated
                comp_variance_pct = (comp_variance / allocated) * 100 if allocated > 0 else 0
                if abs(comp_variance_pct) > tolerance_percentage:
                    component_issues.append({
                        "component": component.capitalize(),
                        "allocated": round(allocated, 2),
                        "actual": round(actual_cost, 2),
                        "variance": round(comp_variance, 2),
                        "variance_pct": round(comp_variance_pct, 1),
                        "over_budget": comp_variance > 0
                    })

            is_within_budget = abs(variance_pct) <= tolerance_percentage
            result = {
                "is_within_budget": is_within_budget,
                "total_budget": round(total_budget, 2),
                "total_actual": round(total_actual, 2),
                "variance": round(variance, 2),
                "variance_percentage": round(variance_pct, 1),
                "currency": currency,
                "component_issues": component_issues,
                "has_disclaimer": not is_within_budget or len(component_issues) > 0
            }
            if result["has_disclaimer"]:
                result["disclaimer"] = self._generate_budget_disclaimer(
                    variance_pct, component_issues, currency
                )
            return result
        except Exception as e:
            logger.error(f"Error validating budget: {e}")
            return {
                "is_within_budget": False,
                "has_disclaimer": True,
                "disclaimer": {
                    "severity": "warning",
                    "message": "Unable to validate budget. Please review costs carefully.",
                    "details": []
                }
            }

    def _generate_budget_disclaimer(self, variance_pct: float, component_issues: list, currency: str) -> Dict:
        severity = "info"
        if abs(variance_pct) > 20:
            severity = "error"
        elif abs(variance_pct) > 10:
            severity = "warning"

        if variance_pct > 0:
            message = f"Trip cost exceeds your budget by {abs(variance_pct):.1f}%"
            details = ["Your estimated total is higher than planned.", "Consider the following options:"]
            for issue in sorted(component_issues, key=lambda x: abs(x["variance"]), reverse=True)[:3]:
                comp_name = issue["component"]
                if issue["over_budget"]:
                    if comp_name == "Hotels":
                        details.append(f"{comp_name}: Consider accommodations in different areas or 3-star alternatives")
                    elif comp_name == "Flights":
                        details.append(f"{comp_name}: Look for flights on different dates or with connections")
                    elif comp_name == "Food":
                        details.append(f"{comp_name}: Try local restaurants and street food instead of tourist areas")
                    elif comp_name == "Activities":
                        details.append(f"{comp_name}: Prioritize must-see attractions and look for free walking tours")
        else:
            message = f"Trip cost is {abs(variance_pct):.1f}% under budget"
            details = ["You have room in your budget for upgrades or additional experiences."]

        return {
            "severity": severity,
            "message": message,
            "details": details,
            "component_breakdown": component_issues
        }

    def _generate_packing_list(self, preferences: Dict, destination: Dict) -> List[str]:
        base_items = [
            "Passport and visa documents",
            "Travel insurance documents",
            "Credit cards and some local currency",
            "Phone and chargers",
            "Medications and prescriptions"
        ]
        destination_type = preferences.get("destination_type", "mixed")
        if "beach" in destination_type:
            base_items.extend(["Swimwear", "Sunscreen", "Beach towel", "Sunglasses"])
        if "mountain" in destination_type or "adventure" in destination_type:
            base_items.extend(["Hiking boots", "Light jacket", "Water bottle"])
        return base_items

    def _generate_travel_tips(self, preferences: Dict, destination: Dict) -> List[str]:
        return [
            "Book attractions and tours in advance during peak season",
            "Download offline maps before arriving",
            "Learn a few basic phrases in the local language",
            "Keep copies of important documents",
            "Stay hydrated and aware of local food safety",
            f"Check weather forecast before departure - {destination.get('weather_info', 'varies')}"
        ]

    def _get_local_transport_tips(self, destination: Dict) -> List[str]:
        return [
            "Use ride-hailing apps for convenience",
            "Public transport is often the most economical option",
            "Consider renting a scooter or car for flexibility",
            "Always agree on taxi fares before starting the journey"
        ]

    def _get_accommodation_tips(self, preferences: Dict, destination: Dict) -> List[str]:
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
        notes = {"defaults_used": [], "limitations": [], "alternatives_available": []}
        if not preferences.get("dates", {}).get("departure"):
            notes["defaults_used"].append(
                f"Travel dates set to 30 days from today "
                f"({flight_result.get('search_params', {}).get('departure_date')}) "
                f"as no specific dates were provided"
            )
        if not hotel_result.get("success"):
            city_code = hotel_result.get("search_params", {}).get("city_code", "destination")
            notes["limitations"].append(
                f"Hotel availability limited in {city_code}. {hotel_result.get('message', '')}"
            )
            notes["alternatives_available"].append(
                "Consider searching hotels directly or specifying an alternative nearby city"
            )
        if not flight_result.get("success"):
            notes["limitations"].append(
                f"Flight search encountered issues: {flight_result.get('error', 'Unknown error')}"
            )
        if not preferences.get("budget", {}).get("total"):
            notes["defaults_used"].append("Budget estimates provided as no specific budget was mentioned")
        return notes

    def _get_emergency_contacts(self, destination: Dict) -> Dict:
        return {
            "emergency_number": "Check local emergency services (911, 112, etc.)",
            "nearest_embassy": f"Contact your embassy in {destination.get('country', 'the destination')}",
            "travel_insurance": "Keep your travel insurance hotline number accessible",
            "local_police": "Note local police station location near your accommodation"
        }
