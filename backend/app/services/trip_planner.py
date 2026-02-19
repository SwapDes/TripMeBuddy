from typing import TypedDict, Annotated, Dict, Optional
from langgraph.graph import StateGraph, END
import logging
import operator

from app.services.agents.preferences_analyzer_agent import PreferencesAnalyzerAgent
from app.services.agents.destination_research_agent import DestinationResearchAgent
from app.services.agents.flight_search_agent import FlightSearchAgent
from app.services.agents.hotel_search_agent import HotelSearchAgent
from app.services.agents.itinerary_builder_agent import ItineraryBuilderAgent
from app.services.currency_service import CurrencyService
from app.services.budget_allocation_service import BudgetAllocationService

logger = logging.getLogger(__name__)


# Define the state that will be passed between agents
class TripPlannerState(TypedDict):
    """State object that flows through the agent workflow"""
    user_request: str
    preferences: Optional[Dict]
    budget_allocation: Optional[Dict]
    research_result: Optional[Dict]
    selected_destination: Optional[Dict]
    flight_result: Optional[Dict]
    hotel_result: Optional[Dict]
    final_plan: Optional[Dict]
    error: Optional[str]
    messages: Annotated[list, operator.add]  # Accumulate messages


class TripPlanner:
    """
    LangGraph-based multi-agent trip planner with budget management

    Workflow:
    1. PreferencesAnalyzer - Extract structured preferences from natural language
    2. BudgetAllocator - Allocate budget across components (if budget specified)
    3. DestinationResearch - Research and recommend destinations
    4. FlightSearch - Search for flights with budget constraints
    5. HotelSearch - Search for hotels with budget constraints
    6. ItineraryBuilder - Compile comprehensive trip plan with budget validation
    """

    def __init__(self, gemini_api_key: str, amadeus_service, redis_client=None):
        """
        Initialize trip planner with all agents and budget service

        Args:
            gemini_api_key: Google Gemini API key
            amadeus_service: Instance of AmadeusService
            redis_client: Optional Redis client for caching
        """
        logger.info("Initializing TripPlanner with LangGraph and Budget Management")

        # Initialize CurrencyService with Redis caching
        self.currency_service = CurrencyService(redis_client=redis_client)
        
        # Initialize BudgetAllocationService
        self.budget_service = BudgetAllocationService()

        # Initialize all agents
        self.preferences_agent = PreferencesAnalyzerAgent(
            gemini_api_key=gemini_api_key,
            currency_service=self.currency_service
        )
        self.destination_agent = DestinationResearchAgent(
            gemini_api_key=gemini_api_key,
            amadeus_service=amadeus_service
        )
        self.flight_agent = FlightSearchAgent(
            amadeus_service=amadeus_service,
            currency_service=self.currency_service
        )
        self.hotel_agent = HotelSearchAgent(
            amadeus_service=amadeus_service,
            currency_service=self.currency_service
        )

        self.itinerary_agent = ItineraryBuilderAgent(
            gemini_api_key=gemini_api_key,
            currency_service=self.currency_service,
            budget_service=self.budget_service
        )

        # Build the workflow graph
        self.workflow = self._build_workflow()

        logger.info("TripPlanner initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with budget allocation"""

        # Create state graph
        workflow = StateGraph(TripPlannerState)

        # Add nodes for each agent
        workflow.add_node("analyze_preferences", self._analyze_preferences_node)
        workflow.add_node("allocate_budget", self._allocate_budget_node)
        workflow.add_node("research_destinations", self._research_destinations_node)
        workflow.add_node("search_flights", self._search_flights_node)
        workflow.add_node("search_hotels", self._search_hotels_node)
        workflow.add_node("build_itinerary", self._build_itinerary_node)

        # Define the workflow edges
        workflow.set_entry_point("analyze_preferences")
        workflow.add_edge("analyze_preferences", "allocate_budget")
        workflow.add_edge("allocate_budget", "research_destinations")
        workflow.add_edge("research_destinations", "search_flights")
        workflow.add_edge("search_flights", "search_hotels")
        workflow.add_edge("search_hotels", "build_itinerary")
        workflow.add_edge("build_itinerary", END)

        # Compile the workflow
        return workflow.compile()

    def plan_trip(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """
        Execute the complete trip planning workflow

        Args:
            user_request: Natural language trip request
            context: Optional additional context

        Returns:
            Dict with complete trip plan
        """
        try:
            logger.info(f"Starting trip planning workflow for request: {user_request[:100]}...")

            # Initialize state
            initial_state = {
                "user_request": user_request,
                "preferences": None,
                "budget_allocation": None,
                "research_result": None,
                "selected_destination": None,
                "flight_result": None,
                "hotel_result": None,
                "final_plan": None,
                "error": None,
                "messages": []
            }

            # Execute workflow
            final_state = self.workflow.invoke(initial_state)

            # Build final response
            response = {
                "success": True,
                "trip_plan": final_state.get("final_plan"),
                "preferences": final_state.get("preferences"),
                "destination": final_state.get("selected_destination"),
                "flights": final_state.get("flight_result"),
                "hotels": final_state.get("hotel_result"),
                "budget_allocation": final_state.get("budget_allocation"),
                "messages": final_state.get("messages", [])
            }

            # Extract assumptions from preferences
            preferences = final_state.get("preferences", {})
            assumptions = preferences.get("_assumptions", [])

            if assumptions:
                response["planning_notes"] = assumptions
                response["assumptions"] = {
                    "extraction": assumptions
                }

            logger.info("Trip planning completed successfully")
            return response

        except Exception as e:
            logger.error(f"Trip planning error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "messages": [f"Error: {str(e)}"]
            }

    # Node implementations

    def _analyze_preferences_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Analyze user preferences"""
        logger.info("Node: Analyzing preferences")

        import asyncio

        # Run async analyze method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            preferences = loop.run_until_complete(
                self.preferences_agent.analyze(state["user_request"])
            )
        finally:
            loop.close()

        state["preferences"] = preferences
        state["messages"].append("Analyzed travel preferences")
        return state

    def _allocate_budget_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Allocate budget across trip components"""
        logger.info("Node: Allocating budget")

        preferences = state["preferences"]
        budget_info = preferences.get('budget', {})
        
        # Only allocate if user provided a budget
        total_budget = budget_info.get('total')
        if not total_budget or total_budget <= 0:
            logger.info("No budget specified, skipping budget allocation")
            state["messages"].append("No budget specified - estimates will be provided")
            return state

        try:
            # Extract parameters for budget allocation
            currency = budget_info.get('currency', 'USD')
            duration_days = preferences.get('duration', {}).get('days', 7)
            travelers_count = preferences.get('travelers', {}).get('adults', 1)
            travel_style = preferences.get('travel_style', 'comfort')
            destination_type = preferences.get('destination_type', 'city')

            # Allocate budget
            budget_allocation = self.budget_service.allocate_budget(
                total_budget=total_budget,
                currency=currency,
                duration_days=duration_days,
                travelers_count=travelers_count,
                travel_style=travel_style,
                destination_type=destination_type
            )

            state["budget_allocation"] = budget_allocation
            state["messages"].append(f"Budget allocated: {currency} {total_budget}")
            
            logger.info(
                f"Budget allocated - Flights: {budget_allocation['components']['flights']['allocated']}, "
                f"Hotels: {budget_allocation['components']['hotels']['allocated']}"
            )

        except Exception as e:
            logger.error(f"Error allocating budget: {e}")
            state["messages"].append("Budget allocation failed - continuing without constraints")

        return state

    def _research_destinations_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Research destinations"""
        logger.info("Node: Researching destinations")

        research_result = self.destination_agent.research(state["preferences"])

        state["research_result"] = research_result

        # Select best destination
        selected_destination = self.destination_agent.select_best_destination(research_result)

        if not selected_destination:
            state["messages"].append("No suitable destinations found")
            return state

        state["selected_destination"] = selected_destination
        state["messages"].append(f"Selected destination: {selected_destination.get('city', 'Unknown')}")

        return state

    def _search_flights_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Search flights with budget constraints"""
        logger.info("Node: Searching flights")

        flight_result = self.flight_agent.search(
            preferences=state["preferences"],
            destination=state["selected_destination"],
            budget_allocation=state.get("budget_allocation")
        )

        state["flight_result"] = flight_result

        if flight_result.get('success'):
            count = flight_result.get('count', 0)
            state["messages"].append(f"Found {count} flight options")
        else:
            state["messages"].append(f"Flight search issue: {flight_result.get('error', 'Unknown')}")

        return state

    def _search_hotels_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Search hotels with budget constraints"""
        logger.info("Node: Searching hotels")

        hotel_result = self.hotel_agent.search(
            preferences=state["preferences"],
            destination=state["selected_destination"],
            flight_result=state["flight_result"],
            budget_allocation=state.get("budget_allocation")
        )

        state["hotel_result"] = hotel_result

        if hotel_result.get('success'):
            count = hotel_result.get('count', 0)
            state["messages"].append(f"Found {count} hotel options")
        else:
            state["messages"].append(f"Hotel search issue: {hotel_result.get('error', 'Unknown')}")

        return state

    def _build_itinerary_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Build comprehensive itinerary with budget validation"""
        logger.info("Node: Building itinerary")

        itinerary_result = self.itinerary_agent.build(
            user_request=state["user_request"],
            preferences=state["preferences"],
            destination=state["selected_destination"],
            flight_result=state["flight_result"],
            hotel_result=state["hotel_result"],
            budget_allocation=state.get("budget_allocation")
        )

        if itinerary_result.get('success'):
            state["final_plan"] = itinerary_result.get('trip_plan')
            state["messages"].append("Complete trip plan generated")
        else:
            state["error"] = itinerary_result.get('error')
            state["messages"].append(f"Itinerary building failed: {state['error']}")

        return state
