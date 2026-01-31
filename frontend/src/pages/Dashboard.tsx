import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  FlightTakeoff,
  CalendarMonth,
  People,
  AttachMoney,
  Star,
  StarBorder,
  Visibility,
  Info,
} from '@mui/icons-material';
import tripService from '../services/tripService';
import type { TripSummary } from '../services/tripService';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadTrips();
  }, []);

  const loadTrips = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await tripService.getTrips();
      setTrips(response.trips);
    } catch (err: any) {
      console.error('Failed to load trips:', err);
      setError('Failed to load your trips. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFavorite = async (tripId: number, currentStatus: boolean) => {
    try {
      await tripService.toggleFavorite(tripId, !currentStatus);
      // Update local state
      setTrips((prev) =>
        prev.map((trip) =>
          trip.id === tripId ? { ...trip, is_favorite: !currentStatus } : trip
        )
      );
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleViewTrip = (tripId: number) => {
    navigate(`/trips/${tripId}`);
  };

  // Check if trip has fallback destination
  const hasFallbackDestination = (trip: TripSummary): { hasFallback: boolean; requested?: string } => {
    try {
      // Type assertion: preferences exists in API response but not in TripSummary type
      const tripData = trip as any;
      
      if (!tripData.preferences) {
        return { hasFallback: false };
      }
      
      const preferences = typeof tripData.preferences === 'string' 
        ? JSON.parse(tripData.preferences) 
        : tripData.preferences;
      
      const requestedDestination = preferences?.destination_preferences?.[0];
      
      if (requestedDestination && trip.destination !== requestedDestination) {
        return { hasFallback: true, requested: requestedDestination };
      }
    } catch (err) {
      console.error('Error parsing preferences:', err);
    }
    return { hasFallback: false };
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'planned':
        return 'primary';
      case 'booked':
        return 'success';
      case 'completed':
        return 'default';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
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

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" fontWeight="bold">
            My Trips
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => navigate('/trips/new')}
            startIcon={<FlightTakeoff />}
          >
            Plan New Trip
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {trips.length === 0 ? (
          <Card sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No trips yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Start planning your next adventure with AI-powered travel recommendations!
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={() => navigate('/trips/new')}
              startIcon={<FlightTakeoff />}
            >
              Plan Your First Trip
            </Button>
          </Card>
        ) : (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)',
              },
              gap: 3,
            }}
          >
            {trips.map((trip) => {
              const fallbackInfo = hasFallbackDestination(trip);
              
              return (
                <Card
                  key={trip.id}
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 4,
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                      <Typography variant="h6" component="h2" sx={{ fontWeight: 'bold', flexGrow: 1 }}>
                        {trip.trip_name}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => handleToggleFavorite(trip.id, trip.is_favorite)}
                        sx={{ ml: 1 }}
                      >
                        {trip.is_favorite ? (
                          <Star color="warning" fontSize="small" />
                        ) : (
                          <StarBorder fontSize="small" />
                        )}
                      </IconButton>
                    </Box>

                    <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
                      {trip.destination}
                      {trip.country && `, ${trip.country}`}
                    </Typography>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <CalendarMonth fontSize="small" color="action" />
                      <Typography variant="body2">
                        {formatDate(trip.departure_date)}
                        {trip.return_date && ` - ${formatDate(trip.return_date)}`}
                      </Typography>
                    </Box>

                    {trip.duration_days && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {trip.duration_days} {trip.duration_days === 1 ? 'day' : 'days'}
                      </Typography>
                    )}

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <People fontSize="small" color="action" />
                      <Typography variant="body2">
                        {trip.travelers_count} {trip.travelers_count === 1 ? 'traveler' : 'travelers'}
                      </Typography>
                    </Box>

                    {trip.budget && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                        <AttachMoney fontSize="small" color="action" />
                        <Typography variant="body2">
                          {trip.currency} {trip.budget.toLocaleString()}
                        </Typography>
                      </Box>
                    )}

                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip
                        label={trip.status.charAt(0).toUpperCase() + trip.status.slice(1)}
                        color={getStatusColor(trip.status)}
                        size="small"
                      />
                      {trip.is_booked && (
                        <Chip label="Booked" color="success" variant="outlined" size="small" />
                      )}
                      {fallbackInfo.hasFallback && (
                        <Tooltip title={`Originally requested: ${fallbackInfo.requested}`} arrow>
                          <Chip 
                            icon={<Info fontSize="small" />}
                            label="Alternative destination" 
                            color="info" 
                            variant="outlined" 
                            size="small" 
                          />
                        </Tooltip>
                      )}
                    </Box>
                  </CardContent>

                  <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      fullWidth
                      onClick={() => handleViewTrip(trip.id)}
                      startIcon={<Visibility />}
                    >
                      View Details
                    </Button>
                  </CardActions>
                </Card>
              );
            })}
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default Dashboard;
