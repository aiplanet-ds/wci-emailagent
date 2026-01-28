"""
Test: Initial delta sync applies 14-day filter for new users.

This test verifies that when a user has NO delta token (first login),
the Graph API call includes a $filter on receivedDateTime to limit
emails to the last 14 days. It also verifies that returning users
(who have a delta token) skip the filter entirely.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_initial_sync_has_14_day_filter():
    """New user (no delta token) should filter emails to last 14 days"""

    captured_params = {}

    async def mock_get(url, headers=None, params=None):
        captured_params["url"] = url
        captured_params["params"] = params
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "value": [],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta-token-abc"
        }
        return mock_response

    async def run():
        with patch("auth.multi_graph.HTTPClientManager") as mock_http, \
             patch("auth.multi_graph.multi_auth") as mock_auth:

            mock_auth.get_user_token.return_value = "fake-token-123"

            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_http.get_graph_client = AsyncMock(return_value=mock_client)

            from auth.multi_graph import MultiUserGraphClient
            client = MultiUserGraphClient()
            client.auth = mock_auth

            # Call WITHOUT delta token (simulates new user)
            result = await client.get_user_delta_messages("newuser@test.com", delta_token=None)

            # 1) Check that $filter was included in params
            assert captured_params["params"] is not None, "FAIL: No params sent on initial sync"
            assert "$filter" in captured_params["params"], "FAIL: $filter missing from initial sync"

            # 2) Check filter uses receivedDateTime ge
            filter_value = captured_params["params"]["$filter"]
            assert "receivedDateTime ge" in filter_value, f"FAIL: Expected 'receivedDateTime ge' in filter, got: {filter_value}"

            # 3) Check the cutoff date is approximately 14 days ago
            date_str = filter_value.replace("receivedDateTime ge ", "")
            cutoff = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            expected_cutoff = datetime.utcnow() - timedelta(days=14)
            diff = abs((cutoff - expected_cutoff).total_seconds())
            assert diff < 60, f"FAIL: Cutoff date off by {diff}s (expected ~14 days ago)"

            # 4) Check the URL targets inbox delta
            assert "mailFolders/inbox/messages/delta" in captured_params["url"], \
                f"FAIL: Wrong URL: {captured_params['url']}"

            # 5) Check $select is still present
            assert "$select" in captured_params["params"], "FAIL: $select missing from initial sync"

            print("PASS: Initial sync (new user) includes 14-day filter")
            print(f"  Filter: {filter_value}")
            print(f"  URL: {captured_params['url']}")
            return True

    return asyncio.run(run())


def test_returning_user_uses_delta_token_without_filter():
    """Returning user (has delta token) should NOT apply any filter"""

    captured_params = {}

    async def mock_get(url, headers=None, params=None):
        captured_params["url"] = url
        captured_params["params"] = params
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "value": [],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta-token-xyz"
        }
        return mock_response

    async def run():
        with patch("auth.multi_graph.HTTPClientManager") as mock_http, \
             patch("auth.multi_graph.multi_auth") as mock_auth:

            mock_auth.get_user_token.return_value = "fake-token-123"

            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_http.get_graph_client = AsyncMock(return_value=mock_client)

            from auth.multi_graph import MultiUserGraphClient
            client = MultiUserGraphClient()
            client.auth = mock_auth

            # Call WITH delta token (simulates returning user)
            existing_token = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=old-token-123"
            result = await client.get_user_delta_messages("returning@test.com", delta_token=existing_token)

            # 1) URL should be the delta token itself
            assert captured_params["url"] == existing_token, \
                f"FAIL: Expected delta token URL, got: {captured_params['url']}"

            # 2) No params should be sent (no $filter)
            assert captured_params["params"] is None, \
                f"FAIL: Params should be None for returning user, got: {captured_params['params']}"

            print("PASS: Returning user uses delta token without filter")
            print(f"  URL: {captured_params['url']}")
            print(f"  Params: {captured_params['params']}")
            return True

    return asyncio.run(run())


if __name__ == "__main__":
    print("=" * 60)
    print("Testing initial sync 14-day filter safeguard")
    print("=" * 60)

    results = []

    print("\nTest 1: New user gets 14-day filter")
    print("-" * 40)
    try:
        results.append(test_initial_sync_has_14_day_filter())
    except Exception as e:
        print(f"FAIL: {e}")
        results.append(False)

    print("\nTest 2: Returning user skips filter")
    print("-" * 40)
    try:
        results.append(test_returning_user_uses_delta_token_without_filter())
    except Exception as e:
        print(f"FAIL: {e}")
        results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    if all(results):
        print("All tests PASSED")
    else:
        print("Some tests FAILED")
        sys.exit(1)
