"""
Pytest configuration and shared fixtures for TripMeBuddy backend tests.
COMPLETE VERSION - Includes all fixtures, Excel tracking, and dependency mocking.
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
from datetime import datetime

# ============================================================================
# CRITICAL: Set test environment variables BEFORE importing app modules
# ============================================================================
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "tripmebuddy_test")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "0")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("KEYCLOAK_SERVER_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "tripmebuddy")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "trip-me-buddy-frontend")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "")
os.environ.setdefault("AMADEUS_API_KEY", "test_key")
os.environ.setdefault("AMADEUS_API_SECRET", "test_secret")
os.environ.setdefault("GEMINI_API_KEY", "test_key")
# CORS origins as JSON array
os.environ.setdefault("BACKEND_CORS_ORIGINS", '["http://localhost:3000"]')

# Now safe to import app modules
from app.main import app
from app.core.database import Base, get_db, get_async_db
from app.core.cache import get_redis
from app.core.config import settings


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create in-memory SQLite engine for testing.
    Session-scoped to reuse across all tests.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Rolls back changes after each test.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ============================================================================
# Mock Redis Fixture
# ============================================================================

@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client for testing (synchronous fixture returning async mock)"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.ping = AsyncMock(return_value=True)
    return redis_mock


# ============================================================================
# Test Client Fixture (with all dependency overrides)
# ============================================================================

@pytest.fixture(scope="function")
def client(test_db, mock_redis) -> Generator[TestClient, None, None]:
    """
    Create FastAPI test client with test database and mocked Redis.
    Overrides both sync and async database dependencies, plus Redis.
    """
    # Sync database override
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    # Async database override
    async def override_get_async_db():
        yield test_db

    # Redis override
    async def override_get_redis():
        return mock_redis

    # Apply all overrides
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def mock_jwt_token() -> str:
    """
    Generate a mock JWT token for testing.
    This is a placeholder - actual implementation would create valid test tokens.
    """
    return "mock_jwt_token_for_testing"


@pytest.fixture
def mock_user_payload() -> dict:
    """
    Mock user payload from decoded JWT token.
    """
    return {
        "sub": "test-user-uuid-12345",
        "email": "testuser@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "roles": ["user"],
    }


@pytest.fixture
def auth_headers(mock_jwt_token: str) -> dict:
    """
    Generate authorization headers for authenticated requests.
    """
    return {"Authorization": f"Bearer {mock_jwt_token}"}


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_trip_data() -> dict:
    """
    Sample trip data for testing trip creation.
    """
    return {
        "user_input": "Plan a 5-day trip to Paris in June for 2 adults, budget $3000",
        "destination": "Paris",
        "start_date": "2026-06-15",
        "end_date": "2026-06-20",
        "num_travelers": 2,
        "budget": 3000.0,
        "currency": "USD",
    }


@pytest.fixture
def sample_user_data() -> dict:
    """
    Sample user data for testing user operations.
    """
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "password": "SecurePass123",
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_amadeus_response() -> dict:
    """
    Mock response from Amadeus API for flight search.
    """
    return {
        "data": [
            {
                "id": "1",
                "price": {"total": "450.00", "currency": "USD"},
                "itineraries": [
                    {
                        "segments": [
                            {
                                "departure": {
                                    "iataCode": "JFK",
                                    "at": "2026-06-15T10:00:00"
                                },
                                "arrival": {
                                    "iataCode": "CDG",
                                    "at": "2026-06-15T22:00:00"
                                },
                            }
                        ]
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_hotel_response() -> dict:
    """
    Mock response from Amadeus API for hotel search.
    """
    return {
        "data": [
            {
                "hotel": {
                    "hotelId": "HOTEL123",
                    "name": "Test Hotel Paris",
                    "rating": 4,
                },
                "offers": [
                    {
                        "id": "OFFER123",
                        "price": {"total": "150.00", "currency": "USD"},
                        "room": {"type": "DOUBLE"},
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_gemini_response() -> str:
    """
    Mock response from Gemini API for destination research.
    """
    return """
    Paris is an excellent choice for a 5-day trip in June. Here are the highlights:
    
    Must-Visit Attractions:
    - Eiffel Tower
    - Louvre Museum
    - Notre-Dame Cathedral
    
    Recommended Activities:
    - Seine River cruise
    - Montmartre walking tour
    - French cooking class
    
    Budget Breakdown:
    - Accommodation: $750
    - Flights: $900
    - Food & Activities: $1350
    """


# ============================================================================
# Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_caches():
    """
    Reset any cached values between tests.
    """
    # Import here to avoid circular dependency
    from app.core import security

    # Reset cached Keycloak public keys
    security._keycloak_public_keys = None

    yield

    # Cleanup after test
    security._keycloak_public_keys = None


# ============================================================================
# Excel Test Results Integration
# ============================================================================

# Global variables for Excel tracking
_excel_file = None
_test_results = {}


def pytest_addoption(parser):
    """Add command line option for Excel test tracking"""
    parser.addoption(
        "--excel-tests",
        action="store",
        default=None,
        help="Path to Excel/CSV file containing test cases (results will be updated)"
    )


def pytest_configure(config):
    """Initialize Excel file path from command line"""
    global _excel_file
    _excel_file = config.getoption("--excel-tests")
    if _excel_file:
        print(f"\n📊 Excel test tracking enabled: {_excel_file}")


def pytest_runtest_logreport(report):
    """Capture individual test results"""
    global _test_results

    if report.when == 'call':  # Only capture the actual test call, not setup/teardown
        test_name = report.nodeid.split('::')[-1]  # Extract function name

        _test_results[test_name] = {
            'outcome': report.outcome,  # passed, failed, skipped
            'duration': round(report.duration, 3),  # seconds
            'error': str(report.longrepr) if report.failed else None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def pytest_sessionfinish(session, exitstatus):
    """Write all test results back to Excel after session completes"""
    global _excel_file, _test_results

    if not _excel_file or not _test_results:
        return

    try:
        # Load existing Excel/CSV file with explicit string dtypes for result columns
        dtype_spec = {
            'Actual Status': 'str',
            'Pass/Fail': 'str',
            'Error Details': 'str',
            'Last Run': 'str'
        }

        try:
            df = pd.read_excel(_excel_file, dtype=dtype_spec)
            file_type = 'Excel'
        except:
            try:
                csv_file = _excel_file.replace('.xlsx', '.csv')
                df = pd.read_csv(csv_file, dtype=dtype_spec)
                _excel_file = csv_file  # Update to CSV path
                file_type = 'CSV'
            except Exception as e:
                print(f"\n⚠️  Could not load test file: {e}")
                return

        # Ensure result columns exist and are object type
        for col in ['Actual Status', 'Pass/Fail', 'Error Details', 'Last Run']:
            if col not in df.columns:
                df[col] = ''
            else:
                df[col] = df[col].astype('object')  # Force to object type

        # Update DataFrame with test results
        updates_count = 0
        for idx, row in df.iterrows():
            test_name = row['Test Name']

            if test_name in _test_results:
                result = _test_results[test_name]

                # Map pytest outcomes to Excel statuses
                status_map = {
                    'passed': 'PASSED',
                    'failed': 'FAILED',
                    'skipped': 'SKIPPED'
                }

                df.loc[idx, 'Actual Status'] = status_map.get(result['outcome'], 'ERROR')
                df.loc[idx, 'Pass/Fail'] = 'PASS' if result['outcome'] == 'passed' else 'FAIL'

                # Truncate error details if too long
                error_detail = result['error'] if result['error'] else ''
                if len(error_detail) > 200:
                    error_detail = error_detail[:197] + '...'
                df.loc[idx, 'Error Details'] = error_detail

                df.loc[idx, 'Last Run'] = result['timestamp']
                updates_count += 1

        # Save results back to file
        if file_type == 'Excel':
            df.to_excel(_excel_file, index=False, engine='openpyxl')
        else:
            df.to_csv(_excel_file, index=False)

        # Print summary
        print(f"\n{'='*70}")
        print(f"✓ Test results updated in {_excel_file}")
        print(f"  - {updates_count} test(s) matched and updated")
        print(f"  - File type: {file_type}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n⚠️  Error updating Excel results: {e}")
        import traceback
        traceback.print_exc()
