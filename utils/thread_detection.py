"""
Thread detection utilities for email conversation tracking.

Provides functions to:
- Detect if an email is a reply or forward from subject line
- Strip Re:/Fwd: prefixes to get the base thread subject
- Extract thread information from Microsoft Graph message data
"""

import re
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ThreadInfo:
    """Contains thread detection results for an email"""
    conversation_id: Optional[str]  # From Microsoft Graph
    conversation_index: Optional[str]  # From Microsoft Graph
    is_reply: bool  # True if detected as reply
    is_forward: bool  # True if detected as forward
    thread_subject: str  # Subject with Re:/Fwd: prefixes stripped


# Regex patterns for detecting reply/forward prefixes
# Supports common patterns: Re:, RE:, re:, Fwd:, FW:, fw:, fwd:
# Also handles localized versions like Re[2]:, Sv:, AW:, etc.
REPLY_PATTERNS = [
    r'^RE:\s*',      # English uppercase
    r'^Re:\s*',      # English title case
    r'^re:\s*',      # English lowercase
    r'^R:\s*',       # Short form
    r'^SV:\s*',      # Swedish/Danish/Norwegian (Svar)
    r'^AW:\s*',      # German (Antwort)
    r'^Odp:\s*',     # Polish (Odpowiedź)
    r'^Re\[\d+\]:\s*',  # Numbered reply (Re[2]:)
]

FORWARD_PATTERNS = [
    r'^FWD:\s*',     # English uppercase
    r'^Fwd:\s*',     # English title case
    r'^fwd:\s*',     # English lowercase
    r'^FW:\s*',      # Short form uppercase
    r'^Fw:\s*',      # Short form title case
    r'^fw:\s*',      # Short form lowercase
    r'^WG:\s*',      # German (Weitergeleitet)
    r'^VS:\s*',      # Swedish/Danish/Norwegian (Videresendt)
    r'^TR:\s*',      # French (Transféré)
    r'^I:\s*',       # Italian (Inoltrato)
]

# Combined pattern for efficient matching
REPLY_REGEX = re.compile('|'.join(REPLY_PATTERNS), re.IGNORECASE)
FORWARD_REGEX = re.compile('|'.join(FORWARD_PATTERNS), re.IGNORECASE)


def strip_subject_prefixes(subject: str) -> str:
    """
    Strip all Re:/Fwd: prefixes from a subject line to get the base thread subject.
    
    Handles multiple nested prefixes (e.g., "Re: Fwd: Re: Original Subject")
    
    Args:
        subject: The email subject line
        
    Returns:
        The cleaned subject with all reply/forward prefixes removed
    """
    if not subject:
        return ""
    
    cleaned = subject.strip()
    
    # Keep stripping prefixes until no more are found
    changed = True
    while changed:
        changed = False
        
        # Try to strip reply prefix
        match = REPLY_REGEX.match(cleaned)
        if match:
            cleaned = cleaned[match.end():].strip()
            changed = True
            continue
            
        # Try to strip forward prefix
        match = FORWARD_REGEX.match(cleaned)
        if match:
            cleaned = cleaned[match.end():].strip()
            changed = True
    
    return cleaned


def detect_thread_info_from_subject(subject: str) -> Dict[str, Any]:
    """
    Detect if an email is a reply or forward based on subject line.
    
    Args:
        subject: The email subject line
        
    Returns:
        Dict with keys: is_reply, is_forward, thread_subject
    """
    if not subject:
        return {
            "is_reply": False,
            "is_forward": False,
            "thread_subject": ""
        }
    
    is_reply = bool(REPLY_REGEX.match(subject.strip()))
    is_forward = bool(FORWARD_REGEX.match(subject.strip()))
    thread_subject = strip_subject_prefixes(subject)
    
    return {
        "is_reply": is_reply,
        "is_forward": is_forward,
        "thread_subject": thread_subject
    }


def extract_thread_info(msg: Dict[str, Any]) -> ThreadInfo:
    """
    Extract complete thread information from a Microsoft Graph message object.
    
    Combines Microsoft Graph threading fields with subject-based detection
    as a fallback.
    
    Args:
        msg: Microsoft Graph message object
        
    Returns:
        ThreadInfo dataclass with all threading fields
    """
    subject = msg.get('subject', '') or ''
    
    # Get Microsoft Graph threading fields
    conversation_id = msg.get('conversationId')
    conversation_index = msg.get('conversationIndex')
    graph_is_reply = msg.get('isReply', False)
    
    # Detect from subject as fallback/supplement
    subject_info = detect_thread_info_from_subject(subject)
    
    # Use Graph API isReply if available, otherwise fall back to subject detection
    is_reply = graph_is_reply if graph_is_reply else subject_info["is_reply"]
    is_forward = subject_info["is_forward"]  # Graph API doesn't have isForward
    thread_subject = subject_info["thread_subject"]
    
    return ThreadInfo(
        conversation_id=conversation_id,
        conversation_index=conversation_index,
        is_reply=is_reply,
        is_forward=is_forward,
        thread_subject=thread_subject
    )

