import pytest
import requests_mock
from canterburycommuto.api_manager import APIManager

@pytest.fixture
def api_manager():
    """Fixture to create an APIManager instance for Google API testing."""
    return APIManager(base_url="https://www.googleapis.com", api_key="fake_api_key")

def test_google_api_get_request(api_manager):
    """Test a Google API GET request with a mock response."""
    with requests_mock.Mocker() as mock:
        mock.get("https://www.googleapis.com/maps/api/geocode/json", json={"results": [{"formatted_address": "Google HQ"}]})

        response = api_manager.send_request("/maps/api/geocode/json", params={"address": "1600 Amphitheatre Parkway"})
        assert "results" in response
        assert response["results"][0]["formatted_address"] == "Google HQ"
