# Router Endpoint Migration Progress

**Date:** 2025-10-30
**Status:** ✅ Core Endpoints Started, 📝 Template Provided for Remaining

---

## ✅ Completed So Far

### Helper Functions (4 functions)
1. ✅ **`get_user_from_db()`** - NEW: Get user from database with 404 handling
2. ✅ **`get_email_from_db()`** - NEW: Get email from database with 404 handling
3. ✅ **`get_all_price_change_emails_from_db()`** - NEW: Database version with filtering
4. ✅ **Old functions marked as legacy** - Kept for backwards compatibility

### API Endpoints
1. ✅ **`list_emails()` - GET /api/emails** - Fully migrated to database
   - Added `db: AsyncSession = Depends(get_db)` dependency
   - Uses `get_all_price_change_emails_from_db()` for database queries
   - Supports filtering (processed, unprocessed, pending_verification, etc.)
   - Supports search by subject/sender
   - Returns data from `emails`, `email_states`, and `epicor_sync_results` tables

---

## 📋 Remaining Endpoints to Migrate (15 endpoints)

### Pattern for Migration

All endpoints follow this pattern:
```python
# OLD:
@router.get("/endpoint")
async def endpoint_name(request: Request):
    user_email = get_user_from_session(request)
    # Load from JSON files...

# NEW:
@router.get("/endpoint")
async def endpoint_name(
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD THIS
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)  # ADD THIS
    # Query from database...
```

---

## 🔧 Endpoints Needing Updates

### 1. `get_email_detail()` - GET /api/emails/{message_id}
**Current:** Reads from `price_change_{message_id}.json` and `epicor_update_{message_id}.json`

**Changes Needed:**
```python
@router.get("/{message_id}", response_model=EmailDetailResponse)
async def get_email_detail(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Get email from database
    email = await get_email_from_db(db, message_id)

    # Get state
    state = await EmailStateService.get_state_by_message_id(db, message_id)

    # Get Epicor sync result
    epicor_result = await EpicorSyncResultService.get_sync_result_by_email_id(db, email.id)

    # Build response
    email_data = {
        "supplier_info": email.supplier_info,
        "price_change_summary": email.price_change_summary,
        "affected_products": email.affected_products,
        "additional_details": email.additional_details,
        "email_metadata": {
            "subject": email.subject,
            "sender": email.sender_email,
            "date": email.received_at.isoformat() if email.received_at else None,
            "message_id": email.message_id
        }
    }

    validation = validation_service.validate_email_data(email_data)

    return {
        "email_data": email_data,
        "state": {
            "processed": state.processed if state else False,
            "verification_status": state.verification_status if state else None,
            ...
        },
        "validation": validation,
        "epicor_status": {
            "successful": epicor_result.successful_updates,
            "failed": epicor_result.failed_updates,
            "total": epicor_result.total_products,
            ...
        } if epicor_result else None
    }
```

---

### 2. `update_email_state()` - PATCH /api/emails/{message_id}
**Current:** Reads/writes JSON files, updates `email_states.json`, creates `epicor_update_{message_id}.json`

**Changes Needed:**
```python
@router.patch("/{message_id}")
async def update_email_state(
    message_id: str,
    update: EmailStateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    email = await get_email_from_db(db, message_id)

    if update.processed:
        # Sync to Epicor
        epicor_service = EpicorAPIService()
        result = epicor_service.sync_price_change_to_epicor(...)

        # Save Epicor result to database (NOT JSON file)
        await EpicorSyncResultService.create_sync_result(
            db=db,
            email_id=email.id,
            user_id=user.id,
            sync_status="success" if result["success"] else "failed",
            total_products=len(...),
            successful_updates=result["successful"],
            failed_updates=result["failed"],
            results_summary=result
        )

        # Update email state
        await EmailStateService.mark_as_processed(db, message_id, user.id)
        await EmailStateService.mark_epicor_synced(db, message_id)

        await db.commit()

    return {"status": "updated"}
```

---

### 3. `generate_followup()` - POST /api/emails/{message_id}/followup
**Current:** Reads from JSON, saves followup draft to `email_states.json`

**Changes Needed:**
```python
@router.post("/{message_id}/followup")
async def generate_followup(
    message_id: str,
    followup_request: FollowupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    email = await get_email_from_db(db, message_id)

    # Generate followup email
    email_data = {
        "supplier_info": email.supplier_info,
        "affected_products": email.affected_products,
        ...
    }
    draft = generate_followup_email(email_data, followup_request.missing_fields)

    # Save to database (NOT JSON file)
    await EmailStateService.set_followup_info(
        db=db,
        message_id=message_id,
        followup_draft=draft,
        missing_fields=followup_request.missing_fields
    )

    await db.commit()

    return {"draft": draft}
```

---

### 4. `list_pending_verification_emails()` - GET /api/emails/pending-verification
**Current:** Scans JSON files, filters by `verification_status`

**Changes Needed:**
```python
@router.get("/pending-verification")
async def list_pending_verification_emails(
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    # Query database for pending verification
    emails = await get_all_price_change_emails_from_db(
        db=db,
        user_id=user.id,
        filter_type="pending_verification"
    )

    return {"emails": emails, "total": len(emails)}
```

---

### 5. `approve_and_process_email()` - POST /api/emails/{message_id}/approve-and-process
**Current:** Complex - reads JSON, runs LLM detection, updates state, saves JSON

**Changes Needed:**
```python
@router.post("/{message_id}/approve-and-process")
async def approve_and_process_email(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    email = await get_email_from_db(db, message_id)
    state = await EmailStateService.get_state_by_message_id(db, message_id)

    if not state or state.verification_status != "pending_review":
        raise HTTPException(400, "Email not pending verification")

    # Mark as manually approved
    await EmailStateService.manually_approve(db, message_id, user.id)

    # Run LLM detection (if not done)
    if not state.llm_detection_performed:
        # Fetch full email from Graph API
        graph_client = MultiUserGraphClient()
        full_message = graph_client.get_user_message_by_id(user_email, message_id)

        # Run LLM detection
        from services.llm_detector import llm_is_price_change_email
        detection_result = llm_is_price_change_email(full_message)

        # Update state
        await EmailStateService.update_llm_detection(
            db=db,
            message_id=message_id,
            is_price_change=detection_result["is_price_change"],
            confidence=detection_result["confidence"],
            reasoning=detection_result["reasoning"]
        )

    # If price change, process with main.process_user_message()
    if state.is_price_change:
        from main import process_user_message
        full_message = graph_client.get_user_message_by_id(user_email, message_id)
        await asyncio.to_thread(process_user_message, full_message, user_email, skip_verification=True)

    await db.commit()

    return {"status": "approved and processed"}
```

---

### 6. `reject_email()` - POST /api/emails/{message_id}/reject
**Current:** Updates `email_states.json`

**Changes Needed:**
```python
@router.post("/{message_id}/reject")
async def reject_email(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD
):
    user_email = get_user_from_session(request)
    user = await get_user_from_db(db, user_email)

    state = await EmailStateService.get_state_by_message_id(db, message_id)
    if not state:
        raise HTTPException(404, "Email state not found")

    # Update verification status
    state.verification_status = "rejected"
    state.vendor_verified = False

    await db.commit()

    return {"status": "rejected"}
```

---

### 7. `get_vendor_cache_status()` - GET /api/emails/vendors/cache-status
**Current:** Calls `vendor_verification_service.get_cache_status()` which reads JSON

**Changes Needed:**
```python
@router.get("/vendors/cache-status")
async def get_vendor_cache_status(
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD (optional, service handles it)
):
    # Vendor service already migrated - just call it
    status = await vendor_verification_service.get_cache_status()
    return status
```

---

### 8. `refresh_vendor_cache()` - POST /api/emails/vendors/refresh-cache
**Current:** Calls `vendor_verification_service.refresh_cache()` which writes JSON

**Changes Needed:**
```python
@router.post("/vendors/refresh-cache")
async def refresh_vendor_cache(
    request: Request,
    db: AsyncSession = Depends(get_db)  # ADD (optional, service handles it)
):
    # Vendor service already migrated - just call it
    result = await vendor_verification_service.refresh_cache()
    return result
```

---

### 9-15. Other Endpoints
Similar patterns apply to:
- `get_raw_email_content()` - No database needed (fetches from Graph API)
- `download_attachment()` - No database needed (fetches from Graph API)
- Any other endpoints that read/write email state

---

## 🎯 Key Database Services to Use

### EmailService
```python
from database.services.email_service import EmailService

# Get email
email = await EmailService.get_email_by_message_id(db, message_id)
email = await EmailService.get_email_by_id(db, email_id)
emails = await EmailService.get_emails_by_user(db, user_id)

# Create email (done by main.py)
email = await EmailService.create_email(db, ...)

# Update email
await EmailService.update_email(db, email_id, ...)
```

### EmailStateService
```python
from database.services.email_state_service import EmailStateService

# Get state
state = await EmailStateService.get_state_by_message_id(db, message_id)

# Create state
state = await EmailStateService.create_state(db, message_id, user_id)

# Update state
await EmailStateService.mark_as_processed(db, message_id, processed_by_id)
await EmailStateService.mark_epicor_synced(db, message_id)
await EmailStateService.mark_as_unprocessed(db, message_id)
await EmailStateService.manually_approve(db, message_id, approved_by_id)
await EmailStateService.set_followup_info(db, message_id, draft, missing_fields)
await EmailStateService.update_llm_detection(db, message_id, is_price_change, confidence, reasoning)
```

### EpicorSyncResultService
```python
from database.services.epicor_sync_result_service import EpicorSyncResultService

# Create sync result
result = await EpicorSyncResultService.create_sync_result(
    db=db,
    email_id=email.id,
    user_id=user.id,
    sync_status="success",
    total_products=10,
    successful_updates=9,
    failed_updates=1,
    results_summary={"details": "..."},
    error_message=None
)

# Get sync result
result = await EpicorSyncResultService.get_sync_result_by_email_id(db, email_id)
```

---

## ✅ Testing Migrated Endpoints

After each endpoint migration, test with:

```bash
# List emails
curl -X GET "http://localhost:8000/api/emails?filter=all" \
  --cookie "session=YOUR_SESSION"

# Get email detail
curl -X GET "http://localhost:8000/api/emails/{message_id}" \
  --cookie "session=YOUR_SESSION"

# Update email state
curl -X PATCH "http://localhost:8000/api/emails/{message_id}" \
  -H "Content-Type: application/json" \
  -d '{"processed": true}' \
  --cookie "session=YOUR_SESSION"
```

---

## 📝 Summary

**Completed:**
- ✅ Helper functions
- ✅ `list_emails()` endpoint

**Remaining:** 15 endpoints following the same pattern
**Estimated Time:** 3-4 hours for all remaining endpoints

**Key Steps for Each Endpoint:**
1. Add `db: AsyncSession = Depends(get_db)` parameter
2. Get user from database: `user = await get_user_from_db(db, user_email)`
3. Replace JSON file operations with database queries
4. Replace `email_state_service` (old) with `EmailStateService` (database)
5. Use `EpicorSyncResultService` instead of `epicor_update_{id}.json` files
6. Add `await db.commit()` after updates
7. Test endpoint

**Result:** No more `email_states.json` or `epicor_update_*.json` files!
