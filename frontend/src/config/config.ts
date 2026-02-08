/**
 * Application configuration
 * Centralizes all environment variables and configuration settings
 */

interface Config {
  // API Configuration
  apiBaseUrl: string;
  
  // Keycloak Configuration
  keycloakUrl: string;
  keycloakRealm: string;
  keycloakClientId: string;
  
  // Environment
  environment: string;
}

// Load configuration from environment variables
const config: Config = {
  // API Base URL - checks multiple possible env var names
  apiBaseUrl: import.meta.env.VITE_API_URL || 
               import.meta.env.VITE_API_BASE_URL || 
               'http://localhost:8000',
  
  // Keycloak settings
  keycloakUrl: import.meta.env.VITE_KEYCLOAK_URL || 
               'http://trip-me-buddy-alb-389941382.us-east-1.elb.amazonaws.com',
  keycloakRealm: import.meta.env.VITE_KEYCLOAK_REALM || 
                 'tripmeBuddy',
  keycloakClientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 
                    'trip-me-buddy-client',
  
  // Environment mode
  environment: import.meta.env.MODE || 'development',
};

// Validate required configuration
const validateConfig = (): void => {
  const errors: string[] = [];
  
  if (!config.apiBaseUrl) {
    errors.push('API Base URL is not configured');
  }
  
  if (!config.keycloakUrl) {
    errors.push('Keycloak URL is not configured');
  }
  
  if (!config.keycloakRealm) {
    errors.push('Keycloak Realm is not configured');
  }
  
  if (!config.keycloakClientId) {
    errors.push('Keycloak Client ID is not configured');
  }
  
  if (errors.length > 0) {
    console.error('Configuration errors:', errors);
    throw new Error(`Configuration validation failed: ${errors.join(', ')}`);
  }
};

// Log configuration in development (helps with debugging)
if (config.environment === 'development') {
  console.log('=== Application Configuration ===');
  console.log('API Base URL:', config.apiBaseUrl);
  console.log('Keycloak URL:', config.keycloakUrl);
  console.log('Keycloak Realm:', config.keycloakRealm);
  console.log('Keycloak Client ID:', config.keycloakClientId);
  console.log('Environment:', config.environment);
  console.log('================================');
  
  // Validate in development to catch issues early
  try {
    validateConfig();
    console.log('✅ Configuration validated successfully');
  } catch (error) {
    console.error('❌ Configuration validation failed:', error);
  }
}

export default config;
