from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from auth.oauth import multi_auth
from auth.multi_graph import graph_client
from services.delta_service import delta_service
from services.epicor_service import epicor_service
from routers import emails, dashboard, settings
from dotenv import load_dotenv
import os
import secrets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="WCI Email Agent API", version="1.0.0")

# Frontend URL for post-auth redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "/")

# Load CORS origins from environment variable (comma-separated)
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if not cors_origins_env:
    raise ValueError("CORS_ALLOWED_ORIGINS environment variable is required")
cors_origins = cors_origins_env.split(",")

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for user authentication
# SESSION_SECRET is required - generating at runtime causes session loss on restart
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    raise ValueError("SESSION_SECRET environment variable is required. Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'")
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    max_age=24 * 60 * 60  # 24 hours
)

# Include API routers
app.include_router(emails.router)
app.include_router(dashboard.router)
app.include_router(settings.router)

# Mount static files (only if directory exists) and templates
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Helper function to get current user from session
def get_current_user(request: Request) -> str:
    """Get current user email from session"""
    # Check both 'user' and 'user_email' for backwards compatibility
    user_email = request.session.get("user_email") or request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_email

# API Routes for Frontend
@app.get("/api/user")
async def get_user_info(request: Request):
    """Get current authenticated user information"""
    try:
        user_email = get_current_user(request)
        user_name = request.session.get("user_name", user_email)
        return {
            "authenticated": True,
            "email": user_email,
            "name": user_name
        }
    except HTTPException:
        return {
            "authenticated": False,
            "email": None,
            "name": None
        }

# OAuth Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, error: str = None):
    """Home page - redirect to success if logged in, otherwise show login"""
    user_email = request.session.get("user_email")
    if user_email and multi_auth.is_user_authenticated(user_email):
        return RedirectResponse(url=FRONTEND_URL, status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.get("/login")
async def login(request: Request):
    """Initiate OAuth login flow"""
    # Generate state for security
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Get OAuth authorization URL
    # Force https for redirect URI behind Azure Container Apps TLS termination (skip for localhost)
    redirect_uri = str(request.url_for("auth_callback"))
    if "localhost" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    auth_url = multi_auth.get_authorization_url(redirect_uri, state)
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback"""
    if error:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"OAuth error: {error}"
        })
    
    if not code or not state:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": "Missing authorization code or state"
        })
    
    # Verify state to prevent CSRF
    session_state = request.session.get("oauth_state")
    if not session_state or session_state != state:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": "Invalid state parameter"
        })
    
    try:
        # Exchange code for token (async)
        # Force https for redirect URI behind Azure Container Apps TLS termination (skip for localhost)
        redirect_uri = str(request.url_for("auth_callback"))
        if "localhost" not in redirect_uri:
            redirect_uri = redirect_uri.replace("http://", "https://")
        result = await multi_auth.exchange_code_for_token(code, redirect_uri)
        
        if "access_token" not in result:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "error": f"Token exchange failed: {result.get('error_description', 'Unknown error')}"
            })
        
        # Get user email and info from result
        user_email = result.get("user_email")
        user_info = result.get("user_info", {})
        
        if not user_email:
            return templates.TemplateResponse("error.html", {
                "request": request, 
                "error": "Unable to retrieve user email"
            })
        
        # Store user in session
        request.session["user_email"] = user_email
        request.session["user_name"] = user_info.get("displayName", user_email)
        
        # Add user to delta monitoring for automated email processing
        try:
            logger.info("=" * 80)
            logger.info(f"[AUTH] USER AUTHENTICATED: {user_email}")
            logger.info("=" * 80)
            await delta_service.add_user_to_monitoring(user_email)
            logger.info("User added to automated monitoring")
            logger.info("Automated workflow ACTIVATED:")
            logger.info("   [1] Email detection (every 60 seconds)")
            logger.info("   [2] Azure OpenAI extraction")
            logger.info("   [3] Epicor ERP price update")
            logger.info("=" * 80)
        except Exception as e:
            logger.warning(f"Could not add user to monitoring: {e}")

        return RedirectResponse(url=FRONTEND_URL, status_code=302)
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"Authentication failed: {str(e)}"
        })

@app.get("/success", response_class=HTMLResponse)
async def success(request: Request):
    """Success page - shows automated workflow is active"""
    try:
        user_email = get_current_user(request)

        return templates.TemplateResponse("success.html", {
            "request": request,
            "user_email": user_email
        })

    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """Logout user and stop monitoring"""
    user_email = request.session.get("user_email")

    # Remove user from automated monitoring
    if user_email:
        try:
            logger.info("=" * 80)
            logger.info(f"[LOGOUT] USER LOGOUT: {user_email}")
            logger.info("=" * 80)
            await delta_service.remove_user_from_monitoring(user_email)
            logger.info("User removed from automated monitoring")
            logger.info("Automated workflow DEACTIVATED for this user")
            logger.info("=" * 80)
        except Exception as e:
            logger.error(f"Error removing user from monitoring: {e}")

    # Clear session
    request.session.clear()

    return RedirectResponse(url=FRONTEND_URL, status_code=302)

# Start delta service when application starts
@app.on_event("startup")
async def startup_event():
    """Initialize database and start the delta service when the application starts"""
    logger.info("=" * 80)
    logger.info("[STARTUP] EMAIL INTELLIGENCE SYSTEM - AUTOMATED MODE")
    logger.info("=" * 80)

    # Database initialization
    logger.info("[DB] Verifying database connection...")
    try:
        from database.config import init_db, engine

        # Verify database connection (tables are created by Alembic migrations)
        await init_db()
        logger.info("Database connection verified (tables managed by Alembic migrations)")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error("Application cannot start without database")
        logger.error("Please ensure PostgreSQL is running and DATABASE_URL is correct")
        raise

    # Initialize Epicor OAuth token
    logger.info("[EPICOR] Initializing Epicor OAuth token...")
    try:
        from services.epicor_auth import epicor_auth
        from database.config import get_db

        async for db in get_db():
            token_initialized = await epicor_auth.initialize_token_async(db)
            if token_initialized:
                logger.info("Epicor OAuth token initialized and stored in database")
            else:
                logger.warning("Epicor OAuth token initialization failed - API calls may fail")
            break
    except Exception as e:
        logger.warning(f"Epicor OAuth initialization error: {e}")
        logger.warning("Epicor API calls may fail until token is obtained")

    # Load polling interval from database
    logger.info("[CONFIG] Loading settings from database...")
    try:
        from database.services.settings_service import SettingsService

        async for db in get_db():
            interval_config = await SettingsService.get_polling_interval(db)
            total_seconds = interval_config["total_seconds"]
            delta_service.update_polling_interval(total_seconds)
            logger.info(f"   Polling Interval: {interval_config['value']} {interval_config['unit']} ({total_seconds} seconds)")
            break
    except Exception as e:
        logger.warning(f"Failed to load polling interval from database: {e}")
        logger.info("   Polling Interval: 1 minute (default)")

    # Configuration and service startup
    logger.info("[CONFIG] Configuration:")
    logger.info(f"   Polling Interval: {delta_service.polling_interval} seconds")
    logger.info("   AI Engine: Azure OpenAI")
    logger.info("   ERP Integration: Epicor REST API v2")
    logger.info("   Authentication: Microsoft OAuth 2.0")
    logger.info("-" * 80)
    logger.info("Starting automated email monitoring service...")
    delta_service.start_polling()
    logger.info("Automated monitoring service ACTIVE")
    logger.info("=" * 80)
    logger.info("Web Interface: Running on port 8000")
    logger.info("Users must login to enable automated processing")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the delta service when the application shuts down"""
    logger.info("=" * 80)
    logger.info("[SHUTDOWN] SHUTTING DOWN EMAIL INTELLIGENCE SYSTEM")
    logger.info("=" * 80)
    delta_service.stop_polling()
    logger.info("Automated monitoring service stopped")

    # Close HTTP client connections
    from utils.http_client import HTTPClientManager
    await HTTPClientManager.close_all()
    logger.info("HTTP client connections closed")

    # Close database connection pool
    from database.config import close_db
    await close_db()
    logger.info("Database connections closed")
    logger.info("=" * 80)

# Run the server when executed directly
if __name__ == "__main__":
    import uvicorn

    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    # Only enable reload in development (disabled by default for production safety)
    reload_enabled = os.getenv("RELOAD", "false").lower() == "true"

    logger.info("Starting Email Intelligence System...")
    logger.info("Access the web interface at the configured URL")
    logger.info("OAuth authentication required")
    logger.info("Delta query polling for email monitoring")
    uvicorn.run("main:app", host=host, port=port, reload=reload_enabled)
