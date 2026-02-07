import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  IconButton,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Close, Add, Remove } from '@mui/icons-material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import type { TripDetail, TripReplanRequest } from '../services/tripService';

interface TripEditModalProps {
  open: boolean;
  trip: TripDetail;
  onClose: () => void;
  onReplan: (request: TripReplanRequest) => void;
}

const CURRENCIES = [
  { code: 'USD', symbol: '$' },
  { code: 'EUR', symbol: '€' },
  { code: 'GBP', symbol: '£' },
  { code: 'INR', symbol: '₹' },
  { code: 'AUD', symbol: 'A$' },
  { code: 'CAD', symbol: 'C$' },
  { code: 'JPY', symbol: '¥' },
];

const TripEditModal: React.FC<TripEditModalProps> = ({ open, trip, onClose, onReplan }) => {
  const [departureDate, setDepartureDate] = useState<Date | null>(
    trip.departure_date ? new Date(trip.departure_date) : null
  );
  const [returnDate, setReturnDate] = useState<Date | null>(
    trip.return_date ? new Date(trip.return_date) : null
  );
  const [travelers, setTravelers] = useState(trip.travelers_count || 1);
  const [budget, setBudget] = useState(trip.budget || 1000);
  const [currency, setCurrency] = useState(trip.currency || 'USD');
  const [destination, setDestination] = useState(trip.destination || '');
  const [origin, setOrigin] = useState(trip.origin || '');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    setError('');

    // Validation
    if (!departureDate || !returnDate) {
      setError('Please select both departure and return dates');
      return;
    }

    if (returnDate <= departureDate) {
      setError('Return date must be after departure date');
      return;
    }

    if (travelers < 1 || travelers > 20) {
      setError('Travelers must be between 1 and 20');
      return;
    }

    if (budget < 100) {
      setError('Budget must be at least 100');
      return;
    }

    if (!destination.trim()) {
      setError('Destination is required');
      return;
    }

    // Build request
    const request: TripReplanRequest = {
      departure_date: departureDate.toISOString().split('T')[0],
      return_date: returnDate.toISOString().split('T')[0],
      travelers_count: travelers,
      budget: budget,
      currency: currency,
      destination: destination.trim(),
      origin: origin.trim() || undefined,
    };

    onReplan(request);
  };

  const getCurrencySymbol = () => {
    return CURRENCIES.find(c => c.code === currency)?.symbol || currency;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Edit Trip: {trip.trip_name}</Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" sx={{ mb: 3 }}>
          Changes will regenerate your trip plan with updated flights, hotels, and itinerary (~90 seconds)
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2 }}>
          {/* Destination */}
          <TextField
            label="Destination"
            fullWidth
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g., Phuket, Paris, Tokyo"
            required
          />

          {/* Origin */}
          <TextField
            label="Origin City"
            fullWidth
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            placeholder="e.g., Mumbai, New York, London"
          />

          {/* Dates */}
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <DatePicker
                label="Departure Date"
                value={departureDate}
                onChange={(date) => setDepartureDate(date)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    required: true,
                  }
                }}
                minDate={new Date()}
              />
              <DatePicker
                label="Return Date"
                value={returnDate}
                onChange={(date) => setReturnDate(date)}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    required: true,
                  }
                }}
                minDate={departureDate || new Date()}
              />
            </Box>
          </LocalizationProvider>

          {/* Travelers */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Travelers
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <IconButton
                onClick={() => setTravelers(Math.max(1, travelers - 1))}
                disabled={travelers <= 1}
                color="primary"
              >
                <Remove />
              </IconButton>
              <TextField
                type="number"
                value={travelers}
                onChange={(e) => setTravelers(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                inputProps={{ min: 1, max: 20 }}
                sx={{ width: 80, textAlign: 'center' }}
              />
              <IconButton
                onClick={() => setTravelers(Math.min(20, travelers + 1))}
                disabled={travelers >= 20}
                color="primary"
              >
                <Add />
              </IconButton>
              <Typography variant="body2" color="text.secondary">
                adults
              </Typography>
            </Box>
          </Box>

          {/* Budget */}
          <Box sx={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 2 }}>
            <TextField
              label="Budget"
              type="number"
              fullWidth
              value={budget}
              onChange={(e) => setBudget(Math.max(0, parseFloat(e.target.value) || 0))}
              InputProps={{
                startAdornment: <InputAdornment position="start">{getCurrencySymbol()}</InputAdornment>,
              }}
              inputProps={{ min: 0, step: 100 }}
              required
            />
            <FormControl fullWidth>
              <InputLabel>Currency</InputLabel>
              <Select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                label="Currency"
              >
                {CURRENCIES.map((curr) => (
                  <MenuItem key={curr.code} value={curr.code}>
                    {curr.code} ({curr.symbol})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Regenerate Plan →
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TripEditModal;
