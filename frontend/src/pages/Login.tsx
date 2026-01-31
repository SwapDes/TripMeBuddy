import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import { useAuth } from '../context/AuthContext';

// Validation schema
const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setError('');
    setIsSubmitting(true);

    try {
      await login(data.email, data.password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
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
          <Box sx={{ mb: 3, textAlign: 'center' }}>
            <Typography variant="h4" component="h1" gutterBottom fontWeight="bold">
              Trip Me Buddy
            </Typography>
            <Typography variant="body1" color="text.secondary">
              AI-Powered Travel Planning
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Box>
            <TextField
              fullWidth
              label="Email"
              type="email"
              margin="normal"
              {...register('email')}
              error={!!errors.email}
              helperText={errors.email?.message}
              disabled={isSubmitting}
            />

            <TextField
              fullWidth
              label="Password"
              type="password"
              margin="normal"
              {...register('password')}
              error={!!errors.password}
              helperText={errors.password?.message}
              disabled={isSubmitting}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSubmit(onSubmit)();
                }
              }}
            />

            <Button
              type="button"
              fullWidth
              variant="contained"
              size="large"
              sx={{ mt: 3, mb: 2 }}
              disabled={isSubmitting}
              onClick={handleSubmit(onSubmit)}
            >
              {isSubmitting ? (
                <>
                  <CircularProgress size={24} sx={{ mr: 1 }} color="inherit" />
                  Logging in...
                </>
              ) : (
                'Login'
              )}
            </Button>
          </Box>

          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Demo Credentials: Use your Keycloak test user
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

const LoginPage = Login;
export default LoginPage;
