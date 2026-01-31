import apiClient from './apiClient';

// Backend trip types (actual API response schema)
export interface TripSummary {
  id: number;
  trip_name: string;
  destination: string;
  country: string | null;
  departure_date: string | null;
  return_date: string | null;
  duration_days: number | null;
  travelers_count: number;
  budget: number | null;
  currency: string;
  is_booked: boolean;
  is_favorite: boolean;
  status: string;
  created_at: string;
}

export interface TripDetail extends TripSummary {
  user_id: string;
  origin: string | null;
  trip_plan: any;
  preferences: any;
  selected_flight: any;
  selected_hotel: any;
  user_notes: string | null;
  updated_at: string | null;
}

interface CreateTripRequest {
  request: string;
  preferences?: Record<string, any>;
}

interface JobResponse {
  job_id: string;
  user_id: number;
  job_type: string;
  status: string;
  progress: number;
  current_step?: string;
  created_at: string;
}

interface TripListResponse {
  trips: TripSummary[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

class TripService {
  /**
   * Get all trips for the current user with optional pagination
   */
  async getTrips(
    page: number = 1,
    pageSize: number = 20,
    statusFilter?: string,
    favoritesOnly?: boolean
  ): Promise<TripListResponse> {
    try {
      const params: any = {
        page,
        page_size: pageSize,
      };

      if (statusFilter) {
        params.status_filter = statusFilter;
      }

      if (favoritesOnly) {
        params.favorites_only = true;
      }

      const response = await apiClient.get<TripListResponse>('/api/v1/trips', { params });
      return response.data;
    } catch (error) {
      console.error('Get trips error:', error);
      throw error;
    }
  }

  /**
   * Get a single trip by ID
   */
  async getTrip(tripId: number): Promise<TripDetail> {
    try {
      const response = await apiClient.get<TripDetail>(`/api/v1/trips/${tripId}`);
      return response.data;
    } catch (error) {
      console.error('Get trip error:', error);
      throw error;
    }
  }

  /**
   * Create a new trip (returns job for async processing)
   */
  async createTrip(tripData: CreateTripRequest): Promise<JobResponse> {
    try {
      const response = await apiClient.post<JobResponse>('/api/v1/jobs/trip-planning', tripData);
      return response.data;
    } catch (error) {
      console.error('Create trip error:', error);
      throw error;
    }
  }

  /**
   * Update an existing trip
   */
  async updateTrip(
    tripId: number,
    tripData: {
      trip_name?: string;
      selected_flight?: any;
      selected_hotel?: any;
      is_booked?: boolean;
      is_favorite?: boolean;
      status?: string;
      user_notes?: string;
    }
  ): Promise<TripDetail> {
    try {
      const response = await apiClient.put<TripDetail>(`/api/v1/trips/${tripId}`, tripData);
      return response.data;
    } catch (error) {
      console.error('Update trip error:', error);
      throw error;
    }
  }

  /**
   * Delete a trip
   */
  async deleteTrip(tripId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/v1/trips/${tripId}`);
    } catch (error) {
      console.error('Delete trip error:', error);
      throw error;
    }
  }

  /**
   * Toggle trip favorite status
   */
  async toggleFavorite(tripId: number, isFavorite: boolean): Promise<TripDetail> {
    try {
      return await this.updateTrip(tripId, { is_favorite: isFavorite });
    } catch (error) {
      console.error('Toggle favorite error:', error);
      throw error;
    }
  }
}

const tripService = new TripService();
export default tripService;
