"""
Unit tests for trips API endpoints - COMPLETE CORRECTED VERSION
Tests CRUD operations using actual /api/v1/trips endpoints.

Note: Trip CREATION is handled by job system, not direct POST endpoint.
All other CRUD operations (Read, Update, Delete) work normally.
"""
import pytest
from unittest.mock import Mock, patch

# Corrected endpoint base
API_BASE = "/api/v1/trips"


# ============================================================================
# Test: List Trips
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_list_trips_authenticated(client, test_db, mock_user_payload):
    """Test retrieving list of user's trips"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.get(
            f"{API_BASE}",
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return trip list (even if empty)
        assert response.status_code == 200
        data = response.json()
        assert "trips" in data
        assert isinstance(data["trips"], list)


@pytest.mark.unit
@pytest.mark.api
def test_list_trips_unauthenticated(client):
    """Test retrieving trips without authentication"""
    response = client.get(f"{API_BASE}")

    # Should require authentication
    assert response.status_code in [401, 403]


@pytest.mark.unit
@pytest.mark.api
def test_list_trips_with_pagination(client, mock_user_payload):
    """Test trip list pagination parameters"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.get(
            f"{API_BASE}?page=1&page_size=5",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data


@pytest.mark.unit
@pytest.mark.api
def test_list_trips_with_filters(client, mock_user_payload):
    """Test trip list with status filter"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.get(
            f"{API_BASE}?status_filter=completed&favorites_only=true",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
def test_list_trips_empty_result(client, test_db, mock_user_payload):
    """Test listing trips when user has none"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.get(
            f"{API_BASE}",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trips"] == []
        assert data["total"] == 0


# ============================================================================
# Test: Get Trip by ID
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_get_trip_by_id_not_found(client, mock_user_payload):
    """Test retrieving non-existent trip"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.get(
            f"{API_BASE}/99999",
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
def test_get_trip_by_id_unauthenticated(client):
    """Test getting trip without authentication"""
    response = client.get(f"{API_BASE}/1")

    # Should require authentication
    assert response.status_code in [401, 403]


# ============================================================================
# Test: Update Trip
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_update_trip_not_found(client, mock_user_payload):
    """Test updating non-existent trip"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        update_data = {
            "destination": "London",
            "budget": 2500
        }

        response = client.put(
            f"{API_BASE}/99999",
            json=update_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
def test_update_trip_unauthenticated(client):
    """Test updating trip without authentication"""
    update_data = {"budget": 2500}

    response = client.put(
        f"{API_BASE}/1",
        json=update_data
    )

    # Should require authentication
    assert response.status_code in [401, 403]


@pytest.mark.unit
@pytest.mark.api
def test_update_trip_invalid_data(client, mock_user_payload):
    """Test updating trip with invalid data"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        # Invalid: negative budget
        invalid_data = {"budget": -1000}

        response = client.put(
            f"{API_BASE}/1",
            json=invalid_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should reject or return 404 (since trip doesn't exist)
        assert response.status_code in [400, 404, 422]


# ============================================================================
# Test: Delete Trip
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_delete_trip_not_found(client, mock_user_payload):
    """Test deleting non-existent trip"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.delete(
            f"{API_BASE}/99999",
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
def test_delete_trip_unauthenticated(client):
    """Test deleting trip without authentication"""
    response = client.delete(f"{API_BASE}/1")

    # Should require authentication
    assert response.status_code in [401, 403]


# ============================================================================
# Test: Favorite Trip
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_favorite_trip_not_found(client, mock_user_payload):
    """Test favoriting non-existent trip"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        response = client.put(
            f"{API_BASE}/99999/favorite",
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
def test_favorite_trip_unauthenticated(client):
    """Test favoriting trip without authentication"""
    response = client.put(f"{API_BASE}/1/favorite")

    # Should require authentication
    assert response.status_code in [401, 403]


# ============================================================================
# Test: Replan Trip
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
def test_replan_trip_not_found(client, mock_user_payload):
    """Test replanning non-existent trip"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        replan_data = {
            "budget": 3000,
            "departure_date": "2026-07-01",
            "return_date": "2026-07-10"
        }

        response = client.post(
            f"{API_BASE}/99999/replan",
            json=replan_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
def test_replan_trip_unauthenticated(client):
    """Test replanning trip without authentication"""
    replan_data = {"budget": 3000}

    response = client.post(
        f"{API_BASE}/1/replan",
        json=replan_data
    )

    # Should require authentication
    assert response.status_code in [401, 403]


@pytest.mark.unit
@pytest.mark.api
def test_replan_trip_invalid_dates(client, mock_user_payload):
    """Test replanning with invalid date range"""
    with patch("app.core.security.get_current_user") as mock_auth:
        mock_auth.return_value = mock_user_payload

        # Invalid: return before departure
        invalid_data = {
            "departure_date": "2026-07-10",
            "return_date": "2026-07-01"
        }

        response = client.post(
            f"{API_BASE}/1/replan",
            json=invalid_data,
            headers={"Authorization": "Bearer mock_token"}
        )

        # Should reject or return 404 (since trip doesn't exist)
        assert response.status_code in [400, 404, 422]


# ============================================================================
# Integration Note:
# ============================================================================
# Trip CREATION tests are not included because trips are created through
# the job system (POST /api/v1/jobs/trip-planning), not a direct endpoint.
#
# To test trip creation:
# 1. Submit job via POST /api/v1/jobs/trip-planning
# 2. Monitor job via SSE /api/v1/jobs/{job_id}/stream
# 3. Check trip is created when job completes
#
# These would be integration tests, not unit tests.
# ============================================================================