import React, { createContext, useState, useEffect, useContext, type ReactNode } from 'react';
import authService from '../services/authService';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = authService.getAccessToken();
        
        if (token && !authService.isTokenExpired(token)) {
          // Token exists and is valid, fetch user data
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        } else if (token && authService.isTokenExpired(token)) {
          // Token expired, try to refresh
          try {
            await authService.refreshToken();
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            // Refresh failed, clear tokens
            authService.logout();
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        authService.logout();
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      await authService.login(email, password);
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      console.error('Login error details:', error);
      throw error;
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
