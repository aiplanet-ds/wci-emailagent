# Price-Change Inbox Dashboard - Quick Start Guide

## 🎉 Ready to Run!

The complete Price-Change Inbox Dashboard has been built and is ready to use.

---

## 🚀 Start the Application (2 steps)

### Step 1: Start Backend
```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent
python -m uvicorn start:app --reload --port 8000
```

### Step 2: Start Frontend (new terminal)
```bash
cd c:\Users\adith\OneDrive\Desktop\wci-emailagent\frontend
npm run dev
```

### Step 3: Open Browser
Navigate to: **http://localhost:5173**

---

## ✅ What's Working

### Backend Features
- ✅ Email list API with filters (all, price_change, processed, etc.)
- ✅ Email detail API with full extraction data
- ✅ Missing fields validation
- ✅ AI follow-up email generation (Azure OpenAI)
- ✅ Mark as processed → Auto-sync to Epicor
- ✅ User authentication (Microsoft OAuth)
- ✅ CORS enabled for React

### Frontend Features
- ✅ Modern React + TypeScript dashboard
- ✅ Inbox table with filters & search
- ✅ Email detail drawer (slides in from right)
- ✅ Supplier information display
- ✅ Price change summary with visual indicators
- ✅ Products table with price comparisons
- ✅ Missing fields checklist (auto-detected)
- ✅ AI-generated follow-up email modal
- ✅ Mark as processed button (syncs to Epicor)
- ✅ Real-time updates (30-second auto-refresh)
- ✅ Responsive design (desktop/tablet)

---

## 📊 Features Overview

### Inbox View
- Filter emails by status (All, Price Change, Processed, etc.)
- Search by subject or sender
- See email badges (Price Change, Processed, Needs Info)
- View sync status and product counts
- Click any row to view details

### Email Detail Drawer
1. **Header**: Subject, sender, date, status badges
2. **Supplier Info**: ID, name, contact details
3. **Price Change Summary**: Type, effective date, reason
4. **Products Table**: Part numbers, old/new prices, % change
5. **Additional Details**: Terms, payment info, notes
6. **Missing Fields Checklist**: Auto-detected required fields
7. **AI Follow-up**: Generate professional email to supplier
8. **Processed Toggle**: Mark complete → syncs to Epicor

---

## 🔄 Complete Workflow Example

1. **Log in** via Microsoft OAuth
2. **View inbox** of price-change emails
3. **Click email** to open detail drawer
4. **Review extracted data** (supplier, products, prices)
5. **Check for missing fields** (yellow warning card)
6. **Select missing fields** and click "Write AI Follow-up"
7. **Copy AI-generated email** to clipboard
8. **Send to supplier** via your email client
9. **When complete**, click "Mark as Processed"
10. **System automatically** syncs prices to Epicor ERP

---

## 🎯 Test Data

Your existing emails in `outputs/adithyatest1617_at_outlook_dot_com/` will appear in the dashboard automatically.

Example email:
- Subject: "Price Change Notification - Effective October 2099"
- Supplier: Faster Inc. (Indiana)
- Product: Hydraulic Fitting SAE Standard (#FFH06-12SAE F)
- Old Price: $190.00 → New Price: $130.00 (-31.58%)

---

## 🛠️ API Endpoints

All endpoints require authentication:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user` | Current user info |
| GET | `/api/emails` | List emails (with filters) |
| GET | `/api/emails/:id` | Email details |
| PATCH | `/api/emails/:id` | Update processed status |
| POST | `/api/emails/:id/followup` | Generate AI follow-up |

---

## 📁 File Structure

```
wci-emailagent/
├── Backend (FastAPI)
│   ├── start.py                    # Main app + API router
│   ├── routers/emails.py           # Email API endpoints
│   ├── services/
│   │   ├── email_state_service.py  # State management
│   │   ├── validation_service.py   # Missing fields
│   │   └── epicor_service.py       # ERP integration
│   └── extractor.py                # AI extraction + follow-up
│
├── Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   │   ├── inbox/             # Inbox table & filters
│   │   │   ├── detail/            # Email drawer & sections
│   │   │   ├── layout/            # Dashboard layout
│   │   │   └── ui/                # Reusable components
│   │   ├── hooks/                 # React Query hooks
│   │   ├── services/api.ts        # HTTP client
│   │   ├── types/email.ts         # TypeScript types
│   │   └── App.tsx                # Main app
│   └── vite.config.ts             # Vite + proxy config
│
└── data/
    └── email_states.json           # Email processing state
```

---

## ⚡ Performance

- **Auto-refresh**: Inbox refreshes every 30 seconds
- **Caching**: React Query caches API responses
- **Optimistic updates**: UI updates immediately on actions
- **Build size**: ~325 KB (gzipped: 101 KB)

---

## 🔐 Security

- OAuth 2.0 authentication (Microsoft)
- Session-based authorization
- HTTP-only cookies
- CORS restricted to localhost:5173
- Email data isolated per user

---

## 📚 Documentation

- **[SETUP_AND_RUN.md](SETUP_AND_RUN.md)** - Comprehensive setup guide
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Detailed architecture

---

## 🐛 Troubleshooting

**Backend not starting?**
- Check Azure OpenAI credentials in `.env`
- Verify Epicor API credentials

**Frontend not loading?**
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS configuration

**Not authenticated?**
- Click "Log In" and complete Microsoft OAuth
- Check that cookies are enabled

---

## 🎨 Customization

### Change UI Colors
Edit `frontend/src/index.css` or Tailwind classes in components

### Adjust Refresh Rate
Edit `frontend/src/hooks/useEmails.ts`:
```typescript
refetchInterval: 30000, // milliseconds
```

### Modify Validation Rules
Edit `services/validation_service.py`

---

## 🚀 Next Features to Add

1. Email archiving
2. Export to CSV/Excel
3. Analytics dashboard
4. Bulk operations
5. Custom email templates
6. Approval workflows
7. Notification system

---

**Enjoy your new Price-Change Inbox Dashboard! 🎉**
