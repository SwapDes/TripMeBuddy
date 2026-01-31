import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Typography, Box, Button } from '@mui/material';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Container maxWidth="sm">
        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h1" component="h1" gutterBottom fontWeight="bold">
            404
          </Typography>
          <Typography variant="h5" component="h2" gutterBottom>
            Page Not Found
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            The page you're looking for doesn't exist.
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate('/dashboard')}
          >
            Go to Dashboard
          </Button>
        </Box>
      </Container>
    </Box>
  );
};

const NotFoundPage = NotFound;
export default NotFoundPage;
