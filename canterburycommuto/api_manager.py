import requests

class APIManager:
    def __init__(self, base_url="https://www.googleapis.com", api_key=None, oauth_token=None):
        """Initialize APIManager with Google API authentication."""
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        
        # Use API Key authentication if provided
        self.api_key = api_key

        # Use OAuth 2.0 token if provided
        if oauth_token:
            self.headers["Authorization"] = f"Bearer {oauth_token}"

    def send_request(self, endpoint, method="GET", params=None, data=None):
        """Send a request to Google API."""
        url = f"{self.base_url}{endpoint}"

        # Include API key in params if using API key authentication
        if self.api_key:
            if not params:
                params = {}
            params["key"] = self.api_key

        try:
            response = requests.request(method, url, headers=self.headers, params=params, json=data)
            response.raise_for_status()
            return response.json()  # Return parsed JSON response
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

