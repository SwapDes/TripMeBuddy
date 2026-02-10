import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  Container,
  TextField,
  Button,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Link,
} from '@mui/material';
import { ArrowBack, Email } from '@mui/icons-material';

const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

const ForgotPassword: React.FC = () => {
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setError('');
    setSuccess(false);
    setIsSubmitting(true);

    try {
      console.log('Password reset requested for:', data.email);
      await new Promise(resolve => setTimeout(resolve, 800));
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container maxWidth="sm">
        <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
          <Box sx={{ mb: 3 }}>
            <Link
              component={RouterLink}
              to="/login"
              sx={{ display: 'flex', alignItems: 'center', mb: 2, color: 'text.secondary' }}
              underline="hover"
            >
              <ArrowBack sx={{ mr: 0.5 }} fontSize="small" />
              Back to Login
            </Link>
            
            <Typography variant="h4" component="h1" gutterBottom fontWeight="bold">
              Forgot Password?
            </Typography>
            <Typography variant="body1" color="text.secondary">
              We'll help you reset your password.
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {success ? (
            <Alert severity="info" sx={{ mb: 3 }} icon={<Email />}>
              <Typography variant="body2" gutterBottom>
                <strong>Password Reset Request Received</strong>
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Password reset is currently handled manually. Please contact{' '}
                <strong>support@tripmebuddy.com</strong> with your registered email address and we'll help you reset your password within 24 hours.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Email verification and automated password reset will be available in a future update.
              </Typography>
            </Alert>
          ) : (
            <Box component="form" onSubmit={handleSubmit(onSubmit)}>
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>Manual Password Reset:</strong> Enter your email below and click submit. 
                  You'll receive instructions on how to contact our support team to reset your password.
                </Typography>
              </Alert>

              <TextField
                fullWidth
                label="Email Address"
                type="email"
                margin="normal"
                {...register('email')}
                error={!!errors.email}
                helperText={errors.email?.message}
                disabled={isSubmitting}
                autoComplete="email"
                autoFocus
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                sx={{ mt: 3, mb: 2 }}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <CircularProgress size={24} sx={{ mr: 1 }} color="inherit" />
                    Processing...
                  </>
                ) : (
                  'Request Password Reset'
                )}
              </Button>

              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Remember your password?{' '}
                  <Link component={RouterLink} to="/login" underline="hover">
                    Login
                  </Link>
                </Typography>
              </Box>
            </Box>
          )}

          <Box sx={{ mt: 3, textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              <strong>Need Help?</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              Contact support@tripmebuddy.com for assistance
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

const ForgotPasswordPage = ForgotPassword;
export default ForgotPasswordPage;
