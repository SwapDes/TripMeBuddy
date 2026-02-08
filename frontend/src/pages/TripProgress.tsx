import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  LinearProgress,
  CircularProgress,
  Alert,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  CheckCircle,
  RadioButtonUnchecked,
  Error as ErrorIcon,
} from '@mui/icons-material';

interface ProgressStep {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
}

const TRIP_STEPS = [
  'Analyzing preferences',
  'Researching destination',
  'Searching flights',
  'Finding hotels',
  'Building itinerary',
];

const TripProgress: React.FC = () => {
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState<'in_progress' | 'completed' | 'error'>('in_progress');
  const [errorMessage, setErrorMessage] = useState('');
  const [tripId, setTripId] = useState<number | null>(null);
  const [steps, setSteps] = useState<ProgressStep[]>(
    TRIP_STEPS.map(name => ({ name, status: 'pending' }))
  );

  // Use ref to track completion synchronously (prevents "Connection lost" flash)
  const isCompletedRef = useRef(false);

  useEffect(() => {
    if (!jobId) {
      setErrorMessage('No job ID provided');
      setStatus('error');
      return;
    }

    // Reset completion flag
    isCompletedRef.current = false;

    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_URL}/api/v1/jobs/${jobId}/stream`,
      {
        withCredentials: true,
      }
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE Event:', data);

        setProgress(data.progress || 0);
        setCurrentStep(data.current_step || '');
        setStatus(data.status || 'in_progress');

        if (data.trip_id) {
          setTripId(data.trip_id);
        }

        // Update steps based on progress percentage
        const currentProgress = data.progress || 0;
        const stepsPercentage = 100 / TRIP_STEPS.length;
        
        setSteps(prev => prev.map((step, idx) => {
          const stepThreshold = (idx + 1) * stepsPercentage;
          if (currentProgress >= stepThreshold) {
            return { ...step, status: 'completed' };
          } else if (currentProgress >= idx * stepsPercentage && currentProgress < stepThreshold) {
            return { ...step, status: 'in_progress' };
          }
          return { ...step, status: 'pending' };
        }));

        // Handle completion
        if (data.status === 'completed' && data.progress === 100 && data.trip_id) {
          isCompletedRef.current = true; // Mark as completed IMMEDIATELY
          setSteps(prev => prev.map(step => ({ ...step, status: 'completed' })));
          setTimeout(() => {
            eventSource.close();
            navigate(`/trips/${data.trip_id}`);
          }, 1500);
        }

        // Handle errors
        if (data.status === 'failed' || data.error_message) {
          const error = data.error_message || 'Trip planning failed';
          setErrorMessage(error);
          setStatus('error');
          eventSource.close();
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      eventSource.close();
      
      // Only show error if job hasn't completed (use ref for synchronous check)
      if (!isCompletedRef.current) {
        setTimeout(() => {
          // Double-check with both ref and progress state
          if (!isCompletedRef.current && progress < 100) {
            setErrorMessage('Connection lost. Please refresh to check trip status.');
            setStatus('error');
          }
        }, 500);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [navigate, jobId]);

  const getStepIcon = (step: ProgressStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'in_progress':
        return (
          <Box sx={{ position: 'relative', display: 'inline-flex' }}>
            <CircularProgress size={24} thickness={4} />
          </Box>
        );
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <RadioButtonUnchecked color="disabled" />;
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Typography variant="h4" component="h1">
            Creating Your Trip
          </Typography>
          {status === 'in_progress' && (
            <CircularProgress size={32} thickness={4} />
          )}
        </Box>

        <Box sx={{ mb: 4 }}>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ height: 10, borderRadius: 5 }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
            <Typography variant="body1" color="text.secondary">
              {progress}% Complete
            </Typography>
            {status === 'in_progress' && (
              <Typography 
                variant="body2" 
                color="primary" 
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                <CircularProgress size={16} thickness={6} />
                Processing...
              </Typography>
            )}
          </Box>
        </Box>

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {errorMessage}
            {tripId && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2">
                  Your trip may have been partially created.{' '}
                  <a href={`/trips/${tripId}`}>View trip details</a>
                </Typography>
              </Box>
            )}
          </Alert>
        )}

        {currentStep && status === 'in_progress' && (
          <Alert 
            severity="info" 
            sx={{ mb: 3 }}
            icon={<CircularProgress size={20} />}
          >
            {currentStep}
          </Alert>
        )}

        {status === 'completed' && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Trip created successfully! Redirecting to trip details...
          </Alert>
        )}

        <List>
          {steps.map((step, index) => (
            <ListItem key={index}>
              <ListItemIcon>{getStepIcon(step)}</ListItemIcon>
              <ListItemText
                primary={step.name}
                primaryTypographyProps={{
                  fontWeight: step.status === 'in_progress' ? 'bold' : 'normal',
                  color: step.status === 'completed' ? 'success.main' : 'text.primary',
                }}
              />
              {step.status === 'in_progress' && (
                <CircularProgress size={20} sx={{ ml: 1 }} />
              )}
            </ListItem>
          ))}
        </List>

        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: 1.5, 
          mt: 4,
          p: 3,
          bgcolor: 'grey.50',
          borderRadius: 2
        }}>
          {status === 'in_progress' && (
            <CircularProgress size={40} thickness={4} />
          )}
          <Typography 
            variant="body2" 
            color="text.secondary" 
            sx={{ textAlign: 'center' }}
          >
            This usually takes 60-90 seconds. Please don't close this page.
          </Typography>
          <Typography 
            variant="caption" 
            color="text.secondary" 
            sx={{ textAlign: 'center', fontStyle: 'italic' }}
          >
            We're searching for the best flights, hotels, and creating a personalized itinerary for you.
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default TripProgress;
