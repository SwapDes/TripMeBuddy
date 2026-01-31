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

logger = logging.getLogger(__name__)


# Define the state that will be passed between agents
class TripPlannerState(TypedDict):
    """State object that flows through the agent workflow"""
    user_request: str
    preferences: Optional[Dict]
    research_result: Optional[Dict]
    selected_destination: Optional[Dict]
    flight_result: Optional[Dict]
    hotel_result: Optional[Dict]
    final_plan: Optional[Dict]
    error: Optional[str]
    messages: Annotated[list, operator.add]  # Accumulate messages


class TripPlanner:
    """
    LangGraph-based multi-agent trip planner

    Workflow:
    1. PreferencesAnalyzer - Extract structured preferences from natural language
    2. DestinationResearch - Research and recommend destinations
    3. FlightSearch - Search for flights to selected destination
    4. HotelSearch - Search for hotels at destination
    5. ItineraryBuilder - Compile comprehensive trip plan
    """

    def __init__(self, gemini_api_key: str, amadeus_service, redis_client=None):
        """
        Initialize trip planner with all agents

        Args:
            gemini_api_key: Google Gemini API key
            amadeus_service: Instance of AmadeusService
            redis_client: Optional Redis client for caching
        """
        logger.info("Initializing TripPlanner with LangGraph")

        # Initialize CurrencyService with Redis caching
        self.currency_service = CurrencyService(redis_client=redis_client)

        # Initialize all agents with currency service where needed
        self.preferences_agent = PreferencesAnalyzerAgent(
            gemini_api_key=gemini_api_key,
            currency_service=self.currency_service
        )
        self.destination_agent = DestinationResearchAgent(gemini_api_key)
        self.flight_agent = FlightSearchAgent(
            amadeus_service=amadeus_service,
            currency_service=self.currency_service
        )
        self.hotel_agent = HotelSearchAgent(
            amadeus_service=amadeus_service,
            currency_service=self.currency_service
        )
        self.itinerary_agent = ItineraryBuilderAgent(gemini_api_key)

        # Build the workflow graph
        self.workflow = self._build_workflow()

        logger.info("TripPlanner initialized successfully")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""

        # Create state graph
        workflow = StateGraph(TripPlannerState)

        # Add nodes for each agent
        workflow.add_node("analyze_preferences", self._analyze_preferences_node)
        workflow.add_node("research_destinations", self._research_destinations_node)
        workflow.add_node("search_flights", self._search_flights_node)
        workflow.add_node("search_hotels", self._search_hotels_node)
        workflow.add_node("build_itinerary", self._build_itinerary_node)

        # Define the workflow edges (linear flow for now)
        workflow.set_entry_point("analyze_preferences")
        workflow.add_edge("analyze_preferences", "research_destinations")
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

            # Build final response with planning notes and assumptions
            response = {
                "success": True,
                "trip_plan": final_state.get("final_plan"),
                "preferences": final_state.get("preferences"),
                "destination": final_state.get("selected_destination"),
                "flights": final_state.get("flight_result"),
                "hotels": final_state.get("hotel_result"),
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
        """Node: Search flights"""
        logger.info("Node: Searching flights")

        flight_result = self.flight_agent.search(
            state["preferences"],
            state["selected_destination"]
        )

        state["flight_result"] = flight_result

        flight_count = len(flight_result.get("flights", []))
        state["messages"].append(f"Found {flight_count} flight options")

        return state

    def _search_hotels_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Search hotels"""
        logger.info("Node: Searching hotels")

        hotel_result = self.hotel_agent.search(
            state["preferences"],
            state["selected_destination"],
            state["flight_result"]
        )

        state["hotel_result"] = hotel_result

        hotel_count = len(hotel_result.get("hotels", []))
        state["messages"].append(f"Found {hotel_count} hotel options")

        return state

    def _build_itinerary_node(self, state: TripPlannerState) -> TripPlannerState:
        """Node: Build final itinerary"""
        logger.info("Node: Building itinerary")

        final_plan = self.itinerary_agent.build(
            user_request=state["user_request"],
            preferences=state["preferences"],
            destination=state["selected_destination"],
            flight_result=state["flight_result"],
            hotel_result=state["hotel_result"]
        )

        state["final_plan"] = final_plan
        state["messages"].append("Trip itinerary created")

        return state
