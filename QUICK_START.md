# 🚀 Quick Start Guide - Email Intelligence System with Epicor Integration

## ✅ What's Working

1. ✅ **Email Processing** - AI extracts price changes from supplier emails
2. ✅ **Epicor Integration** - Create parts and update prices via REST API v2
3. ✅ **Multi-user Support** - Multiple users can login with Microsoft accounts
4. ✅ **Test Part Created** - `TEST-001` with price $125.00 (updated from $100.00)

---

## 🔧 Current Issue: Session Expired

**Error:** `401 Unauthorized` when fetching messages

**Cause:** Your Microsoft authentication token has expired

**Fix:** Restart the application and login again

---

## 🎯 How to Use the System

### **Step 1: Start the Application**

```bash
python start.py
```

### **Step 2: Login**

1. Open browser: `http://localhost:8000`
2. Click **"Sign in with Microsoft"**
3. Login with your Microsoft account
4. Grant permissions

### **Step 3: Process Emails**

**Option A: Wait for Real Email**
- Send yourself a test email with price changes
- Wait 3 minutes for delta service to poll
- Email will appear in dashboard

**Option B: Test with Existing Part**

1. Go to dashboard
2. Find an email with part number `TEST-001`
3. Click on the email
4. Click **"🤖 Extract Information"**
5. Review extracted data
6. Click **"🔄 Update Prices in Epicor ERP"**
7. Verify in Epicor that price was updated

---

## 📧 Test Email Format

Send yourself an email like this:

**Subject:** `Price Update - TEST-001`

**Body:**
```
Dear Customer,

We are updating our prices effective immediately:

Product: Test Part for Email Integration
Part Number: TEST-001
Old Price: $125.00
New Price: $150.00
Effective Date: Immediate

Please update your records accordingly.

Best regards,
Supplier Name
```

---

## 🔧 Epicor Integration

### **Create a New Test Part**

```bash
python create_test_part.py
```

Follow the prompts:
- Part Number: `TEST-002`
- Description: `Another Test Part`
- Part Type: `P` (Purchased)
- Price: `200.00`
- Part Class: `R150` (OTHER)
- Product Group: `CF030025` (CF - UNASSIGNED)

### **Update Part Price Directly**

```bash
python test_price_update.py
```

Enter:
- Part Number: `TEST-001`
- New Price: `150.00`

### **View Available Part Classes**

```bash
python get_part_classes.py
```

Shows all 87 Part Classes in your Epicor system.

### **View Available Product Groups**

```bash
python get_product_groups.py
```

Shows all 100 Product Groups in your Epicor system.

---

## 🔐 Authentication

### **Microsoft Graph API**
- Uses OAuth 2.0 with delegated permissions
- Tokens are cached per user
- Automatically refreshes when possible
- **If expired:** Logout and login again

### **Epicor API**
- Uses Bearer Token + X-api-Key authentication
- Token expires every 60 minutes
- **Manual refresh required** (automatic OAuth not enabled yet)
- See `AUTO_TOKEN_GUIDE.md` for automatic token setup

---

## 📁 Project Structure

```
email-agent/
├── start.py                    # Main FastAPI application
├── services/
│   ├── epicor_service.py      # Epicor API integration
│   ├── epicor_auth.py         # Epicor OAuth (not working yet)
│   └── delta_service.py       # Email polling service
├── auth/
│   ├── oauth.py               # Microsoft OAuth
│   └── multi_graph.py         # Microsoft Graph API client
├── templates/
│   ├── login.html             # Login page
│   ├── dashboard.html         # Email list
│   └── email_details.html     # Email details + Epicor update
├── create_test_part.py        # Create parts in Epicor
├── test_price_update.py       # Test price updates
├── get_part_classes.py        # List Part Classes
└── get_product_groups.py      # List Product Groups
```

---

## 🐛 Troubleshooting

### **"401 Unauthorized" Error**

**Solution:** Restart the app and login again
```bash
# Press Ctrl+C to stop
python start.py
# Go to http://localhost:8000 and login
```

### **"Part not found" Error**

**Solution:** Create the part first
```bash
python create_test_part.py
```

### **"Part Class required" Error**

**Solution:** Specify Part Class when creating part
- Use `R150` (OTHER) for generic parts
- Run `python get_part_classes.py` to see all options

### **"Product Group required" Error**

**Solution:** Specify Product Group when creating part
- Use `CF030025` (CF - UNASSIGNED) for generic parts
- Run `python get_product_groups.py` to see all options

### **Epicor Bearer Token Expired**

**Solution:** Update token manually
1. Open Epicor REST API Help in browser
2. Open DevTools (F12) → Network tab
3. Make any API call
4. Copy Bearer token from Authorization header
5. Update `.env` file:
   ```env
   EPICOR_BEARER_TOKEN=<new_token_here>
   ```
6. Restart the app

---

## 📊 Current Configuration

### **Epicor Settings** (from `.env`)
- Base URL: `https://centralusdtadtl26.epicorsaas.com/saas5393third/api/v2/odata`
- Company ID: `165122`
- API Key: `K9mqSIYKlSX5mMjECaSOZEqu0p9UvdyUaDqXhq9vXLewQ`
- Authentication: Bearer Token + X-api-Key

### **Test Part**
- Part Number: `TEST-001`
- Description: `Test Part for Email Integration`
- Part Type: `P` (Purchased)
- Part Class: `R150` (OTHER)
- Product Group: `CF030025` (CF - UNASSIGNED)
- Current Price: `$125.00`

---

## 🎉 Next Steps

1. **Restart the application** to fix the 401 error
2. **Login again** at `http://localhost:8000`
3. **Send a test email** with `TEST-001` price change
4. **Process the email** and update price in Epicor
5. **Verify in Epicor** that the price was updated

---

## 📚 Additional Documentation

- `AUTO_TOKEN_GUIDE.md` - How to enable automatic Epicor token generation
- `EPICOR_INTEGRATION.md` - Complete Epicor integration guide
- `INTEGRATION_SUMMARY.md` - Implementation overview

---

## 💡 Tips

- **Email polling:** Runs every 3 minutes automatically
- **Multiple parts:** You can update multiple parts in one email
- **Price format:** AI understands various formats ($100, 100.00, USD 100)
- **Part numbers:** Must match exactly (case-sensitive)
- **Verification:** Always verify in Epicor after updates

---

**Need help?** Check the error messages in the terminal where `python start.py` is running.

