from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from auth.oauth import multi_auth
from auth.multi_graph import graph_client
from services.delta_service import delta_service
import os
import secrets

app = FastAPI()

# Add session middleware for user authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", secrets.token_hex(32)),
    max_age=24 * 60 * 60  # 24 hours
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Helper function to get current user from session
def get_current_user(request: Request) -> str:
    """Get current user email from session"""
    user_email = request.session.get("user_email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_email

# OAuth Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirect to dashboard if logged in, otherwise show login"""
    user_email = request.session.get("user_email")
    if user_email and multi_auth.is_user_authenticated(user_email):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

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
        
        # Add user to delta monitoring (no webhook subscriptions needed with delta queries)
        try:
            await delta_service.add_user_to_monitoring(user_email)
            print(f"✅ Added user {user_email} to delta monitoring")
        except Exception as e:
            print(f"⚠️ Warning: Could not add user to monitoring: {e}")
        
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "error": f"Authentication failed: {str(e)}"
        })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard"""
    try:
        user_email = get_current_user(request)
        user_name = request.session.get("user_name", user_email)
        
        # Get user's recent messages
        try:
            messages = graph_client.get_user_messages(user_email, top=10)
        except Exception as e:
            messages = []
            print(f"Error fetching messages for {user_email}: {e}")
        
        # Get user's processed emails count
        user_output_dir = f"outputs/{user_email.replace('@', '_at_').replace('.', '_dot_')}"
        processed_count = 0
        if os.path.exists(user_output_dir):
            processed_count = len([f for f in os.listdir(user_output_dir) if f.endswith('.json')])
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_email": user_email,
            "user_name": user_name,
            "messages": messages,
            "processed_count": processed_count
        })
        
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

@app.post("/logout")
async def logout(request: Request):
    """Logout user"""
    user_email = request.session.get("user_email")
    subscription_id = request.session.get("subscription_id")
    
    # Delete webhook subscription
    if user_email and subscription_id:
        try:
            graph_client.delete_user_subscription(user_email, subscription_id)
            print(f"✅ Deleted subscription for user {user_email}")
        except Exception as e:
            print(f"⚠️ Error deleting subscription: {e}")
    
    # Clear session
    request.session.clear()
    
    return RedirectResponse(url="/", status_code=302)

@app.get("/email/{message_id}", response_class=HTMLResponse)
async def email_details(request: Request, message_id: str):
    """Show email details and extracted information"""
    try:
        user_email = get_current_user(request)
        
        # Get email from Microsoft Graph
        try:
            message = graph_client.get_user_message_by_id(user_email, message_id)
        except Exception as e:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Could not fetch email: {str(e)}"
            })
        
        # Check if extraction already exists
        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        user_output_dir = f"outputs/{safe_email}"
        output_filename = f"price_change_{message_id}.json"
        output_path = os.path.join(user_output_dir, output_filename)
        
        extracted_data = None
        extraction_exists = False
        
        if os.path.exists(output_path):
            try:
                import json
                with open(output_path, 'r', encoding='utf-8') as f:
                    extracted_data = json.load(f)
                extraction_exists = True
            except Exception as e:
                print(f"Error reading extraction file: {e}")
        
        return templates.TemplateResponse("email_details.html", {
            "request": request,
            "message": message,
            "message_id": message_id,
            "user_email": user_email,
            "extracted_data": extracted_data,
            "extraction_exists": extraction_exists
        })
        
    except HTTPException:
        return RedirectResponse(url="/", status_code=302)

# Start delta service when application starts
@app.on_event("startup")
async def startup_event():
    """Start the delta service when the application starts"""
    print("🚀 Starting delta email service...")
    delta_service.start_polling()
    print("✅ Delta email service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the delta service when the application shuts down"""
    print("⏹️ Stopping delta email service...")
    delta_service.stop_polling()
    print("✅ Delta email service stopped")

@app.post("/process/{message_id}")
async def process_email(request: Request, message_id: str):
    """Trigger manual email processing/extraction"""
    try:
        user_email = get_current_user(request)
        
        # Check if already exists
        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        user_output_dir = f"outputs/{safe_email}"
        output_filename = f"price_change_{message_id}.json"
        output_path = os.path.join(user_output_dir, output_filename)
        
        if os.path.exists(output_path):
            return {"status": "already_processed", "message": "Email has already been processed"}
        
        # Process immediately (no longer need background tasks)
        try:
            from main import process_user_message
            msg = graph_client.get_user_message_by_id(user_email, message_id)
            result = process_user_message(msg, user_email)
            
            return {"status": "completed", "message": "Email processed successfully", "result": result}
            
        except Exception as e:
            return {"status": "error", "message": f"Processing failed: {str(e)}"}
        
    except HTTPException:
        return {"status": "error", "message": "Not authenticated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# Run the server when executed directly
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Email Intelligence System...")
    print("📱 Access the web interface at: http://localhost:8000")
    print("🔒 OAuth authentication required")
    print("📬 Delta query polling for email monitoring")
    uvicorn.run("start:app", host="0.0.0.0", port=8000, reload=True)
