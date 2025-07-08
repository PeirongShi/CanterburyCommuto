# Additional Documentation

## Specification on API Usage

This project utilizes the **Google Maps Directions API** to compute and retrieve route details. The implementation leverages this API to determine the shortest path between two geographic points (defined by their GPS coordinates), fetch the route polyline for visualization, and calculate the total distance and estimated travel time.

### Google Maps API Utilized

The script interacts with the **Directions API** endpoint: `https://maps.googleapis.com/maps/api/directions/json`. This API provides the following capabilities:

1. **Route Path**:
   - The API returns a polyline representation of the route (“overview_polyline”), which is decoded into a list of latitude and longitude tuples for visualization.

2. **Travel Distance**:
   - The `legs[0].distance.value` field is extracted to compute the total distance in kilometers.

3. **Travel Time**:
   - The `legs[0].duration.value` field is extracted to compute the estimated travel time in minutes.

#### Default Options

- **Traffic Conditions**:
  - The API calculates travel time and distance based on historical traffic data, which is the default behavior.

### Exclusivity of Directions API Usage

Theoretically, this project uses only the **Google Maps Directions API**. However, if the code shows other APIs are needed, which may not be the case, please enable the other APIs on Google Cloud Console, which may solve the problem.

### Code Snippets Related to this API

- **Generating the API Request Body**:
  ```python
  def generate_request_body(origin: str, destination: str) -> dict:
    """
    Creates the request body for the Google Maps Routes API (v2).

    Parameters:
    - origin (str): The starting point of the route in "latitude,longitude" format.Body
    - destination (str): The endpoint of the route in "latitude,longitude" format.

    Returns:
    - dict: JSON body for the Routes API POST request.
    """
    origin_lat, origin_lng = map(float, origin.split(','))
    dest_lat, dest_lng = map(float, destination.split(','))

    return {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_lat,
                    "longitude": origin_lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dest_lat,
                    "longitude": dest_lng
                }
            }
        },
        "travelMode": "DRIVE",
        "computeAlternativeRoutes": True,  # enables fallback options
        "routeModifiers": {
            "avoidTolls": False
        }
    }
  ```

- **Fetching Route Data**:
  ```python
  def get_route_data_google(origin: str, destination: str, api_key: str, save_api_info: bool = False) -> tuple:
    """
    Fetches route data from the Google Maps Routes API (v2) and decodes the polyline.

    Parameters:
    - origin (str): Starting point ("latitude,longitude").
    - destination (str): Endpoint ("latitude,longitude").
    - api_key (str): Google Maps API key with Routes API enabled.
    - save_api_info (bool): Optionally saves raw response in cache.

    Returns:
    - tuple:
        - list of (lat, lng) tuples (route polyline)
        - float: distance in kilometers
        - float: time in minutes
    """
    max_retries = 5
    delay = 10  # seconds

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.legs.distanceMeters,routes.legs.duration,routes.polyline.encodedPolyline"
    }

    body = generate_request_body(origin, destination)

    for attempt in range(max_retries):
        try:
            response = requests.post(GOOGLE_API_URL, json=body, headers=headers)
            data = response.json()

            if response.status_code == 200 and "routes" in data and data["routes"]:
                if save_api_info:
                    global api_response_cache
                    api_response_cache[(origin, destination)] = data

                # Pick the shortest route if alternatives are present
                route = min(data["routes"], key=lambda r: r["legs"][0].get("distanceMeters", float("inf")))

                polyline_points = route["polyline"]["encodedPolyline"]
                coordinates = polyline.decode(polyline_points)

                legs = route.get("legs", [])
                if not legs:
                    raise ValueError("No legs found in route.")

                distance_meters = int(legs[0]["distanceMeters"])
                duration_seconds = int(legs[0]["duration"].replace("s", ""))

                return coordinates, distance_meters / 1000, duration_seconds / 60

            elif response.status_code == 429:
                print(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                time.sleep(delay*(attempt+1))

            else:
                print("Error fetching route:", data)
                return [], 0, 0

        except Exception as e:
            print(f"Exception during route extraction: {e}")
            return [], 0, 0

    print("Exceeded maximum retries due to rate limit or repeated failure.")
    return [], 0, 0
  ```
 

#### Additional Documentation

- Official Google Maps Routes API Documentation: [https://developers.google.com/maps/documentation/routes](https://developers.google.com/maps/documentation/routes)


## Function Implementation

Once imported from CanterburyCommuto, the Overlap_Function will implement the main goal of this package. 

This function takes the csv file containing the GPS coordinates of route pairs and the API key as the necessary inputs. 
Other optional inputs are a threshold, a width, and a buffer distance, which are used for approximations. 
The function will first ask the user about his/her willingness to have approximations in the overlaps. 

If you answer 'no', then the function will consider that an overlap starts from the first common point of a route pair and ends at the last common point.

Otherwise, there are four options for approximation. 

The first type uses route segments before the first common point and after the last common point, since humans are free entities that can move around and decide to meet early or part later from the common points. Rectangles are created around the route segments before and after the common points. The intersection of the rectangles of the given width is evaluated. If the value of the intersection area over the smaller rectangle area is larger than a certain threshold, the route segment pairs will be kept. The first and last overlapping nodes will be redetermined through these route pairs kept by the rectangle approximation.

After selecting any of the two methods mentioned above, you will receive a follow-up question asking if you would like to obtain the information before and after the overlap, but this will lead to higher costs, as your API is called for more times. You may answer 'no', if you are operating on a tight budget. 

The second type of approximation uses a buffer, whose distance can be chosen by the user optionally. The intersection area of the buffers created along the two routes within a pair will be recorded. The ratios of the intersection over the two buffers will then be calculated. 

The third type of approximation considers the buffer intersection as a geometrical shape that intersects with the routes, which are considered as lines in this case. The road nodes that are closest to the intersection points are found, and then the relevant commuting information is calculated accordingly.

The last option for approximation is called 'exact'. In some sense, it is even better than the case where no approximation is made. When no approximation is made, there can be underestimation of the overlap if, for example, the first common node is found way after the two routes meet. With the 'exact' option, one is able to find the exact locations where the buffer intersection meets the road, so relatively accurate commuting information can be determined.

The Command-Line Interface specifies each input of the function. 

