# Documentation

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

- **Generating the API URL**:
  ```python
  def generate_url(origin: str, destination: str, api_key: str) -> str:
      return f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
  ```

- **Fetching Route Data**:
  ```python
  def get_route_data(origin: str, destination: str, api_key: str) -> tuple:
      url = generate_url(origin, destination, api_key)
      response = requests.get(url)
      directions_data = response.json()
      if directions_data['status'] == 'OK':
          route_polyline = directions_data['routes'][0]['overview_polyline']['points']
          coordinates = polyline.decode(route_polyline)
          total_distance = directions_data['routes'][0]['legs'][0]['distance']['value'] / 1000  # km
          total_time = directions_data['routes'][0]['legs'][0]['duration']['value'] / 60  # minutes
          return coordinates, total_distance, total_time
      else:
          return [], 0, 0
  ```

#### Additional Documentation

- Official Google Maps Directions API Documentation: [https://developers.google.com/maps/documentation/directions/start](https://developers.google.com/maps/documentation/directions/start)


## Function Implementation

Once imported from CanterburyCommuto, the Overlap_Function will implement the main goal of this package. 

This function takes the csv file containing the GPS coordinates of route pairs and the API key as the necessary inputs. 
Other optional inputs are a threshold, a width, and a buffer distance, which are used for approximations. 
The function will first ask the user about his/her willingness to have approximations in the overlaps. 

If you answer 'no', then the function will consider that an overlap starts from the first common point of a route pair and ends at the last common point.

Otherwise, there are two types of approximation. 

The first type uses route segments before the first common point and after the last common point, since humans are free entities that can move around and decide to meet early or part later from the common points. Rectangles are created around the route segments before and after the common points. The intersection of the rectangles of the given width is evaluated. If the value of the intersection area over the smaller rectangle area is larger than a certain threshold, the route segment pairs will be kept. The first and last overlapping nodes will be redetermined through these route pairs kept by the rectangle approximation.

After selecting any of the two methods mentioned above, you will receive a follow-up question asking if you would like to obtain the information before and after the overlap, but this will lead to higher costs, as your API is called for more times. You may answer 'no', if you are operating on a tight budget. 

The second type of approximation uses a buffer, whose distance can be chosen by the user optionally. The intersection area of the buffers created along the two routes within a pair will be recorded. The ratios of the intersection over the two buffers will then be calculated. 

The Command-Line Interface explains the meaning of each input of the function. 

