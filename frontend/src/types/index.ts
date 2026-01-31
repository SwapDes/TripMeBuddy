// User types
export interface User {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  }
  
  // Trip types
  export interface Trip {
    id: string;
    user_id: string;
    title: string;
    description: string | null;
    natural_language_request: string;
    status: TripStatus;
    destinations: string[];
    start_date: string | null;
    end_date: string | null;
    budget: number | null;
    currency: string | null;
    number_of_travelers: number;
    itinerary: TripItinerary | null;
    created_at: string;
    updated_at: string;
  }
  
  // Trip status types
  export const TripStatus = {
    DRAFT: 'draft',
    PLANNING: 'planning',
    PLANNED: 'planned',
    FAILED: 'failed',
    CANCELLED: 'cancelled'
  } as const;
  
  export type TripStatus = typeof TripStatus[keyof typeof TripStatus];
  
  export interface TripItinerary {
    destinations: DestinationDetail[];
    flights: FlightOption[];
    hotels: HotelOption[];
    daily_plan: DailyPlan[];
    budget_breakdown: BudgetBreakdown;
    planning_notes: string[];
    metadata: ItineraryMetadata;
  }
  
  export interface DestinationDetail {
    city: string;
    country: string;
    airport_code: string;
    description: string;
    highlights: string[];
    best_time_to_visit: string;
    local_tips: string[];
  }
  
  export interface FlightOption {
    id: string;
    departure: FlightSegment;
    arrival: FlightSegment;
    duration: string;
    stops: number;
    price: Price;
    carrier: string;
    booking_link: string | null;
  }
  
  export interface FlightSegment {
    airport_code: string;
    airport_name: string;
    city: string;
    datetime: string;
    terminal: string | null;
  }
  
  export interface HotelOption {
    id: string;
    name: string;
    location: string;
    rating: number | null;
    price_per_night: Price | null;
    total_price: Price | null;
    amenities: string[];
    description: string | null;
    booking_link: string | null;
    check_in: string;
    check_out: string;
  }
  
  export interface Price {
    amount: number;
    currency: string;
    converted_amount?: number;
    converted_currency?: string;
  }
  
  export interface DailyPlan {
    day: number;
    date: string;
    location: string;
    activities: Activity[];
    meals: Meal[];
    notes: string[];
  }
  
  export interface Activity {
    time: string;
    title: string;
    description: string;
    duration: string;
    estimated_cost: Price | null;
  }
  
  export interface Meal {
    time: string;
    type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
    suggestion: string;
    estimated_cost: Price | null;
  }
  
  export interface BudgetBreakdown {
    total: Price;
    flights: Price;
    hotels: Price;
    activities: Price;
    meals: Price;
    contingency: Price;
  }
  
  export interface ItineraryMetadata {
    generated_at: string;
    ai_model: string;
    sources_used: string[];
    confidence_score: number;
  }
  
  // Job tracking types
  export interface JobStatus {
    job_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    progress: number;
    current_step: string | null;
    result: any | null;
    error: string | null;
    created_at: string;
    updated_at: string;
  }
  
  // Request types
  export interface CreateTripRequest {
    natural_language_request: string;
  }
  
  export interface UpdateTripRequest {
    title?: string;
    description?: string;
    status?: TripStatus;
  }
  
  // Response types
  export interface ApiResponse<T> {
    data: T;
    message?: string;
  }
  
  export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }
  
  export interface ErrorResponse {
    detail: string;
    status_code: number;
  }
  
  // Auth types
  export interface LoginRequest {
    email: string;
    password: string;
  }
  
  export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }
  
  export interface RegisterRequest {
    email: string;
    password: string;
    full_name: string;
  }