"""
Keycloak Admin API integration for user management
"""
import httpx
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class KeycloakAdmin:
    """Service for managing users via Keycloak Admin API"""
    
    def __init__(
        self,
        server_url: str,
        realm_name: str,
        client_id: str,
        client_secret: str
    ):
        self.server_url = server_url.rstrip('/')
        self.realm_name = realm_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.admin_token: Optional[str] = None
    
    async def _get_admin_token(self) -> str:
        """Get admin access token using client credentials"""
        token_url = f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with admin token"""
        if not self.admin_token:
            self.admin_token = await self._get_admin_token()
        
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json",
        }
    
    async def user_exists(self, email: str) -> bool:
        """Check if user with email already exists"""
        try:
            users_url = f"{self.server_url}/admin/realms/{self.realm_name}/users"
            params = {"email": email, "exact": "true"}
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(users_url, params=params, headers=headers)
                
                # Token expired, retry with new token
                if response.status_code == 401:
                    self.admin_token = None
                    headers = await self._get_headers()
                    response = await client.get(users_url, params=params, headers=headers)
                
                response.raise_for_status()
                users = response.json()
                return len(users) > 0
                
        except Exception as e:
            logger.error(f"Error checking if user exists: {e}")
            raise
    
    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        email_verified: bool = False
    ) -> str:
        """
        Create a new user in Keycloak
        
        Returns:
            str: Keycloak user ID
        """
        try:
            # Check if user already exists
            if await self.user_exists(email):
                raise ValueError(f"User with email {email} already exists")
            
            users_url = f"{self.server_url}/admin/realms/{self.realm_name}/users"
            headers = await self._get_headers()
            
            # User data
            user_data = {
                "username": email,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": email_verified,
                "credentials": [{
                    "type": "password",
                    "value": password,
                    "temporary": False
                }]
            }
            
            async with httpx.AsyncClient() as client:
                # Create user
                response = await client.post(users_url, json=user_data, headers=headers)
                
                # Token expired, retry with new token
                if response.status_code == 401:
                    self.admin_token = None
                    headers = await self._get_headers()
                    response = await client.post(users_url, json=user_data, headers=headers)
                
                if response.status_code == 409:
                    raise ValueError(f"User with email {email} already exists")
                
                response.raise_for_status()
                
                # Get user ID from Location header
                location = response.headers.get("Location")
                if location:
                    user_id = location.split("/")[-1]
                    logger.info(f"Created user in Keycloak with ID: {user_id}")
                    return user_id
                else:
                    # Fallback: query for user
                    params = {"email": email, "exact": "true"}
                    response = await client.get(users_url, params=params, headers=headers)
                    response.raise_for_status()
                    users = response.json()
                    if users:
                        return users[0]["id"]
                    else:
                        raise Exception("User created but ID not found")
                        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating user in Keycloak: {e}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def reset_password(self, user_id: str, new_password: str, temporary: bool = False) -> None:
        """Reset user password"""
        try:
            reset_url = f"{self.server_url}/admin/realms/{self.realm_name}/users/{user_id}/reset-password"
            headers = await self._get_headers()
            
            credential_data = {
                "type": "password",
                "value": new_password,
                "temporary": temporary
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(reset_url, json=credential_data, headers=headers)
                
                # Token expired, retry with new token
                if response.status_code == 401:
                    self.admin_token = None
                    headers = await self._get_headers()
                    response = await client.put(reset_url, json=credential_data, headers=headers)
                
                response.raise_for_status()
                logger.info(f"Password reset for user ID: {user_id}")
                
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            raise Exception(f"Failed to reset password: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user details by email"""
        try:
            users_url = f"{self.server_url}/admin/realms/{self.realm_name}/users"
            params = {"email": email, "exact": "true"}
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(users_url, params=params, headers=headers)
                
                # Token expired, retry with new token
                if response.status_code == 401:
                    self.admin_token = None
                    headers = await self._get_headers()
                    response = await client.get(users_url, params=params, headers=headers)
                
                response.raise_for_status()
                users = response.json()
                return users[0] if users else None
                
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
