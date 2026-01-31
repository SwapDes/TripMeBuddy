import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SendIcon from '@mui/icons-material/Send';
import tripService from '../services/tripService';

const NewTrip: React.FC = () => {
  const navigate = useNavigate();
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!request.trim()) {
      setError('Please describe your trip');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await tripService.createTrip({
        request: request.trim(),
      });
      // Response contains job_id, redirect to progress page
      navigate(`/trips/progress/${response.job_id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create trip. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/dashboard');
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
          sx={{ mb: 3 }}
        >
          Back to Dashboard
        </Button>

        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
            Plan Your Trip
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
            Describe your ideal trip in natural language and let AI plan it for you
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              multiline
              rows={6}
              label="Describe Your Trip"
              placeholder="Example: I want to visit Paris for 5 days in June with my family. We love art museums and French cuisine. Our budget is around $5000."
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              disabled={loading}
              sx={{ mb: 3 }}
              helperText="Include destination, dates, budget, travel preferences, number of travelers, and any specific interests"
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                disabled={loading || !request.trim()}
                fullWidth
              >
                {loading ? 'Planning Your Trip...' : 'Plan My Trip'}
              </Button>
            </Box>
          </form>

          <Box sx={{ mt: 4, p: 3, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
              Tips for better results:
            </Typography>
            <Typography variant="body2" component="div">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>Mention your destination and preferred dates</li>
                <li>Specify your budget range and currency</li>
                <li>Include number of travelers</li>
                <li>Share your interests (adventure, culture, food, relaxation, etc.)</li>
                <li>Note any special requirements or preferences</li>
              </ul>
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default NewTrip;
