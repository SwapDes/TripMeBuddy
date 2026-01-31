import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Divider,
  Paper,
} from '@mui/material';
import {
  ArrowBack,
  Star,
  StarBorder,
  Edit,
  Delete,
  CalendarMonth,
  People,
  AttachMoney,
  Flight,
  Hotel,
  Place,
} from '@mui/icons-material';
import tripService from '../services/tripService';
import type { TripDetail } from '../services/tripService';

const TripDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trip, setTrip] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  console.log('TripDetail mounted, id:', id); // DEBUG

  useEffect(() => {
    console.log('useEffect triggered, id:', id); // DEBUG
    
    if (!id) {
      console.log('No id provided'); // DEBUG
      setError('Trip ID not found in URL');
      setLoading(false);
      return;
    }
    
    loadTrip();
  }, [id]);

  const loadTrip = async () => {
    console.log('loadTrip called, id:', id); // DEBUG
    if (!id) {
      console.log('No id, returning'); // DEBUG
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      console.log('Calling tripService.getTrip with ID:', id); // DEBUG
      const data = await tripService.getTrip(parseInt(id));
      console.log('Trip data received:', data); // DEBUG
      setTrip(data);
    } catch (err: any) {
      console.error('Failed to load trip:', err);
      setError('Failed to load trip details. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFavorite = async () => {
    if (!trip) return;
    
    try {
      await tripService.toggleFavorite(trip.id, !trip.is_favorite);
      setTrip({ ...trip, is_favorite: !trip.is_favorite });
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleDelete = async () => {
    if (!trip || !window.confirm('Are you sure you want to delete this trip?')) return;
    
    try {
      await tripService.deleteTrip(trip.id);
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to delete trip:', err);
      setError('Failed to delete trip. Please try again.');
    }
  };

  // Check if trip has fallback destination
  const getFallbackInfo = () => {
    if (!trip) return null;
    
    try {
      const preferences = typeof trip.preferences === 'string'
        ? JSON.parse(trip.preferences)
        : trip.preferences;
      
      const requestedDestination = preferences?.destination_preferences?.[0];
      
      if (requestedDestination && trip.destination !== requestedDestination) {
        const tripPlan = typeof trip.trip_plan === 'string' 
          ? JSON.parse(trip.trip_plan) 
          : trip.trip_plan;
        
        const reasoning = tripPlan?.destination?.reasoning || 
                         `We selected ${trip.destination} as an alternative to provide you with the best travel experience.`;
        
        return {
          requested: requestedDestination,
          selected: trip.destination,
          reasoning: reasoning
        };
      }
    } catch (err) {
      console.error('Error checking fallback:', err);
    }
    
    return null;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'planned': return 'primary';
      case 'booked': return 'success';
      case 'completed': return 'default';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error || !trip) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ mt: 4 }}>
          <Alert severity="error">{error || 'Trip not found'}</Alert>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')} sx={{ mt: 2 }}>
            Back to Dashboard
          </Button>
        </Box>
      </Container>
    );
  }

  const tripPlan = typeof trip.trip_plan === 'string' ? JSON.parse(trip.trip_plan) : trip.trip_plan;
  const tripSummary = tripPlan?.trip_summary || {};
  const destination = tripPlan?.destination || {};
  const flights = tripPlan?.flights || {};
  const hotels = tripPlan?.hotels || {};
  const dailyItinerary = tripPlan?.daily_itinerary || [];
  const fallbackInfo = getFallbackInfo();

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')}>
              Back
            </Button>
            <Typography variant="h4" component="h1" fontWeight="bold">
              {trip.trip_name}
            </Typography>
            <IconButton onClick={handleToggleFavorite}>
              {trip.is_favorite ? <Star color="warning" /> : <StarBorder />}
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<Edit />}>
              Edit
            </Button>
            <Button variant="outlined" color="error" startIcon={<Delete />} onClick={handleDelete}>
              Delete
            </Button>
          </Box>
        </Box>

        {/* Fallback Destination Alert */}
        {fallbackInfo && (
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2" fontWeight="bold" gutterBottom>
              Alternative Destination Selected
            </Typography>
            <Typography variant="body2">
              You originally requested <strong>{fallbackInfo.requested}</strong>, but we selected{' '}
              <strong>{fallbackInfo.selected}</strong> instead.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {fallbackInfo.reasoning}
            </Typography>
          </Alert>
        )}

        {/* Trip Summary Card */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
              <Box>
                <Typography variant="h5" gutterBottom>
                  {trip.destination}
                  {trip.country && `, ${trip.country}`}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip label={trip.status.toUpperCase()} color={getStatusColor(trip.status)} size="small" />
                  {trip.is_booked && <Chip label="BOOKED" color="success" variant="outlined" size="small" />}
                </Box>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CalendarMonth color="action" />
                <Box>
                  <Typography variant="body2" color="text.secondary">Departure</Typography>
                  <Typography variant="body1">{formatDate(trip.departure_date)}</Typography>
                </Box>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CalendarMonth color="action" />
                <Box>
                  <Typography variant="body2" color="text.secondary">Return</Typography>
                  <Typography variant="body1">{formatDate(trip.return_date)}</Typography>
                </Box>
              </Box>

              {trip.duration_days && (
                <Box>
                  <Typography variant="body2" color="text.secondary">Duration</Typography>
                  <Typography variant="body1">{trip.duration_days} days</Typography>
                </Box>
              )}

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <People color="action" />
                <Box>
                  <Typography variant="body2" color="text.secondary">Travelers</Typography>
                  <Typography variant="body1">{trip.travelers_count}</Typography>
                </Box>
              </Box>

              {trip.budget && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AttachMoney color="action" />
                  <Box>
                    <Typography variant="body2" color="text.secondary">Budget</Typography>
                    <Typography variant="body1">
                      {trip.currency} {trip.budget.toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>

        {/* Destination Information */}
        {destination.description && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Place color="primary" />
                <Typography variant="h6">About {destination.city || trip.destination}</Typography>
              </Box>
              <Typography variant="body1" paragraph>
                {destination.description}
              </Typography>
              {destination.highlights && destination.highlights.length > 0 && (
                <>
                  <Typography variant="subtitle2" gutterBottom>Highlights:</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {destination.highlights.map((highlight: string, idx: number) => (
                      <Chip key={idx} label={highlight} size="small" />
                    ))}
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Flights */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Flight color="primary" />
              <Typography variant="h6">Flight Options</Typography>
            </Box>
            {(!flights.flights || flights.flights.length === 0) ? (
              <Alert severity="info">
                {flights.error || flights.message || 'No flight options found. This may be due to limited availability for the selected dates or route.'}
              </Alert>
            ) : (
              <>
                {flights.flights.slice(0, 3).map((flightOffer: any, idx: number) => {
                  // Extract flight details from the Amadeus structure
                  const itinerary = flightOffer.itineraries?.[0];
                  const segment = itinerary?.segments?.[0];
                  const price = flightOffer.price;
                  
                  return (
                    <Paper key={idx} variant="outlined" sx={{ p: 2, mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box>
                          <Typography variant="body1" fontWeight="bold">
                            {segment?.carrierCode || 'Airline'} {segment?.number || ''}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {segment?.departure?.iataCode} → {segment?.arrival?.iataCode}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Duration: {itinerary?.duration || 'N/A'} | Stops: {segment?.numberOfStops || 0}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="h6" color="primary">
                            {price?.currency} {parseFloat(price?.total || 0).toLocaleString()}
                          </Typography>
                          {price?.converted && (
                            <Typography variant="caption" color="text.secondary">
                              ≈ {price.converted.currency} {parseFloat(price.converted.amount || 0).toLocaleString()}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  );
                })}
              </>
            )}
          </CardContent>
        </Card>

        {/* Hotels */}
        {hotels.hotels && hotels.hotels.length > 0 && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Hotel color="primary" />
                <Typography variant="h6">Hotel Options</Typography>
              </Box>
              {hotels.success === false && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  {hotels.message || 'Hotel pricing not available for selected dates. Search booking sites directly for current rates.'}
                </Alert>
              )}
              {hotels.hotels.slice(0, 5).map((hotelItem: any, idx: number) => {
                const hotel = hotelItem.hotel || {};
                const offers = hotelItem.offers || [];
                const firstOffer = offers[0];
                
                return (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body1" fontWeight="bold">
                          {hotel.name || 'Hotel'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {hotel.cityCode || trip.destination}
                        </Typography>
                        {hotel.latitude && hotel.longitude && (
                          <Typography variant="caption" color="text.secondary">
                            Coordinates: {hotel.latitude}, {hotel.longitude}
                          </Typography>
                        )}
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        {firstOffer?.price ? (
                          <>
                            <Typography variant="h6" color="primary">
                              {firstOffer.price.currency} {parseFloat(firstOffer.price.total || 0).toLocaleString()}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Total for stay
                            </Typography>
                          </>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            Check booking sites
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </Paper>
                );
              })}
            </CardContent>
          </Card>
        )}

        {/* Daily Itinerary */}
        {dailyItinerary.length > 0 && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Daily Itinerary</Typography>
              {dailyItinerary.map((day: any, idx: number) => (
                <Box key={idx} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Day {day.day} - {day.location}
                  </Typography>
                  {day.activities && day.activities.length > 0 && (
                    <Box sx={{ ml: 2 }}>
                      {day.activities.map((activity: any, actIdx: number) => (
                        <Box key={actIdx} sx={{ mb: 1 }}>
                          <Typography variant="body2" fontWeight="medium">
                            {activity.time}: {activity.title}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {activity.description}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  )}
                </Box>
              ))}
            </CardContent>
          </Card>
        )}

        {/* User Notes */}
        {trip.user_notes && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Notes</Typography>
              <Typography variant="body1">{trip.user_notes}</Typography>
            </CardContent>
          </Card>
        )}
      </Box>
    </Container>
  );
};

export default TripDetailPage;
