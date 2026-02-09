import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { formatDateForDisplayLong } from '../utils/dateUtils';
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
  List,
  ListItem,
  ListItemText,
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
  WbSunny,
  Language,
  CardTravel,
  Favorite,
  Restaurant,
  Palette,
  AccountBalance,
  Info,
  CheckCircle,
  Warning,
  Lightbulb,
} from '@mui/icons-material';
import tripService from '../services/tripService';
import TripEditModal from '../components/TripEditModal';
import ReplanProgress from '../components/ReplanProgress';
import type { TripReplanRequest } from '../services/tripService';

import type { TripDetail } from '../services/tripService';

const TripDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trip, setTrip] = useState<TripDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [replanProgressOpen, setReplanProgressOpen] = useState(false);
  const [replanJobId, setReplanJobId] = useState<string>('');


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
  const handleEditClick = () => {
    setEditModalOpen(true);
  };

  const handleReplan = async (request: TripReplanRequest) => {
    if (!trip) return;
    
    try {
      setEditModalOpen(false);
      const response = await tripService.replanTrip(trip.id, request);
      setReplanJobId(response.job_id);
      setReplanProgressOpen(true);
    } catch (err: any) {
      console.error('Failed to start replan:', err);
      setError(err.response?.data?.detail || 'Failed to start trip regeneration');
    }
  };

  const handleReplanComplete = () => {
    setReplanProgressOpen(false);
    setReplanJobId('');
    loadTrip(); // Refresh trip data
  };

  const handleReplanError = (errorMsg: string) => {
    setError(errorMsg);
    setReplanProgressOpen(false);
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
        
        const destinationInfo = tripPlan?.trip_plan?.trip_plan?.destination_info || 
                               tripPlan?.trip_plan?.destination_info ||
                               tripPlan?.destination_info;
        
        const reasoning = destinationInfo?.description || 
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'planned': return 'primary';
      case 'booked': return 'success';
      case 'completed': return 'default';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  const getInterestIcon = (interest: string) => {
    const lowerInterest = interest.toLowerCase();
    if (lowerInterest.includes('food') || lowerInterest.includes('culinary')) return <Restaurant />;
    if (lowerInterest.includes('art')) return <Palette />;
    if (lowerInterest.includes('culture') || lowerInterest.includes('history')) return <AccountBalance />;
    return <Favorite />;
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
  
  // Navigate the nested structure: trip_plan.trip_plan.trip_plan
  const actualPlan = tripPlan?.trip_plan?.trip_plan || tripPlan?.trip_plan || tripPlan;
  
  console.log('Full actualPlan:', actualPlan); // DEBUG
  
  const destinationInfo = actualPlan?.destination_info || {};
  const transportation = actualPlan?.transportation || {};
  const accommodation = actualPlan?.accommodation || {};
  
  console.log('Transportation object:', transportation); // DEBUG
  console.log('Accommodation object:', accommodation); // DEBUG
  
  // Flights: outbound, return, and alternatives
  const outboundFlight = transportation?.outbound_flight;
  const returnFlight = transportation?.return_flight;
  const flightAlternatives = transportation?.flight_alternatives || [];
  
  // Hotels: Check both old format (accommodation) and new format (tripPlan.hotels)
  const hotelsData = tripPlan?.hotels || {}; // New format
  const hotelsList = hotelsData?.hotels || []; // Array of hotels from new format
  
  console.log('=== HOTEL DATA EXTRACTION ===');
  console.log('tripPlan.hotels:', tripPlan?.hotels);
  console.log('hotelsList from new format:', hotelsList);
  
  // Old format: accommodation.recommended_hotel and accommodation.hotel_alternatives
  const recommendedHotel = accommodation?.recommended_hotel;
  const oldFormatAlternatives = accommodation?.hotel_alternatives || [];
  
  console.log('accommodation.recommended_hotel:', recommendedHotel);
  console.log('accommodation.hotel_alternatives:', oldFormatAlternatives);
  
  // Combine: use old format if it exists, otherwise use new format
  const hotelAlternatives = oldFormatAlternatives.length > 0 ? oldFormatAlternatives : hotelsList;
  
  console.log('Final hotelAlternatives (using ' + (oldFormatAlternatives.length > 0 ? 'old' : 'new') + ' format):', hotelAlternatives);
  console.log('============================');
  
  console.log('Hotels data (new format):', hotelsData); // DEBUG
  console.log('Hotel alternatives:', hotelAlternatives); // DEBUG
  
  const dailyItinerary = actualPlan?.daily_itinerary || [];
  const planningNotes = actualPlan?.planning_notes || {};
  const budgetBreakdown = actualPlan?.budget_breakdown || {};
  
  console.log('Budget breakdown object:', budgetBreakdown); // DEBUG
  
  // Get preferences
  const preferences = typeof trip.preferences === 'string' 
    ? JSON.parse(trip.preferences) 
    : trip.preferences;

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
            <Button variant="outlined" startIcon={<Edit />} onClick={handleEditClick}>
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
                  <Typography variant="body1">{formatDateForDisplayLong(trip.departure_date)}</Typography>
                </Box>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CalendarMonth color="action" />
                <Box>
                  <Typography variant="body2" color="text.secondary">Return</Typography>
                  <Typography variant="body1">{formatDateForDisplayLong(trip.return_date)}</Typography>
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

        {/* Destination Overview */}
        {destinationInfo.description && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Place color="primary" />
                <Typography variant="h6">Destination Overview</Typography>
              </Box>
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.7 }}>
                {destinationInfo.description}
              </Typography>
              
              {/* Highlights */}
              {destinationInfo.highlights && destinationInfo.highlights.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Must-See Highlights
                  </Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 1 }}>
                    {destinationInfo.highlights.map((highlight: string, idx: number) => (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CheckCircle color="success" fontSize="small" />
                        <Typography variant="body2">{highlight}</Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        )}

        {/* Travel Information (Weather, Visa, Cultural Notes) */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 3, mb: 3 }}>
          {/* Weather */}
          {destinationInfo.weather && (
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <WbSunny color="warning" />
                  <Typography variant="h6">Weather</Typography>
                </Box>
                <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                  {destinationInfo.weather}
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* Visa Requirements */}
          {destinationInfo.visa_requirements && (
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CardTravel color="error" />
                  <Typography variant="h6">Visa</Typography>
                </Box>
                <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                  {destinationInfo.visa_requirements}
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* Cultural Notes */}
          {destinationInfo.cultural_notes && (
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Language color="info" />
                  <Typography variant="h6">Cultural Tips</Typography>
                </Box>
                <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
                  {destinationInfo.cultural_notes}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Box>

        {/* Travel Preferences */}
        {preferences && (preferences.interests || preferences.travel_style || preferences.special_requirements) && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Favorite color="primary" />
                <Typography variant="h6">Your Travel Preferences</Typography>
              </Box>
              
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 3 }}>
                {/* Travel Style */}
                {preferences.travel_style && (
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Travel Style
                    </Typography>
                    <Chip 
                      label={preferences.travel_style.charAt(0).toUpperCase() + preferences.travel_style.slice(1)} 
                      color="primary" 
                      variant="outlined"
                    />
                  </Box>
                )}

                {/* Interests */}
                {preferences.interests && preferences.interests.length > 0 && (
                  <Box sx={{ gridColumn: { xs: '1', sm: 'span 2' } }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Interests
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {preferences.interests.map((interest: string, idx: number) => (
                        <Chip 
                          key={idx}
                          icon={getInterestIcon(interest)}
                          label={interest.charAt(0).toUpperCase() + interest.slice(1)} 
                          size="small"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {/* Special Requirements */}
                {preferences.special_requirements && preferences.special_requirements.length > 0 && (
                  <Box sx={{ gridColumn: '1 / -1' }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Special Requirements
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {preferences.special_requirements.map((req: string, idx: number) => (
                        <Chip 
                          key={idx}
                          label={req.charAt(0).toUpperCase() + req.slice(1)} 
                          size="small"
                          color="warning"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Budget Breakdown */}
        {budgetBreakdown.total_estimated && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <AttachMoney color="primary" />
                <Typography variant="h6">Budget Breakdown</Typography>
              </Box>
              
              {/* Calculate conversion rate - use trip budget vs breakdown total */}
              {(() => {
                // Debug logging
                console.log('Budget currency:', budgetBreakdown.currency);
                console.log('Trip currency:', trip.currency);
                console.log('Trip budget:', trip.budget);
                console.log('Breakdown total:', budgetBreakdown.total_estimated);
                
                // Calculate conversion rate from trip budget and breakdown total
                let conversionRate = 1;
                const shouldConvert = budgetBreakdown.currency !== trip.currency;
                
                if (shouldConvert && trip.budget && budgetBreakdown.total_estimated) {
                  // trip.budget is already a number (in user's currency - INR)
                  // budgetBreakdown.total_estimated is a number (in USD)
                  conversionRate = trip.budget / budgetBreakdown.total_estimated;
                }
                
                console.log('Calculated conversion rate:', conversionRate);
                console.log('Should convert:', shouldConvert);
                
                return (
                  <>
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 2 }}>
                      {budgetBreakdown.flights && (
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Flights
                          </Typography>
                          <Typography variant="h6">
                            {shouldConvert ? trip.currency : budgetBreakdown.currency} {
                              (budgetBreakdown.flights * conversionRate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                            }
                          </Typography>
                        </Box>
                      )}
                      {budgetBreakdown.accommodation && (
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Accommodation
                          </Typography>
                          <Typography variant="h6">
                            {shouldConvert ? trip.currency : budgetBreakdown.currency} {
                              (budgetBreakdown.accommodation * conversionRate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                            }
                          </Typography>
                        </Box>
                      )}
                      {budgetBreakdown.food_and_activities && (
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Food & Activities
                          </Typography>
                          <Typography variant="h6">
                            {shouldConvert ? trip.currency : budgetBreakdown.currency} {
                              (budgetBreakdown.food_and_activities * conversionRate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                            }
                          </Typography>
                        </Box>
                      )}
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Total Estimated
                        </Typography>
                        <Typography variant="h5" color="primary" fontWeight="bold">
                          {shouldConvert ? trip.currency : budgetBreakdown.currency} {
                            (budgetBreakdown.total_estimated * conversionRate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                          }
                        </Typography>
                      </Box>
                    </Box>

                    {shouldConvert && (
                      <Box sx={{ mt: 2, p: 1.5, bgcolor: 'grey.50', borderRadius: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Original amounts in {budgetBreakdown.currency}: {budgetBreakdown.currency} {budgetBreakdown.total_estimated.toLocaleString()}
                        </Typography>
                      </Box>
                    )}
                  </>
                );
              })()}
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
            {(!outboundFlight && flightAlternatives.length === 0) ? (
              <Alert severity="info">
                No flight options found. This may be due to limited availability for the selected dates or route.
              </Alert>
            ) : (
              <>
                {/* Outbound Flight */}
                {outboundFlight && (
                  <>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      Recommended Outbound Flight
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'primary.50' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box>
                          <Typography variant="body1" fontWeight="bold">
                            {outboundFlight.details?.itineraries?.[0]?.segments?.[0]?.carrierCode || 'Airline'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Duration: {outboundFlight.duration || 'N/A'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Segments: {outboundFlight.segments || 'N/A'}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="h6" color="primary">
                            {outboundFlight.price}
                          </Typography>
                          {outboundFlight.details?.price?.converted && (
                            <Typography variant="caption" color="text.secondary">
                              ≈ {outboundFlight.details.price.converted.currency} {
                                parseFloat(outboundFlight.details.price.converted.amount || 0).toLocaleString()
                              }
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  </>
                )}

                {/* Return Flight */}
                {returnFlight && (
                  <>
                    <Typography variant="subtitle2" color="primary" gutterBottom sx={{ mt: 2 }}>
                      Return Flight
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'success.50' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box>
                          <Typography variant="body1" fontWeight="bold">
                            {returnFlight.details?.itineraries?.[1]?.segments?.[0]?.carrierCode || 'Airline'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Duration: {returnFlight.duration || 'N/A'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Segments: {returnFlight.segments || 'N/A'}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="h6" color="success.main">
                            {returnFlight.price}
                          </Typography>
                          {returnFlight.details?.price?.converted && (
                            <Typography variant="caption" color="text.secondary">
                              ≈ {returnFlight.details.price.converted.currency} {
                                parseFloat(returnFlight.details.price.converted.amount || 0).toLocaleString()
                              }
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  </>
                )}

                {/* Flight Alternatives */}
                {flightAlternatives.length > 0 && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                      Alternative Flight Options
                    </Typography>
                    {flightAlternatives
                      .filter((flightOffer: any) => flightOffer !== null && flightOffer !== undefined)
                      .map((flightOffer: any, idx: number) => {
                        const itinerary = flightOffer.details?.itineraries?.[0];
                        const segment = itinerary?.segments?.[0];
                        const price = flightOffer.details?.price;
                      
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
                                Duration: {flightOffer.duration || 'N/A'} | Segments: {flightOffer.segments || 0}
                              </Typography>
                            </Box>
                            <Box sx={{ textAlign: 'right' }}>
                              <Typography variant="h6" color="primary">
                                {flightOffer.price}
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
              </>
            )}
          </CardContent>
        </Card>

        {/* Hotels */}
        {(() => {
          const validHotels = hotelAlternatives.filter((h: any) => h !== null && h !== undefined);
          console.log('=== HOTEL DEBUG ===');
          console.log('Hotel alternatives raw:', hotelAlternatives);
          console.log('Valid hotels after filter:', validHotels);
          console.log('Valid hotels count:', validHotels.length);
          console.log('Recommended hotel:', recommendedHotel);
          console.log('Should render section:', !!(recommendedHotel || validHotels.length > 0));
          console.log('==================');
          
          return (recommendedHotel || validHotels.length > 0) ? (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Hotel color="primary" />
                  <Typography variant="h6">Accommodation Options</Typography>
                </Box>

                {/* Recommended Hotel */}
                {recommendedHotel && (
                  <>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      Recommended Hotel
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'primary.50' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box sx={{ flex: 1 }}>
                          <Typography variant="body1" fontWeight="bold">
                            {recommendedHotel.name || 
                             recommendedHotel.hotel?.name || 
                             recommendedHotel.details?.hotel?.name || 
                             'Recommended Hotel'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {recommendedHotel.hotel?.cityCode || 
                             recommendedHotel.details?.hotel?.cityCode || 
                             trip.destination}
                          </Typography>
                          {(recommendedHotel.offers?.[0]?.room?.description?.text || 
                            recommendedHotel.details?.offers?.[0]?.room?.description?.text) && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                              {(recommendedHotel.offers?.[0]?.room?.description?.text || 
                                recommendedHotel.details?.offers?.[0]?.room?.description?.text || '').split('\n')[0]}
                            </Typography>
                          )}
                        </Box>
                        <Box sx={{ textAlign: 'right', ml: 2 }}>
                          {(recommendedHotel.offers?.[0]?.price || 
                            recommendedHotel.details?.offers?.[0]?.price || 
                            recommendedHotel.price || 
                            recommendedHotel.price_per_night) ? (
                            <>
                              <Typography variant="h6" color="primary">
                                {recommendedHotel.price_per_night || 
                                 `${(recommendedHotel.offers?.[0]?.price?.currency || 
                                     recommendedHotel.details?.offers?.[0]?.price?.currency || '')} ${
                                   parseFloat(recommendedHotel.offers?.[0]?.price?.total || 
                                             recommendedHotel.details?.offers?.[0]?.price?.total || 
                                             recommendedHotel.price || 0).toLocaleString()
                                 }`}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" display="block">
                                Total for stay
                              </Typography>
                              {(recommendedHotel.offers?.[0]?.price?.converted || 
                                recommendedHotel.details?.offers?.[0]?.price?.converted) && (
                                <Typography variant="caption" color="text.secondary">
                                  ≈ {(recommendedHotel.offers?.[0]?.price?.converted?.currency || 
                                      recommendedHotel.details?.offers?.[0]?.price?.converted?.currency)} {
                                    parseFloat(recommendedHotel.offers?.[0]?.price?.converted?.amount || 
                                              recommendedHotel.details?.offers?.[0]?.price?.converted?.amount || 0).toLocaleString()
                                  }
                                </Typography>
                              )}
                            </>
                          ) : (
                            <Typography variant="caption" color="text.secondary">
                              Check booking sites
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  </>
                )}

                {/* Hotel Alternatives */}
                {validHotels.length > 0 && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                      Alternative Hotels
                    </Typography>
                    {validHotels.map((hotelItem: any, idx: number) => {
                      // Support multiple hotel data formats from backend
                      const hotelName = hotelItem.name || // Old format: top-level name
                                       hotelItem.hotel?.name || // New format: nested hotel.name
                                       hotelItem.details?.hotel?.name || // Old format: details.hotel.name
                                       'Hotel';
                      
                      const hotel = hotelItem.hotel || hotelItem.details?.hotel || {};
                      const offers = hotelItem.offers || hotelItem.details?.offers || [];
                      const firstOffer = offers[0];
                      
                      // Price can be at multiple paths
                      const priceInfo = firstOffer?.price || hotelItem.price || null;
                      const pricePerNight = hotelItem.price_per_night; // Old format has this
                    
                    return (
                      <Paper key={idx} variant="outlined" sx={{ p: 2, mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="body1" fontWeight="bold">
                              {hotelName}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {hotel.cityCode || trip.destination}
                            </Typography>
                            {firstOffer?.room?.description?.text && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                {firstOffer.room.description.text.split('\n')[0]}
                              </Typography>
                            )}
                          </Box>
                          <Box sx={{ textAlign: 'right', ml: 2 }}>
                            {priceInfo || pricePerNight ? (
                              <>
                                <Typography variant="h6" color="primary">
                                  {pricePerNight || `${priceInfo.currency} ${parseFloat(priceInfo.total || 0).toLocaleString()}`}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block">
                                  Total for stay
                                </Typography>
                                {priceInfo?.converted && (
                                  <Typography variant="caption" color="text.secondary">
                                    ≈ {priceInfo.converted.currency} {
                                      parseFloat(priceInfo.converted.amount || 0).toLocaleString()
                                    }
                                  </Typography>
                                )}
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
                </>
              )}
            </CardContent>
          </Card>
        ) : null;
        })()}

        {/* Daily Itinerary */}
        {dailyItinerary.length > 0 && (() => {
          // Calculate conversion rate - use trip budget vs breakdown total
          let conversionRate = 1;
          const shouldConvert = budgetBreakdown.currency !== trip.currency;
          
          if (shouldConvert && trip.budget && budgetBreakdown.total_estimated) {
            conversionRate = trip.budget / budgetBreakdown.total_estimated;
          }
          
          return (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Daily Itinerary</Typography>
                {dailyItinerary.map((day: any, idx: number) => {
                  console.log('Day structure:', day); // DEBUG
                  
                  return (
                    <Box key={idx} sx={{ mb: 3, pb: 2, borderBottom: idx < dailyItinerary.length - 1 ? '1px solid #e0e0e0' : 'none' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight="bold">
                          Day {day.day}: {day.title}
                        </Typography>
                        {day.estimated_cost && (
                          <Chip 
                            label={`~${shouldConvert ? trip.currency : budgetBreakdown.currency} ${
                              (day.estimated_cost * conversionRate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                            }`}
                            size="small" 
                            color="primary" 
                            variant="outlined"
                          />
                        )}
                      </Box>
                      
                      {/* Activities - only show if title exists and is not empty */}
                      {day.activities && day.activities.length > 0 && (
                        <Box sx={{ ml: 2, mt: 1 }}>
                          {day.activities
                            .filter((activity: any) => activity.title && activity.title.trim() !== '')
                            .map((activity: any, actIdx: number) => (
                              <Box key={actIdx} sx={{ mb: 1.5 }}>
                                <Typography variant="body2" fontWeight="medium" color="primary">
                                  {activity.time}: {activity.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                                  {activity.description}
                                </Typography>
                              </Box>
                            ))}
                        </Box>
                      )}

                      {/* Meals */}
                      {day.meals && (
                        <Box sx={{ mt: 1.5, ml: 2, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                          <Typography variant="caption" fontWeight="bold" color="text.secondary">
                            Meals
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 0.5 }}>
                            {day.meals.breakfast && (
                              <Typography variant="caption">🍳 {day.meals.breakfast}</Typography>
                            )}
                            {day.meals.lunch && (
                              <Typography variant="caption">🍽️ {day.meals.lunch}</Typography>
                            )}
                            {day.meals.dinner && (
                              <Typography variant="caption">🌙 {day.meals.dinner}</Typography>
                            )}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </CardContent>
            </Card>
          );
        })()}

        {/* Planning Notes */}
        {(planningNotes.defaults_used?.length > 0 || 
          planningNotes.limitations?.length > 0 || 
          planningNotes.alternatives_available?.length > 0) && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Info color="action" />
                <Typography variant="h6">Planning Notes</Typography>
              </Box>

              {planningNotes.defaults_used?.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <CheckCircle color="success" fontSize="small" />
                    <Typography variant="subtitle2" fontWeight="bold">
                      Defaults Applied
                    </Typography>
                  </Box>
                  <List dense>
                    {planningNotes.defaults_used.map((note: string, idx: number) => (
                      <ListItem key={idx} sx={{ py: 0.5 }}>
                        <ListItemText 
                          primary={note}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {planningNotes.limitations?.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Warning color="warning" fontSize="small" />
                    <Typography variant="subtitle2" fontWeight="bold">
                      Limitations
                    </Typography>
                  </Box>
                  <List dense>
                    {planningNotes.limitations.map((note: string, idx: number) => (
                      <ListItem key={idx} sx={{ py: 0.5 }}>
                        <ListItemText 
                          primary={note}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {planningNotes.alternatives_available?.length > 0 && (
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Lightbulb color="info" fontSize="small" />
                    <Typography variant="subtitle2" fontWeight="bold">
                      Alternatives Available
                    </Typography>
                  </Box>
                  <List dense>
                    {planningNotes.alternatives_available.map((note: string, idx: number) => (
                      <ListItem key={idx} sx={{ py: 0.5 }}>
                        <ListItemText 
                          primary={note}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
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

        {/* Edit Modal */}
        {trip && (
          <TripEditModal
            open={editModalOpen}
            trip={trip}
            onClose={() => setEditModalOpen(false)}
            onReplan={handleReplan}
          />
        )}

        {/* Replan Progress Modal */}
        {replanJobId && (
          <ReplanProgress
            open={replanProgressOpen}
            jobId={replanJobId}
            onComplete={handleReplanComplete}
            onError={handleReplanError}
          />
        )}
      </Box>
    </Container>
  );
};

export default TripDetailPage;
