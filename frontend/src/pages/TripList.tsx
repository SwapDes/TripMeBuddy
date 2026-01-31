import React from 'react';
import { Container, Typography, Box } from '@mui/material';

const TripList: React.FC = () => {
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          My Trips
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Trip list page coming soon.
        </Typography>
      </Box>
    </Container>
  );
};

const TripListPage = TripList;
export default TripListPage;
