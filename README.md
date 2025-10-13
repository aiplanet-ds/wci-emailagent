# Email Intelligence System - Multi-User AI-Powered Email Processing

This project is a comprehensive **AI-Powered Email Intelligence System** that connects to Microsoft Outlook via the Microsoft Graph API, provides secure multi-user authentication, and processes emails automatically using delta queries. The system features a professional web interface, automated polling for new emails, and complete user data isolation.

---

## 🌟 Key Features

- **🔐 Multi-User OAuth Authentication**: Secure Microsoft login for any user
- **🎨 Professional Web Interface**: Modern, responsive dashboard with real-time statistics
- **🤖 AI-Powered Processing**: Azure OpenAI-driven email analysis and data extraction
- **📊 Supplier Price Change Detection**: Specialized extraction for pricing notifications
- **🔒 Complete Data Isolation**: Each user's data is completely separated and secure
- **📬 Delta Query Monitoring**: Automated email polling every 3 minutes for new messages
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices
- **🛡️ Enterprise Security**: Session management, token caching, and secure authentication

---

## 📂 Project Structure
```
email-intelligence-system/
│── auth/
│   │── oauth.py            # Multi-user OAuth authentication
│   │── multi_graph.py      # Microsoft Graph client with delta queries
│── services/
│   │── delta_service.py    # Background delta query polling service
│── templates/
│   │── login.html          # Professional login page
│   │── dashboard.html      # User dashboard interface
│   │── error.html          # Error handling pages
│── static/                 # CSS, JS, and static assets
│── processors.py           # Attachment processing (PDF, Excel, Word, TXT)
│── extractor.py            # OpenAI-powered JSON extraction
│── main.py                 # Legacy CLI processing (use web interface instead)
│── webhook.py              # FastAPI web application with OAuth routes
│── requirements.txt        # Python dependencies
│── .env.template           # Environment configuration template
│── README.md
│── downloads/              # User-specific attachment storage
│   │── user1_at_domain_dot_com/
│   │── user2_at_domain_dot_com/
│── outputs/                # User-specific JSON results
│   │── user1_at_domain_dot_com/
│   │── user2_at_domain_dot_com/
│── token_cache_*.json      # Per-user authentication tokens
```

---

## ⚙️ Setup

### 1. Clone Repo
```bash
git clone <repo-url>
cd email-information-extraction
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
# Activate:
# On Linux/Mac
source .venv/bin/activate
# On Windows
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.template` → `.env` and fill in your values:
```env
# Microsoft Azure AD / App Registration
AZ_TENANT_ID=your-tenant-id
AZ_CLIENT_ID=your-client-id
AZ_CLIENT_SECRET=your-client-secret
AZ_USER_EMAIL=your-email@example.com   # only used in application mode

# Modes: delegated | application
GRAPH_MODE=delegated

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_API_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Session security (optional - will be auto-generated if not provided)
SESSION_SECRET=your-session-secret-key

# NOTE: WEBHOOK_URL is no longer needed - using delta queries instead
```

### 5. Configure Azure App Registration
For the multi-user OAuth to work, ensure your Azure app registration has:

**API Permissions:**
- `User.Read` (Microsoft Graph)
- `Mail.Read` (Microsoft Graph)

**Authentication:**
- Platform: Web
- Redirect URI: `http://localhost:8000/auth/callback` (for development)
- For production: `https://yourdomain.com/auth/callback`

**Supported account types:**
- "Accounts in any organizational directory and personal Microsoft accounts"

---

## 📱 Usage

### Web Interface (Recommended)

1. **Start the Application:**
   ```cmd
   python start.py
   ```

2. **Access the Web Interface:**
   - Open your browser to: `http://localhost:8000`
   - Click "Login with Microsoft" 
   - Complete OAuth authentication
   - View your personalized dashboard

3. **Email Processing:**
   - The system automatically polls for new emails every 3 minutes using delta queries
   - New emails are processed automatically when detected
   - View results on your dashboard
   - Download processed files from the web interface

### CLI Mode (Direct Processing)

For one-off email processing without the web interface:

```cmd
python main.py
```

This processes emails directly using the configured account in `.env`

---

## 🔧 Advanced Configuration

### Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `AZ_TENANT_ID` | Azure tenant ID (use `common` for multi-tenant) | ✅ |
| `AZ_CLIENT_ID` | Azure application client ID | ✅ |
| `AZ_CLIENT_SECRET` | Azure application secret | ✅ |
| `AZ_USER_EMAIL` | User email (CLI mode only) | CLI only |
| `GRAPH_MODE` | `delegated` or `application` | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | ✅ |
| `AZURE_OPENAI_API_ENDPOINT` | Azure OpenAI endpoint URL | ✅ |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI deployment name | ✅ |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | ✅ |
| `SESSION_SECRET` | Session encryption key | Web only |

---

## ✨ Features

### 🔐 Multi-User Authentication
- **OAuth 2.0 Integration**: Secure Microsoft OAuth authentication
- **User Isolation**: Each user's data is completely separated
- **Session Management**: 24-hour secure sessions with automatic cleanup
- **Delta Queries**: Automated polling for new emails every 3 minutes

### 🤖 AI-Powered Processing
- **Smart Extraction**: AI analyzes email content and attachments
- **PDF/Excel Support**: Intelligent parsing of document attachments
- **Structured Output**: Clean JSON data with extracted insights
- **Automated Processing**: Background processing of new emails via polling

### 🌐 Professional Web Interface
- **Modern UI**: Clean, responsive design with gradient styling
- **Live Dashboard**: Current stats and processing status
- **File Management**: Download and manage processed files
- **User Profiles**: Personalized experience for each user

### 🔄 Flexible Processing Modes
- **Web Mode**: Full-featured web application with OAuth
- **CLI Mode**: Direct command-line processing for automation
- **Delta Query Mode**: Automated polling for new emails every 3 minutes
- **Manual Mode**: On-demand processing of existing emails

---

## 🔧 Technical Architecture

### Core Components
- **FastAPI Web Framework**: High-performance async web application
- **Microsoft Graph API**: Email and user data access
- **Delta Query Service**: Background polling for email changes every 3 minutes
- **MSAL Authentication**: Multi-user OAuth token management
- **Azure OpenAI Integration**: AI-powered content analysis
- **Jinja2 Templates**: Server-side rendered web pages
- **APScheduler**: Background task scheduling for automated polling

### Security Features
- **OAuth 2.0**: Industry-standard authentication
- **Session Encryption**: Secure session data storage
- **User Data Isolation**: Complete separation of user data
- **Token Caching**: Secure per-user token storage

### 📬 Delta Query Email Monitoring

The system uses **Microsoft Graph Delta Queries** for efficient email monitoring:

#### How It Works:
1. **Background Polling**: Service runs every 3 minutes checking for new emails
2. **Delta Tokens**: Tracks changes since last check (only new/modified emails)
3. **Multi-User Support**: Each authenticated user monitored separately
4. **Automatic Processing**: New emails automatically processed in background
5. **Error Handling**: Robust retry logic and token refresh capabilities

#### Benefits Over Webhooks:
- ✅ **No ngrok required** - Pure localhost development
- ✅ **No webhook URL management** - No changing tunnel addresses
- ✅ **Simplified Azure setup** - No webhook endpoint configuration
- ✅ **Consistent monitoring** - Reliable 3-minute intervals
- ✅ **Better for development** - No external dependencies

#### Performance:
- **Polling Interval**: 3 minutes (configurable)
- **API Efficiency**: Delta queries only return changes since last poll
- **Resource Usage**: Minimal - only polls when users are authenticated
- **Scalability**: Handles multiple users with separate polling streams

---

## 📝 Notes & Best Practices
- **Delegated mode** = OAuth authentication (recommended for multi-user)
- **Application mode** = Service principal access (requires admin consent)
- **Duplicate prevention**: Built-in safeguards against duplicate processing
- **Production deployment**: Use Azure App Service or similar with HTTPS
- **Session security**: 24-hour automatic session expiration

---

## � Quick Start Commands

### Development
```cmd
# Start web application
python webhook.py

# Access web interface
# http://localhost:8000

# CLI processing
python main.py
```

### Production Setup
```cmd
# Set production environment variables
# Update redirect URIs in Azure App Registration
# Configure HTTPS if needed

# Start application
python webhook.py
```

---

## 📊 Output Structure

### File Organization
```
outputs/
├── user@example.com/          # User-specific directories
│   ├── email_123_analysis.json
│   ├── email_124_analysis.json
│   └── ...
downloads/
├── user@example.com/          # User-specific downloads
│   ├── attachment_1.pdf
│   ├── attachment_2.xlsx
│   └── ...
```

### Sample Output (JSON)
```json
{
  "email_id": "AAMkAD...",
  "subject": "Invoice for Project ABC",
  "sender": "vendor@company.com",
  "timestamp": "2024-01-15T10:30:00Z",
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "amount": "$5,000.00",
    "due_date": "2024-02-15",
    "vendor_details": {
      "name": "ABC Corp",
      "address": "123 Business St"
    }
  },
  "attachments": [
    {
      "filename": "invoice.pdf",
      "type": "pdf",
      "size": "245KB",
      "path": "downloads/user@example.com/invoice.pdf"
    }
  ],
  "processing_metadata": {
    "processed_at": "2024-01-15T10:31:45Z",
    "ai_model": "gpt-4",
    "confidence_score": 0.95
  }
}
```

---

## 🎯 Next Steps

1. **Deploy to Production**: Consider Azure App Service or similar
2. **Add More AI Models**: Integrate additional AI providers
3. **Database Integration**: Store results in a database
4. **API Endpoints**: Build REST API for external integrations
5. **Mobile App**: Create mobile interface for on-the-go access

---

## 🤝 Contributing

We welcome contributions! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready to transform your email workflow? Start with `python webhook.py` and visit `http://localhost:8000`!** 🚀
