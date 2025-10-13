import os
import json
import atexit
from typing import Optional, Dict, Any
from msal import ConfidentialClientApplication, SerializableTokenCache
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("AZ_TENANT_ID")
CLIENT_ID = os.getenv("AZ_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZ_CLIENT_SECRET")

# OAuth scopes for delegated permissions
SCOPES = ["User.Read", "Mail.Read"]

class MultiUserAuth:
    def __init__(self):
        self.user_caches: Dict[str, SerializableTokenCache] = {}
        self.user_apps: Dict[str, ConfidentialClientApplication] = {}
        atexit.register(self.save_all_caches)
    
    def get_user_cache_file(self, user_email: str) -> str:
        """Get cache file path for specific user"""
        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        return f"token_cache_{safe_email}.json"
    
    def load_user_cache(self, user_email: str) -> SerializableTokenCache:
        """Load or create token cache for specific user"""
        if user_email not in self.user_caches:
            cache = SerializableTokenCache()
            cache_file = self.get_user_cache_file(user_email)
            
            # Load existing cache if it exists
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    cache.deserialize(f.read())
            
            self.user_caches[user_email] = cache
        
        return self.user_caches[user_email]
    
    def save_user_cache(self, user_email: str):
        """Save token cache for specific user"""
        if user_email in self.user_caches:
            cache = self.user_caches[user_email]
            if cache.has_state_changed:
                cache_file = self.get_user_cache_file(user_email)
                with open(cache_file, "w") as f:
                    f.write(cache.serialize())
    
    def save_all_caches(self):
        """Save all user caches"""
        for user_email in self.user_caches:
            self.save_user_cache(user_email)
    
    def get_user_app(self, user_email: str) -> ConfidentialClientApplication:
        """Get MSAL app for specific user"""
        if user_email not in self.user_apps:
            cache = self.load_user_cache(user_email)
            app = ConfidentialClientApplication(
                CLIENT_ID,
                authority=f"https://login.microsoftonline.com/{TENANT_ID}",
                client_credential=CLIENT_SECRET,
                token_cache=cache
            )
            self.user_apps[user_email] = app

        return self.user_apps[user_email]
    
    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get OAuth authorization URL"""
        # Use a temporary app for getting auth URL (no user-specific cache needed)
        app = ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET
        )

        auth_url = app.get_authorization_request_url(
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )
        return auth_url
    
    def exchange_code_for_token(self, authorization_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token and return user info"""
        # Use a temporary app to exchange the code
        app = ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET
        )

        result = app.acquire_token_by_authorization_code(
            authorization_code,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        if "access_token" in result:
            # Get user info from the token
            import requests
            headers = {"Authorization": f"Bearer {result['access_token']}"}
            user_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
            if user_response.status_code == 200:
                user_info = user_response.json()
                user_email = user_info.get("mail") or user_info.get("userPrincipalName")
                
                if user_email:
                    # Now store the token with the correct user email
                    user_cache = self.load_user_cache(user_email)
                    user_app = self.get_user_app(user_email)
                    
                    # Store the token in the user's cache
                    # We need to manually add the account to the cache
                    account_info = {
                        "client_id": CLIENT_ID,
                        "username": user_email,
                        "home_account_id": result.get("id_token_claims", {}).get("oid", user_email),
                        "environment": "login.microsoftonline.com",
                        "realm": result.get("id_token_claims", {}).get("tid", "common")
                    }
                    
                    # Add token to cache - simplified approach
                    import msal
                    
                    # Store the account info in the cache
                    account = {
                        "home_account_id": result.get("id_token_claims", {}).get("oid", ""),
                        "environment": "login.microsoftonline.com", 
                        "realm": result.get("id_token_claims", {}).get("tid", "common"),
                        "local_account_id": result.get("id_token_claims", {}).get("oid", ""),
                        "username": user_email,
                        "authority_type": "MSSTS"
                    }
                    
                    # Create a proper MSAL cache entry
                    cache_entry = {
                        "AccessToken": {
                            f"{CLIENT_ID}-{account['realm']}-{' '.join(SCOPES)}": {
                                "credential_type": "AccessToken",
                                "secret": result["access_token"],
                                "home_account_id": account["home_account_id"],
                                "environment": account["environment"],
                                "client_id": CLIENT_ID,
                                "target": " ".join(SCOPES),
                                "realm": account["realm"],
                                "token_type": "Bearer",
                                "cached_at": str(int(__import__('time').time())),
                                "expires_on": str(int(__import__('time').time()) + result.get("expires_in", 3600))
                            }
                        },
                        "Account": {
                            f"{account['home_account_id']}-{account['environment']}-{account['realm']}": account
                        }
                    }
                    
                    if result.get("refresh_token"):
                        cache_entry["RefreshToken"] = {
                            f"{CLIENT_ID}-{account['realm']}-": {
                                "credential_type": "RefreshToken", 
                                "secret": result["refresh_token"],
                                "home_account_id": account["home_account_id"],
                                "environment": account["environment"],
                                "client_id": CLIENT_ID,
                                "target": ""
                            }
                        }
                    
                    # Deserialize existing cache and merge
                    existing_cache = user_cache.serialize()
                    if existing_cache:
                        import json
                        existing_data = json.loads(existing_cache)
                        # Merge with new entry
                        for key, value in cache_entry.items():
                            if key in existing_data:
                                existing_data[key].update(value)
                            else:
                                existing_data[key] = value
                        user_cache.deserialize(json.dumps(existing_data))
                    else:
                        import json
                        user_cache.deserialize(json.dumps(cache_entry))
                    
                    self.save_user_cache(user_email)
                    result["user_email"] = user_email
                    result["user_info"] = user_info
        
        return result
    
    def get_user_token(self, user_email: str) -> Optional[str]:
        """Get valid access token for user"""
        app = self.get_user_app(user_email)
        
        # Try to get accounts for this user
        accounts = app.get_accounts()
        
        # Find account matching the user email
        user_account = None
        for account in accounts:
            if account.get("username", "").lower() == user_email.lower():
                user_account = account
                break
        
        if user_account:
            # Try silent token acquisition
            result = app.acquire_token_silent(SCOPES, account=user_account)
            if result and "access_token" in result:
                self.save_user_cache(user_email)
                return result["access_token"]
        
        return None
    
    def is_user_authenticated(self, user_email: str) -> bool:
        """Check if user has valid authentication"""
        return self.get_user_token(user_email) is not None
    
    def logout_user(self, user_email: str):
        """Logout user by removing their cache"""
        cache_file = self.get_user_cache_file(user_email)
        if os.path.exists(cache_file):
            os.remove(cache_file)
        
        # Remove from memory
        if user_email in self.user_caches:
            del self.user_caches[user_email]
        if user_email in self.user_apps:
            del self.user_apps[user_email]

# Global instance
multi_auth = MultiUserAuth()