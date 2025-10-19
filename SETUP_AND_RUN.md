# Price-Change Inbox Dashboard - Complete Setup Guide

## 🎉 Implementation Complete!

All backend and frontend components have been built and are ready to run.

---

## 📋 What's Been Built

### Backend (Python/FastAPI)
✅ Email State Management Service
✅ Validation Service (missing fields detection)
✅ AI Follow-up Email Generator (Azure OpenAI)
✅ REST API Endpoints (`/api/emails/*`)
✅ CORS Configuration for React
✅ User Authentication Endpoint

### Frontend (React/TypeScript)
✅ Vite + React + TypeScript Setup
✅ Tailwind CSS Styling
✅ React Query State Management
✅ Complete UI Component Library
✅ Inbox Table with Filters & Search
✅ Email Detail Drawer
✅ Missing Fields Checklist
✅ AI Follow-up Modal
✅ Dashboard Layout

---

## 🚀 How to Run

### Step 1: Start the Backend

```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent
python -m uvicorn start:app --reload --port 8000
```

**Expected Output:**
```
🚀 EMAIL INTELLIGENCE SYSTEM - AUTOMATED MODE
================================================================================
📋 Configuration:
   🔄 Polling Interval: 60 seconds (1 minute)
   🤖 AI Engine: Azure OpenAI
   💼 ERP Integration: Epicor REST API v2
   🔐 Authentication: Microsoft OAuth 2.0
--------------------------------------------------------------------------------
🚀 Starting automated email monitoring service...
✅ Automated monitoring service ACTIVE
================================================================================
📱 Web Interface: http://localhost:8000
ℹ️  Users must login to enable automated processing
================================================================================

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 2: Start the Frontend

Open a **new terminal** window:

```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent\frontend
npm run dev
```

**Expected Output:**
```
  VITE v7.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Step 3: Access the Application

1. Open your browser to: **http://localhost:5173**
2. You'll be redirected to Microsoft OAuth login
3. Log in with your Microsoft account
4. After authentication, you'll see the Price-Change Inbox Dashboard

---

## 🎯 Testing the Complete Workflow

### Test 1: View Emails
1. The inbox should display all price-change emails from your `outputs/` directory
2. Try different filters: All, Price Change, Processed, Unprocessed
3. Use the search bar to find specific emails

### Test 2: View Email Details
1. Click on any email row in the inbox
2. The detail drawer should slide in from the right
3. Verify all sections:
   - ✅ Supplier Information
   - ✅ Price Change Summary
   - ✅ Affected Products (table)
   - ✅ Additional Details
   - ✅ Missing Fields Checklist (if applicable)

### Test 3: Generate AI Follow-up
1. If missing fields are detected, you'll see a yellow "Missing Information" card
2. Check the boxes for fields you want to request
3. Click "Write AI Follow-up"
4. A modal should appear with the AI-generated email
5. Click "Copy to Clipboard" to copy the email

### Test 4: Mark as Processed
1. In the email detail drawer, click "Mark as Processed"
2. The system will:
   - Validate required fields are present
   - Sync prices to Epicor ERP
   - Update the email state
   - Show the Epicor sync status
3. The badge should change from "Unprocessed" to "Processed"

---

## 📂 Directory Structure

```
wci-emailagent/
├── backend/
│   ├── start.py                           # FastAPI main app
│   ├── routers/
│   │   └── emails.py                      # Email API endpoints
│   ├── services/
│   │   ├── email_state_service.py         # State management
│   │   ├── validation_service.py          # Missing fields validation
│   │   ├── epicor_service.py              # Epicor integration
│   │   └── delta_service.py               # Email monitoring
│   ├── auth/
│   │   ├── oauth.py                       # Microsoft OAuth
│   │   └── multi_graph.py                 # Graph API client
│   ├── extractor.py                       # AI extraction + follow-up
│   ├── processors.py                      # Attachment processing
│   ├── main.py                            # Email processing logic
│   └── data/
│       └── email_states.json              # Email state storage
├── frontend/
│   ├── src/
│   │   ├── components/                    # React components
│   │   ├── hooks/                         # React Query hooks
│   │   ├── services/                      # API client
│   │   ├── types/                         # TypeScript types
│   │   ├── lib/                           # Utilities
│   │   ├── App.tsx                        # Main app
│   │   └── main.tsx                       # Entry point
│   ├── vite.config.ts                     # Vite configuration
│   ├── tailwind.config.js                 # Tailwind CSS config
│   └── package.json                       # Dependencies
└── outputs/                               # Email JSON files
    └── {user_email}/
        ├── price_change_{message_id}.json
        └── epicor_update_{message_id}.json
```

---

## 🔧 Troubleshooting

### Backend Issues

**Error: "EPICOR_BASE_URL not configured"**
- Check your `.env` file has all required Epicor credentials
- Make sure `.env` is in the project root

**Error: "Not authenticated"**
- Ensure you've logged in via Microsoft OAuth
- Check that session cookies are enabled in your browser

**Error: "Failed to sync to Epicor"**
- Verify Epicor API credentials are correct
- Check that required fields are present before marking as processed

### Frontend Issues

**Blank screen / Loading forever**
- Check browser console for errors
- Ensure backend is running on port 8000
- Verify CORS is configured correctly

**"Not Authenticated" message**
- Click "Log In" button
- Complete Microsoft OAuth flow
- Return to http://localhost:5173

**API errors (401, 403, 500)**
- Check Network tab in browser DevTools
- Verify API endpoints are responding
- Check backend console for error logs

### CORS Issues

If you see CORS errors in the browser console:

1. Verify backend has CORS middleware configured (already done in `start.py`)
2. Check that `allow_origins` includes `http://localhost:5173`
3. Ensure `allow_credentials: True` is set

---

## 🎨 Customization

### Change Theme Colors

Edit `frontend/tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: '#your-color',
      // ... other colors
    },
  },
},
```

### Adjust Auto-Refresh Interval

Edit `frontend/src/hooks/useEmails.ts`:
```typescript
refetchInterval: 30000, // Change to your preferred milliseconds
```

### Modify Missing Field Rules

Edit `services/validation_service.py`:
```python
# Update validation logic in validate_email_data()
```

---

## 📊 API Endpoints Reference

### GET /api/user
Get current authenticated user information

**Response:**
```json
{
  "authenticated": true,
  "email": "user@example.com",
  "name": "User Name"
}
```

### GET /api/emails
List all emails with optional filters

**Query Params:**
- `filter`: all | price_change | non_price_change | processed | unprocessed
- `search`: search string

**Response:**
```json
{
  "emails": [...],
  "total": 42
}
```

### GET /api/emails/:message_id
Get detailed information for a specific email

**Response:**
```json
{
  "email_data": {...},
  "state": {...},
  "validation": {...},
  "epicor_status": {...}
}
```

### PATCH /api/emails/:message_id
Update email state (mark as processed/unprocessed)

**Request Body:**
```json
{
  "processed": true
}
```

**Response:**
```json
{
  "success": true,
  "state": {...},
  "epicor_result": {...}
}
```

### POST /api/emails/:message_id/followup
Generate AI follow-up email

**Request Body:**
```json
{
  "missing_fields": [
    {
      "field": "contact_email",
      "label": "Contact Email",
      "section": "supplier_info"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "followup_draft": "Dear Supplier...",
  "generated_at": "2025-01-15T10:30:00"
}
```

---

## 🔐 Security Notes

- OAuth tokens are stored server-side in encrypted format
- Session cookies are HTTP-only and secure
- CORS is restricted to localhost during development
- For production, update CORS origins to your domain

---

## 📝 Next Steps / Future Enhancements

1. **Email Archiving**: Add ability to archive old emails
2. **Export Functionality**: Export emails/products to CSV/Excel
3. **Analytics Dashboard**: Charts showing price trends, supplier activity
4. **Bulk Operations**: Process multiple emails at once
5. **Notifications**: Email/SMS alerts for new price changes
6. **Approval Workflow**: Multi-step approval before Epicor sync
7. **Audit Logs**: Detailed activity tracking
8. **Custom Templates**: Customizable follow-up email templates

---

## ✅ Acceptance Criteria Met

From the original specification:

✅ Inbox lists emails with subject, sender, date, badges
✅ Filter and search work correctly
✅ Detail view shows all extracted data
✅ Missing fields appear as checklist items
✅ Write AI Follow-up button activates when ≥1 box checked
✅ Modal displays generated draft
✅ Processed toggle updates backend and syncs to Epicor
✅ Error states have clear retry paths
✅ Responsive for desktop/tablet
✅ Keyboard navigation and ARIA labels

---

## 🎓 Architecture Decisions

### Why React Query?
- Automatic caching and revalidation
- Built-in loading/error states
- Optimistic updates
- Auto-refetching on interval

### Why Tailwind CSS?
- Utility-first approach (fast development)
- No CSS conflicts
- Highly customizable
- Great developer experience

### Why JSON Files for State?
- Simple implementation
- No database setup required
- Easy to audit (human-readable)
- Matches existing architecture

### Why Separate API Routes?
- Clean separation of concerns
- Easy to add more endpoints
- Can scale to microservices later
- RESTful design principles

---

## 📞 Support

If you encounter issues:

1. Check browser console for errors
2. Check backend terminal for error logs
3. Review the troubleshooting section above
4. Check `IMPLEMENTATION_GUIDE.md` for detailed component documentation

---

**Built with ❤️ using FastAPI, React, TypeScript, and Azure AI**
