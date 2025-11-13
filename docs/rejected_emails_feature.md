# Rejected Emails Tab - Feature Documentation

## Overview

The **Rejected Emails** tab allows users to view all emails that have been manually rejected during the verification process. This provides an audit trail and allows users to review their rejection decisions.

---

## Feature Details

### What Are Rejected Emails?

Rejected emails are emails from **unverified vendors** that users have chosen to **skip/ignore** during the manual approval process. When an email is rejected:

- ❌ **NO LLM detection runs** (saves API costs)
- ❌ **NO extraction runs** (saves API costs)
- 📁 Basic metadata is kept for audit purposes
- 🚫 Email is hidden from active processing lists

---

## API Endpoints

### 1. Get Rejected Emails

**Endpoint:** `GET /api/emails/rejected`

**Description:** Retrieves all rejected emails for the authenticated user

**Response:**
```json
{
  "emails": [
    {
      "message_id": "AAMkADU...",
      "subject": "Marketing Newsletter - March 2024",
      "sender": "marketing@company.com",
      "date": "2024-03-15T10:30:00Z",
      "verification_status": "rejected",
      "rejected_reason": "Spam email - not relevant to pricing",
      "rejected_by": "user@mycompany.com",
      "rejected_at": "2024-03-15T11:00:00Z",
      "vendor_verified": false
    },
    {
      "message_id": "AAMkADV...",
      "subject": "Personal Email",
      "sender": "friend@example.com",
      "date": "2024-03-14T09:00:00Z",
      "verification_status": "rejected",
      "rejected_reason": "Manually rejected by user",
      "rejected_by": "user@mycompany.com",
      "rejected_at": "2024-03-14T09:30:00Z",
      "vendor_verified": false
    }
  ],
  "total": 2
}
```

**Features:**
- ✅ Sorted by rejection date (most recent first)
- ✅ Includes rejection reason and user who rejected
- ✅ Shows original email metadata

---

### 2. Reject an Email (Enhanced)

**Endpoint:** `POST /api/emails/{message_id}/reject`

**Description:** Reject an email with optional reason

**Request Body (Optional):**
```json
{
  "reason": "Spam email - not relevant to pricing"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email rejected successfully",
  "rejected_by": "user@mycompany.com",
  "rejected_reason": "Spam email - not relevant to pricing"
}
```

**Default Reason:** If no reason provided: `"Manually rejected by user"`

---

## Email State Changes

### State Fields for Rejected Emails

When an email is rejected, the following state is stored:

```json
{
  "verification_status": "rejected",
  "processed": true,
  "processed_at": "2024-03-15T11:00:00Z",
  "rejected_at": "2024-03-15T11:00:00Z",
  "rejected_by": "user@mycompany.com",
  "rejected_reason": "Spam email - not relevant to pricing",
  "vendor_verified": false,
  "awaiting_llm_detection": false,
  "llm_detection_performed": false
}
```

### State Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| **verification_status** | string | Set to `"rejected"` |
| **processed** | boolean | Set to `true` (email has been reviewed) |
| **processed_at** | ISO datetime | When email was rejected |
| **rejected_at** | ISO datetime | When email was rejected (same as processed_at) |
| **rejected_by** | string | Email of user who rejected it |
| **rejected_reason** | string | Why it was rejected (user-provided or default) |
| **vendor_verified** | boolean | Always `false` (unverified vendor) |
| **awaiting_llm_detection** | boolean | Set to `false` (won't run LLM) |
| **llm_detection_performed** | boolean | Set to `false` (never ran LLM) |

---

## User Workflow

### Step-by-Step Flow

```
1. User receives email from unverified vendor
   ↓
2. Email appears in "Pending Verification" tab
   ↓
3. User reviews email and clicks "Reject"
   ↓
4. Optional: User provides reason for rejection
   ↓
5. Email marked as rejected
   ↓
6. Email removed from "Pending Verification" tab
   ↓
7. Email now appears in "Rejected Emails" tab
```

### Dashboard Tabs

| Tab | Shows | Purpose |
|-----|-------|---------|
| **All Emails** | All processed price changes | Main view of extracted emails |
| **Pending Verification** | Unverified emails awaiting approval | Action required from user |
| **Rejected Emails** | All rejected emails | Audit trail and review |

---

## Use Cases

### 1. Spam Filtering
```
Email: "Buy Cheap Products Now!"
Action: Reject with reason "Spam email"
Result: Saved $0.01-0.03 in API costs
```

### 2. Personal Emails
```
Email: Personal message from friend
Action: Reject with reason "Personal email, not business"
Result: Keeps dashboard clean, saves costs
```

### 3. Marketing Newsletters
```
Email: "Check out our spring sale!"
Action: Reject with reason "Marketing newsletter"
Result: Prevents clutter in processed emails
```

### 4. Duplicate Emails
```
Email: Same supplier email received twice
Action: Reject with reason "Duplicate - already processed"
Result: Avoids duplicate processing
```

### 5. Mis-categorized Emails
```
Email: Support ticket response
Action: Reject with reason "Not a price change - support email"
Result: Keeps only relevant price change emails
```

---

## Cost Savings

### Per Rejected Email

**Without Rejection Feature:**
- LLM Detection: $0.01
- LLM Extraction (if detected): $0.02
- **Total: $0.01-0.03 per spam email**

**With Rejection Feature:**
- Cost: **$0.00** (no API calls)
- **Savings: 100% for rejected emails**

### Example Scenario

**Assumptions:**
- 100 emails/day received
- 30 from unverified vendors
- User rejects 20 as spam/irrelevant
- User approves 10 for processing

**Old Approach (no rejection, all processed):**
- 30 emails × $0.01 = $0.30/day (detection)
- 20 emails × $0.02 = $0.40/day (extraction on spam)
- **Total: $0.70/day = $255.50/year wasted on spam**

**New Approach (with rejection):**
- 10 approved emails × $0.01 = $0.10/day (detection)
- 10 approved emails × $0.02 = $0.20/day (extraction)
- 20 rejected emails × $0.00 = $0.00/day (no cost)
- **Total: $0.30/day = $109.50/year**
- **Savings: $146/year (57% reduction on unverified emails)**

---

## Audit Trail Benefits

### Why Keep Rejected Emails?

1. **Accountability** - Track who rejected what and why
2. **Mistake Recovery** - Review if email was wrongly rejected
3. **Pattern Analysis** - Identify common spam sources
4. **Compliance** - Audit trail for business decisions
5. **Training** - Learn what types of emails to filter

### What's Stored?

✅ **Stored:**
- Email subject, sender, date
- Rejection reason and user
- Rejection timestamp
- Original email metadata

❌ **NOT Stored:**
- Email body content (unless needed for audit)
- Attachments (not downloaded for rejected emails)
- LLM analysis results (never performed)

---

## Frontend Integration

### Example UI Components

#### Rejected Emails Tab

```
╔════════════════════════════════════════════════════════════╗
║ REJECTED EMAILS (20)                                       ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║ From: marketing@company.com                                ║
║ Subject: Spring Sale - 50% Off!                            ║
║ Date: Mar 15, 2024 10:30 AM                                ║
║ Rejected By: user@mycompany.com                            ║
║ Rejected At: Mar 15, 2024 11:00 AM                         ║
║ Reason: Marketing newsletter - not relevant                ║
║ [View Details] [Delete Permanently]                        ║
║                                                            ║
║────────────────────────────────────────────────────────────║
║                                                            ║
║ From: friend@example.com                                   ║
║ Subject: Hey, are you free this weekend?                   ║
║ Date: Mar 14, 2024 09:00 AM                                ║
║ Rejected By: user@mycompany.com                            ║
║ Rejected At: Mar 14, 2024 09:30 AM                         ║
║ Reason: Personal email, not business                       ║
║ [View Details] [Delete Permanently]                        ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

#### Reject Modal (When Rejecting Email)

```
╔════════════════════════════════════════╗
║ Reject Email                           ║
╠════════════════════════════════════════╣
║                                        ║
║ Are you sure you want to reject this  ║
║ email?                                 ║
║                                        ║
║ From: unknown@vendor.com               ║
║ Subject: Price Update                  ║
║                                        ║
║ Reason (Optional):                     ║
║ ┌────────────────────────────────────┐ ║
║ │ Spam email - not relevant          │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║ Common reasons:                        ║
║ • Spam email                           ║
║ • Personal email                       ║
║ • Marketing newsletter                 ║
║ • Duplicate email                      ║
║ • Not a price change                   ║
║                                        ║
║ [Cancel]  [Reject Email]               ║
╚════════════════════════════════════════╝
```

---

## API Usage Examples

### Get Rejected Emails

```javascript
// Fetch rejected emails
const response = await fetch('/api/emails/rejected', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer <token>'
  }
});

const data = await response.json();
console.log(`Found ${data.total} rejected emails`);

data.emails.forEach(email => {
  console.log(`${email.subject} - Rejected: ${email.rejected_reason}`);
});
```

### Reject Email Without Reason

```javascript
// Simple rejection
const response = await fetch('/api/emails/ABC123/reject', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer <token>'
  }
});

const result = await response.json();
// result.rejected_reason = "Manually rejected by user"
```

### Reject Email With Reason

```javascript
// Rejection with custom reason
const response = await fetch('/api/emails/ABC123/reject', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer <token>'
  },
  body: JSON.stringify({
    reason: "Spam email - not relevant to pricing"
  })
});

const result = await response.json();
console.log(result.rejected_reason); // "Spam email - not relevant to pricing"
```

---

## Future Enhancements

### Potential Features

1. **Bulk Reject** - Reject multiple emails at once
   ```javascript
   POST /api/emails/bulk-reject
   Body: {
     "message_ids": ["ABC", "DEF", "GHI"],
     "reason": "Spam emails"
   }
   ```

2. **Undo Rejection** - Restore rejected email to pending
   ```javascript
   POST /api/emails/{message_id}/restore
   ```

3. **Delete Permanently** - Remove rejected email from system
   ```javascript
   DELETE /api/emails/{message_id}
   ```

4. **Block Sender** - Auto-reject future emails from sender
   ```javascript
   POST /api/emails/{message_id}/reject-and-block
   ```

5. **Rejection Templates** - Pre-defined rejection reasons
   ```javascript
   GET /api/emails/rejection-templates
   Response: ["Spam", "Personal", "Marketing", "Duplicate", "Other"]
   ```

6. **Rejection Statistics** - Analytics on rejection patterns
   ```javascript
   GET /api/emails/rejection-stats
   Response: {
     "total_rejected": 150,
     "by_reason": {
       "Spam": 80,
       "Personal": 30,
       "Marketing": 25,
       "Other": 15
     }
   }
   ```

---

## Testing Checklist

### Manual Testing

- [ ] Reject email without reason → Shows default reason
- [ ] Reject email with custom reason → Shows custom reason
- [ ] View rejected emails tab → Shows all rejected emails
- [ ] Rejected emails sorted by date → Most recent first
- [ ] Rejected email shows correct metadata → Subject, sender, date
- [ ] Rejected email shows rejection info → Who rejected, when, why
- [ ] Rejected email not in "Pending Verification" → Removed after rejection
- [ ] Rejected email not in "All Emails" → Only shows processed price changes
- [ ] Try to approve rejected email → Returns error (not pending)
- [ ] Try to reject already rejected email → Returns error

### API Testing

```bash
# Get rejected emails
curl -X GET http://localhost:8000/api/emails/rejected \
  -H "Cookie: session=..."

# Reject email without reason
curl -X POST http://localhost:8000/api/emails/ABC123/reject \
  -H "Cookie: session=..."

# Reject email with reason
curl -X POST http://localhost:8000/api/emails/ABC123/reject \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"reason":"Spam email"}'
```

---

## Summary

### What Was Added

1. ✅ **GET /api/emails/rejected** - List all rejected emails
2. ✅ **Enhanced reject endpoint** - Accept optional rejection reason
3. ✅ **Enhanced email state** - Track rejection details
4. ✅ **Audit trail** - Full rejection history

### Benefits

- 💰 **Cost savings** - $0.00 per rejected email (vs $0.01-0.03)
- 📊 **Transparency** - Know who rejected what and why
- 🔍 **Audit trail** - Review rejection decisions
- 🧹 **Clean dashboard** - Only relevant emails in active lists
- ⚡ **Fast rejection** - Instant, no API calls

### User Experience

- Simple "Reject" button in pending verification tab
- Optional reason field for clarity
- Dedicated "Rejected Emails" tab for review
- Clear indication of who rejected and why
- Sorted by date for easy review

---

**Version**: 2.2 (Rejected Emails Feature)
**Date**: 2025-03-15
**Status**: Implemented and Ready for Testing
