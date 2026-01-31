import config from '../config/config';
import apiClient from './apiClient';
import type { TokenResponse, User } from '../types';

class AuthService {
  private keycloakUrl: string;
  private realm: string;
  private clientId: string;

  constructor() {
    this.keycloakUrl = config.keycloakUrl;
    this.realm = config.keycloakRealm;
    this.clientId = config.keycloakClientId;
  }

  /**
   * Login with username and password via Keycloak
   */
  async login(email: string, password: string): Promise<TokenResponse> {
    const tokenUrl = `${this.keycloakUrl}/realms/${this.realm}/protocol/openid-connect/token`;
    
    const params = new URLSearchParams({
      grant_type: 'password',
      client_id: this.clientId,
      username: email,
      password: password,
    });

    try {
      const response = await fetch(tokenUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error_description || 'Login failed');
      }

      const data = await response.json();
      
      const tokenResponse: TokenResponse = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
        expires_in: data.expires_in,
      };

      // Store tokens
      this.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

      return tokenResponse;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const tokenUrl = `${this.keycloakUrl}/realms/${this.realm}/protocol/openid-connect/token`;
    
    const params = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: this.clientId,
      refresh_token: refreshToken,
    });

    try {
      const response = await fetch(tokenUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params,
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      
      const tokenResponse: TokenResponse = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
        expires_in: data.expires_in,
      };

      this.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

      return tokenResponse;
    } catch (error) {
      console.error('Token refresh error:', error);
      this.logout();
      throw error;
    }
  }

  /**
   * Logout user
   */
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  /**
   * Get current user info from backend
   */
  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>('/api/v1/users/me');
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error);
      throw error;
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  /**
   * Get access token from storage
   */
  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Get refresh token from storage
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  /**
   * Set tokens in storage
   */
  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  /**
   * Decode JWT token to get user info
   */
  decodeToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Token decode error:', error);
      return null;
    }
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token: string): boolean {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) {
      return true;
    }
    const expirationTime = decoded.exp * 1000; // Convert to milliseconds
    return Date.now() >= expirationTime;
  }
}

const authService = new AuthService();
export default authService;
