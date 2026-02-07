import React, { useEffect, useState, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  LinearProgress,
  CircularProgress,
  Alert,
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

interface ReplanProgressProps {
  open: boolean;
  jobId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

interface ProgressStep {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
}

const REPLAN_STEPS = [
  'Analyzing preferences',
  'Researching destination',
  'Searching flights',
  'Finding hotels',
  'Building itinerary',
];

const ReplanProgress: React.FC<ReplanProgressProps> = ({ open, jobId, onComplete, onError }) => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState<'in_progress' | 'completed' | 'error'>('in_progress');
  const [errorMessage, setErrorMessage] = useState('');
  const [steps, setSteps] = useState<ProgressStep[]>(
    REPLAN_STEPS.map(name => ({ name, status: 'pending' }))
  );

  // Use ref to track completion synchronously (prevents "Connection lost" flash)
  const isCompletedRef = useRef(false);

  useEffect(() => {
    if (!open || !jobId) return;

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

        // Update steps based on progress percentage
        const currentProgress = data.progress || 0;
        const stepsPercentage = 100 / REPLAN_STEPS.length;
        
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
        if (data.status === 'completed' && data.progress === 100) {
          isCompletedRef.current = true; // Mark as completed IMMEDIATELY
          setSteps(prev => prev.map(step => ({ ...step, status: 'completed' })));
          setTimeout(() => {
            eventSource.close();
            onComplete();
          }, 1500);
        }

        // Handle errors
        if (data.status === 'failed' || data.error_message) {
          const error = data.error_message || 'Trip re-planning failed';
          setErrorMessage(error);
          setStatus('error');
          eventSource.close();
          onError(error);
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
            onError('Connection lost');
          }
        }, 500);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, open, progress, onComplete, onError]);

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
    <Dialog open={open} maxWidth="sm" fullWidth disableEscapeKeyDown>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <span>Regenerating Trip Plan</span>
          {status === 'in_progress' && (
            <CircularProgress size={24} thickness={4} />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {progress}% Complete
            </Typography>
            {status === 'in_progress' && (
              <Typography 
                variant="caption" 
                color="primary" 
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                <CircularProgress size={12} thickness={6} />
                Processing...
              </Typography>
            )}
          </Box>
        </Box>

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}

        {currentStep && status === 'in_progress' && (
          <Alert 
            severity="info" 
            sx={{ mb: 2 }}
            icon={<CircularProgress size={20} />}
          >
            {currentStep}
          </Alert>
        )}

        {status === 'completed' && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Trip plan regenerated successfully! Redirecting...
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
                <CircularProgress size={16} sx={{ ml: 1 }} />
              )}
            </ListItem>
          ))}
        </List>

        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: 1, 
          mt: 3,
          p: 2,
          bgcolor: 'grey.50',
          borderRadius: 1
        }}>
          {status === 'in_progress' && (
            <CircularProgress size={32} thickness={4} />
          )}
          <Typography 
            variant="caption" 
            color="text.secondary" 
            sx={{ textAlign: 'center' }}
          >
            This usually takes 60-90 seconds. Please don't close this window.
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ReplanProgress;
