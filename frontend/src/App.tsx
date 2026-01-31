import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

// Page imports
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TripList from './pages/TripList';
import TripDetail from './pages/TripDetail';
import NewTrip from './pages/NewTrip';
import TripProgress from './pages/TripProgress';
import NotFound from './pages/NotFound';

// Create MUI theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips"
              element={
                <ProtectedRoute>
                  <Layout>
                    <TripList />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips/new"
              element={
                <ProtectedRoute>
                  <Layout>
                    <NewTrip />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips/progress/:jobId"
              element={
                <ProtectedRoute>
                  <Layout>
                    <TripProgress />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/trips/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <TripDetail />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Redirects */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
