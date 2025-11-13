# LLM-Powered Price Change Detection

## Overview

The WCI Email Agent now uses **LLM-powered detection** instead of keyword-based filtering to identify supplier price change notifications. This provides more accurate, context-aware detection that understands the semantic meaning of emails rather than relying on rigid keyword matching.

## Architecture

### Previous Architecture (Keyword-Based)
```
Email → [Keyword Matching] → [Confirmation Check] → [LLM Extraction] → Processed
         (Stage 1)              (Stage 2)             (Stage 3)
```

### New Architecture (LLM-Powered)
```
Email → [LLM Detection with Confidence] → [Vendor Verification] → [LLM Extraction] → Processed
         (Separate from Extraction)
```

## Key Features

### 1. Semantic Understanding
- Analyzes the **meaning and context** of emails, not just keywords
- Detects subtle price change notifications written in various styles
- Distinguishes between price changes vs invoices, quotes, marketing emails

### 2. Confidence Scoring
- Returns confidence scores from **0.0 to 1.0**
- Configurable threshold (default: **0.75**)
- Provides reasoning for each decision

### 3. Full Content Analysis
- Analyzes complete email body
- Processes all attachments (PDF, Excel, Word, TXT)
- Considers email metadata (subject, sender, date)

### 4. Separate Detection and Extraction
- **Detection**: Identifies if email is a price change (llm_detector.py)
- **Extraction**: Extracts structured data from confirmed emails (extractor.py)
- Clear separation of concerns for better maintainability

## Components

### 1. LLM Detector Service
**File**: `services/llm_detector.py`

**Main Function**: `llm_is_price_change_email(email_content, metadata, confidence_threshold)`

**Returns**:
```python
{
  "is_price_change": bool,        # Whether email is a price change
  "confidence": float,             # Confidence score (0.0 - 1.0)
  "reasoning": str,                # Brief explanation of decision
  "meets_threshold": bool,         # Whether confidence >= threshold
  "error": str (optional)          # Error message if detection failed
}
```

**Example Usage**:
```python
from services.llm_detector import llm_is_price_change_email

result = llm_is_price_change_email(email_content, metadata)

if result["meets_threshold"]:
    print(f"Price change detected! Confidence: {result['confidence']:.2%}")
    print(f"Reasoning: {result['reasoning']}")
```

### 2. Integration with Delta Service
**File**: `services/delta_service.py`

**Updated Method**: `is_price_change_email(user_email, message)`

The delta service now:
1. Fetches full email content with attachments
2. Calls LLM detector for analysis
3. Logs confidence scores and reasoning
4. Only processes emails meeting confidence threshold

### 3. Configuration
**File**: `.env.template` (and your `.env`)

```bash
# LLM Price Change Detection Configuration
PRICE_CHANGE_CONFIDENCE_THRESHOLD=0.75
```

**Threshold Guidelines**:
- **0.65**: Lenient - catches more emails, may include borderline cases
- **0.75**: Balanced (default) - good accuracy with few false positives
- **0.85**: Strict - very high precision, may miss subtle notifications

## LLM Detection Logic

### What the LLM Looks For

**Positive Indicators** (Price Change Notification):
- Supplier/vendor announcing price changes
- New price lists, rate revisions, cost updates
- Price adjustments with effective dates
- Formal price change notifications
- Catalog updates with new pricing

**Negative Indicators** (NOT a Price Change):
- Invoices, receipts, billing statements
- Purchase orders, order confirmations
- Marketing emails, newsletters, promotions
- Internal company emails
- Delivery notifications, shipment tracking
- Quote requests from customers

### Example Prompts

The LLM receives:
1. **Email metadata** (subject, sender, date, has_attachments)
2. **Full email content** (body + attachments)
3. **Instructions** on what constitutes a price change notification

The LLM returns:
- Binary decision (is/isn't price change)
- Confidence score with reasoning
- JSON format for easy parsing

## Benefits Over Keyword Detection

### 1. Higher Accuracy
- Understands context, not just keywords
- Detects subtle or unusual phrasing
- Handles multiple languages and writing styles

### 2. Fewer False Positives
- Distinguishes invoices from price changes
- Recognizes marketing emails vs supplier notifications
- Understands document type and intent

### 3. Fewer False Negatives
- Catches price changes without obvious keywords
- Detects implied price changes ("updated catalog", "new rates")
- Handles informal language

### 4. No Keyword Maintenance
- No need to update keyword lists
- Automatically adapts to new phrasing
- Handles domain-specific terminology

### 5. Transparency
- Provides reasoning for each decision
- Confidence scores enable threshold tuning
- Easy to debug and understand decisions

## Testing

### Automated Test Suite
**File**: `test_llm_detection.py`

Run comprehensive tests:
```bash
python test_llm_detection.py
```

This tests 6 email scenarios:
1. ✅ Clear price change notification
2. ❌ Invoice (not a price change)
3. ✅ Subtle price change (testing LLM understanding)
4. ❌ Order confirmation (not a price change)
5. ❌ Marketing newsletter with prices
6. ✅ Formal price increase letter

### Custom Email Testing
Test your own emails interactively:
```bash
python test_llm_detection.py
# Select option 2
```

## Performance Considerations

### API Costs
- Each detection requires 1 Azure OpenAI API call
- Uses GPT-4 with low token usage (~500 tokens per email)
- More expensive than keyword matching but more accurate

### Speed
- Detection takes 1-3 seconds per email (API latency)
- Slower than instant keyword matching
- Acceptable for email polling workflows (1 minute intervals)

### Optimization Tips
1. **Cache detection results** for processed emails
2. **Batch process** emails when possible
3. **Monitor confidence scores** to tune threshold
4. **Use lower temperature** (0.2) for consistency

## Monitoring and Logging

The system logs:
- Detection results with confidence scores
- Reasoning for each decision
- Threshold pass/fail status
- API errors and fallback behavior

Example log output:
```
🤖 Analyzing with LLM detector...
✅ PRICE CHANGE DETECTED (Confidence: 0.92)
💡 Reasoning: Email from supplier announcing new pricing effective April 1st
```

## Troubleshooting

### Low Accuracy
- **Adjust threshold**: Lower threshold (e.g., 0.65) to catch more emails
- **Check prompt**: Ensure LLM prompt is up to date
- **Review logs**: Analyze reasoning for incorrect detections

### API Errors
- **Check credentials**: Verify Azure OpenAI API key and endpoint
- **Check rate limits**: Ensure not exceeding API quotas
- **Check deployment**: Verify GPT-4 deployment name

### High Costs
- **Increase threshold**: Reduce false positives (fewer extractions)
- **Monitor usage**: Track API calls in Azure portal
- **Consider hybrid**: Add quick pre-filter for obvious non-matches

## Migration from Keyword Detection

If you're migrating from the old keyword-based system:

1. **No action required** - the code has been updated automatically
2. **Add config**: Set `PRICE_CHANGE_CONFIDENCE_THRESHOLD` in your `.env`
3. **Monitor results**: Watch logs to ensure detection is working well
4. **Tune threshold**: Adjust based on your email patterns
5. **Test thoroughly**: Use test suite to validate accuracy

## Future Enhancements

Potential improvements:
1. **Caching**: Cache detection results for duplicate emails
2. **Batch API**: Process multiple emails in single API call
3. **Fine-tuning**: Train custom model for specific domain
4. **Hybrid mode**: Keyword pre-filter + LLM confirmation
5. **Confidence calibration**: Automatically tune threshold based on user feedback

## Support

For issues or questions:
1. Check logs for detection reasoning
2. Run test suite to validate setup
3. Review API credentials and configuration
4. Adjust confidence threshold if needed
5. Report issues with example emails and expected behavior

---

**Last Updated**: 2024-03-15
**Version**: 2.0 (LLM Detection)
