import React from 'react';
import { Container, Typography, Box } from '@mui/material';

const CreateTrip: React.FC = () => {
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Create New Trip
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Trip creation page coming soon.
        </Typography>
      </Box>
    </Container>
  );
};

const CreateTripPage = CreateTrip;
export default CreateTripPage;
