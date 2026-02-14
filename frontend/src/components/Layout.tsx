import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  Button,
  Container,
  IconButton,
  Menu,
  MenuItem,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { AccountCircle, Logout } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Create Trip', path: '/trips/new' },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
          <Typography
            variant="h6"
            component="div"
            sx={{ 
              flexGrow: 0, 
              mr: { xs: 1, sm: 4 },
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontSize: { xs: '1rem', sm: '1.25rem' }
            }}
            onClick={() => navigate('/dashboard')}
          >
            Trip Me Buddy
          </Typography>

          <Box sx={{ 
            flexGrow: 1, 
            display: 'flex', 
            gap: { xs: 1, sm: 2 },
            overflow: 'auto',
            '&::-webkit-scrollbar': { display: 'none' },
            scrollbarWidth: 'none'
          }}>
            {navItems.map((item) => (
              <Button
                key={item.path}
                color="inherit"
                onClick={() => navigate(item.path)}
                sx={{
                  fontWeight: location.pathname === item.path ? 'bold' : 'normal',
                  borderBottom: location.pathname === item.path ? '2px solid white' : 'none',
                  fontSize: { xs: '0.875rem', sm: '1rem' },
                  whiteSpace: 'nowrap',
                  minWidth: 'auto',
                  px: { xs: 1, sm: 2 }
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 1 }}>
            {!isMobile && (
              <Typography variant="body2" sx={{ mr: 1 }}>
                {user?.full_name}
              </Typography>
            )}
            <IconButton
              size="large"
              onClick={handleMenu}
              color="inherit"
              sx={{ p: { xs: 0.5, sm: 1 } }}
            >
              <AccountCircle />
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              {isMobile && (
                <MenuItem disabled>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {user?.full_name}
                  </Typography>
                </MenuItem>
              )}
              <MenuItem onClick={handleLogout}>
                <Logout sx={{ mr: 1 }} fontSize="small" />
                Logout
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      <Container
        component="main"
        maxWidth="lg"
        sx={{ mt: 4, mb: 4, flexGrow: 1 }}
      >
        {children}
      </Container>

      <Box
        component="footer"
        sx={{
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) => theme.palette.grey[200],
        }}
      >
        <Container maxWidth="lg">
          <Typography variant="body2" color="text.secondary" align="center">
            © 2026 Trip Me Buddy - AI-Powered Travel Planning
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

const LayoutComponent = Layout;
export default LayoutComponent;
