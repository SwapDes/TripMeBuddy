import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  LinearProgress,
  Paper,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  CheckCircle,
  RadioButtonUnchecked,
  Flight,
  Hotel,
  Map,
  Assessment,
} from '@mui/icons-material';
import config from '../config/config';

interface ProgressUpdate {
  status: string;
  progress: number;
  current_step?: string;
  trip_id?: number;
}

interface Trip {
  id: number;
  created_at: string;
}

const TripProgress: React.FC = () => {
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  
  // Actual progress from backend
  const [targetProgress, setTargetProgress] = useState(0);
  // Displayed progress (animated)
  const [displayProgress, setDisplayProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('Initializing...');
  const [status, setStatus] = useState('pending');
  const [error, setError] = useState<string>('');
  
  // Track which steps should be completed based on progress thresholds
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  // Track which steps are visually shown as completed (with delays)
  const [visualSteps, setVisualSteps] = useState<Set<number>>(new Set());
  
  const animationFrameRef = useRef<number | null>(null);

  const steps = [
    { label: 'Analyzing preferences', threshold: 10, icon: <Assessment /> },
    { label: 'Researching destinations', threshold: 30, icon: <Map /> },
    { label: 'Searching flights', threshold: 50, icon: <Flight /> },
    { label: 'Finding hotels', threshold: 70, icon: <Hotel /> },
    { label: 'Creating itinerary', threshold: 90, icon: <CheckCircle /> },
  ];

  // Animate progress bar smoothly toward target
  useEffect(() => {
    const animate = () => {
      setDisplayProgress((current) => {
        if (Math.abs(current - targetProgress) < 0.5) {
          return targetProgress;
        }
        // Increment by 0.5% per frame (smooth animation)
        const increment = targetProgress > current ? 0.5 : -0.5;
        return current + increment;
      });
    };

    // Animate at 60fps
    const interval = setInterval(animate, 16);
    
    return () => clearInterval(interval);
  }, [targetProgress]);

  // Update completed steps based on DISPLAYED progress thresholds
  useEffect(() => {
    const newCompletedSteps = new Set<number>();
    steps.forEach((step, index) => {
      if (displayProgress >= step.threshold) {
        newCompletedSteps.add(index);
      }
    });
    setCompletedSteps(newCompletedSteps);
  }, [displayProgress]);

  // Smooth visual step completion with 4-second delays
  useEffect(() => {
    if (!completedSteps.size) return;

    // Convert completed steps to sorted array
    const stepsArray = Array.from(completedSteps).sort((a, b) => a - b);

    // Find steps that aren't visually shown yet
    const newSteps = stepsArray.filter(step => !visualSteps.has(step));
    
    if (!newSteps.length) return;

    // Show each new step with 4-second delays
    newSteps.forEach((step, index) => {
      setTimeout(() => {
        setVisualSteps(prev => new Set([...prev, step]));
      }, index * 4000); // 4 seconds between each step
    });
  }, [completedSteps, visualSteps]);

  // Fetch user's latest trip for navigation
  const fetchLatestTrip = async () => {
    try {
      // Get auth token from localStorage (where Keycloak stores it)
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        console.error('No access token found');
        navigate('/dashboard');
        return;
      }
      
      const response = await fetch(`${config.apiBaseUrl}/api/v1/trips`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch trips');
      }
      
      const data = await response.json();
      console.log('Trips response:', data);
      
      // Handle both array and object responses
      const trips: Trip[] = Array.isArray(data) ? data : (data.trips || []);
      
      if (!trips || trips.length === 0) {
        console.log('No trips found, navigating to dashboard');
        navigate('/dashboard');
        return;
      }
      
      // Sort by created_at descending and get the first one
      const latestTrip = trips.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];
      
      console.log('Latest trip:', latestTrip);
      navigate(`/trips/${latestTrip.id}`);
    } catch (err) {
      console.error('Error fetching latest trip:', err);
      navigate('/dashboard');
    }
  };

  // SSE connection for real-time updates
  useEffect(() => {
    if (!jobId) {
      setError('No job ID provided');
      return;
    }

    const eventSource = new EventSource(
      `${config.apiBaseUrl}/api/v1/jobs/${jobId}/stream`,
      { withCredentials: true }
    );

    eventSource.onmessage = (event) => {
      try {
        const data: ProgressUpdate = JSON.parse(event.data);
        
        // Update target progress (will be animated smoothly)
        setTargetProgress(data.progress || 0);
        setCurrentStep(data.current_step || '');
        setStatus(data.status || 'running');

        if (data.status === 'completed') {
          eventSource.close();
          
          // Wait for animations to complete, then fetch and navigate
          setTimeout(() => {
            fetchLatestTrip();
          }, 2000);
        }

        if (data.status === 'failed') {
          eventSource.close();
          setError(data.current_step || 'Trip planning failed');
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      
      // Only show error if job didn't complete successfully
      if (status !== 'completed' && status !== 'failed' && targetProgress < 100) {
        setError('Connection lost. Please check your trip status on the dashboard.');
      }
      
      eventSource.close();
    };

    return () => {
      eventSource.close();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [jobId, navigate, targetProgress, status]);

  const getStepStatus = (index: number) => {
    if (visualSteps.has(index)) return 'completed';
    if (index === visualSteps.size) return 'active';
    return 'pending';
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom align="center">
            Planning Your Perfect Trip
          </Typography>
          
          <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
            Our AI is working on creating your customized itinerary...
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ mb: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {currentStep}
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {Math.round(displayProgress)}%
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={displayProgress} 
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>

          <List>
            {steps.map((step, index) => {
              const stepStatus = getStepStatus(index);
              return (
                <ListItem key={index}>
                  <ListItemIcon>
                    {stepStatus === 'completed' ? (
                      <CheckCircle color="success" />
                    ) : (
                      <RadioButtonUnchecked 
                        color={stepStatus === 'active' ? 'primary' : 'disabled'} 
                      />
                    )}
                  </ListItemIcon>
                  <ListItemText 
                    primary={step.label}
                    primaryTypographyProps={{
                      fontWeight: stepStatus === 'active' ? 'bold' : 'normal',
                      color: stepStatus === 'completed' ? 'success.main' : 
                             stepStatus === 'active' ? 'primary' : 'text.secondary'
                    }}
                  />
                </ListItem>
              );
            })}
          </List>

          {status === 'completed' && displayProgress >= 99 && (
            <Alert severity="success" sx={{ mt: 3 }}>
              Trip planned successfully! Redirecting to your itinerary...
            </Alert>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default TripProgress;
