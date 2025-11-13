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
from routers import emails, dashboard
import os
import secrets
import json

app = FastAPI(title="WCI Email Agent API", version="1.0.0")

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React dev server
        "http://localhost:8000",  # Same origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for user authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", secrets.token_hex(32)),
    max_age=24 * 60 * 60  # 24 hours
)

# Include API routers
app.include_router(emails.router)
app.include_router(dashboard.router)

# Mount static files and templates
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
        return RedirectResponse(url="/success", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.get("/login")
async def login(request: Request):
    """Initiate OAuth login flow"""
    # Generate state for security
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Get OAuth authorization URL
    redirect_uri = str(request.url_for("auth_callback"))
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
        # Exchange code for token
        redirect_uri = str(request.url_for("auth_callback"))
        result = multi_auth.exchange_code_for_token(code, redirect_uri)
        
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
            print("\n" + "="*80)
            print(f"[AUTH] USER AUTHENTICATED: {user_email}")
            print("="*80)
            await delta_service.add_user_to_monitoring(user_email)
            print(f"[OK] User added to automated monitoring")
            print(f"[ACTIVE] Automated workflow ACTIVATED:")
            print(f"   [1] Email detection (every 60 seconds)")
            print(f"   [2] Azure OpenAI extraction")
            print(f"   [3] Epicor ERP price update")
            print("="*80 + "\n")
        except Exception as e:
            print(f"[WARN] WARNING: Could not add user to monitoring: {e}")

        return RedirectResponse(url="/success", status_code=302)
        
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
            print("\n" + "="*80)
            print(f"[LOGOUT] USER LOGOUT: {user_email}")
            print("="*80)
            await delta_service.remove_user_from_monitoring(user_email)
            print(f"[OK] User removed from automated monitoring")
            print(f"[STOP] Automated workflow DEACTIVATED for this user")
            print("="*80 + "\n")
        except Exception as e:
            print(f"[ERROR] ERROR removing user from monitoring: {e}")

    # Clear session
    request.session.clear()

    return RedirectResponse(url="/", status_code=302)

# Start delta service when application starts
@app.on_event("startup")
async def startup_event():
    """Initialize database and start the delta service when the application starts"""
    print("\n" + "="*80)
    print("[STARTUP] EMAIL INTELLIGENCE SYSTEM - AUTOMATED MODE")
    print("="*80)

    # Database initialization
    print("[DB] Initializing database connection...")
    try:
        from database.config import init_db, engine
        from sqlalchemy import text

        # Test database connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("[OK] Database connection successful")

        # Ensure all tables exist
        print("[DB] Creating/verifying database tables...")
        await init_db()
        print("[OK] Database tables ready")

    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        print("[ERROR] Application cannot start without database")
        print("[ERROR] Please ensure PostgreSQL is running and DATABASE_URL is correct")
        raise

    # Configuration and service startup
    print("[CONFIG] Configuration:")
    print("   [POLL] Polling Interval: 60 seconds (1 minute)")
    print("   [AI] AI Engine: Azure OpenAI")
    print("   [ERP] ERP Integration: Epicor REST API v2")
    print("   [AUTH] Authentication: Microsoft OAuth 2.0")
    print("-"*80)
    print("[START] Starting automated email monitoring service...")
    delta_service.start_polling()
    print("[OK] Automated monitoring service ACTIVE")
    print("="*80)
    print("[WEB] Web Interface: http://localhost:8000")
    print("[INFO] Users must login to enable automated processing")
    print("="*80 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the delta service when the application shuts down"""
    print("\n" + "="*80)
    print("[SHUTDOWN] SHUTTING DOWN EMAIL INTELLIGENCE SYSTEM")
    print("="*80)
    delta_service.stop_polling()
    print("[OK] Automated monitoring service stopped")
    print("="*80 + "\n")

# Run the server when executed directly
if __name__ == "__main__":
    import uvicorn
    print("[START] Starting Email Intelligence System...")
    print("[WEB] Access the web interface at: http://localhost:8000")
    print("[AUTH] OAuth authentication required")
    print("[POLL] Delta query polling for email monitoring")
    uvicorn.run("start:app", host="0.0.0.0", port=8000, reload=True)
