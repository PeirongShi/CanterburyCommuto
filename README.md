Dear users,

This Python package CanterburyCommuto is created under the instruction of Professor Florian Grosset and Professor Émilien Schultz. 

# Overview
The aim of CanterburyCommuto is to find the percentages of time and distance travelled before, during, and after the overlap, if it exists, between two commuting routes. 

However, you can run this package on as many route pairs as you wish, as long as these route pairs are stored in a csv file in a way similar to the output of Sample.py in the repository.
Don't worry if the order of the columns in your csv file is different from that of the Sample.py output, as CanterburyCommuto will ask you to manually fill in the column names corresponding to 
the origins and destinations of the route pairs. 

# Google API Key
To use CanterburyCommuto, it is necessary to have your API key ready from Google. How to find this key?

1. Go to Google Cloud Console.
2. Create a billing account. If the usage of API is below a certain threshold, no payment will be needed.
3. Click on the button next to the Google Cloud logo to make a new project.
4. From Quick access, find APIs&Services. Click on it.
5. Go to the API Library.
6. Type in Google Maps in the search bar.
7. Enable the Google Maps Directions API. (It is probably harmless to enable more APIs than needed.) You will be able to create an API key in this step.
8. Go to Credentials, where you will find your key stored.

Caveat: Do not share your Google API key to the public. Your key is related to your billing account. If abused, high costs will be incurred. 

# Specification on API Usage

This project utilizes the **Google Maps Directions API** to compute and retrieve route details. The implementation leverages this API to determine the shortest path between two geographic points (defined by their GPS coordinates), fetch the route polyline for visualization, and calculate the total distance and estimated travel time.

#### Google Maps API Utilized

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

#### Exclusivity of Directions API Usage

Theoretically, this project uses only the **Google Maps Directions API**. However, if the code shows other APIs are needed, which may not be the case, please enable the other APIs on Google Cloud Console, which may solve the problem.

#### Code Snippets Related to this API

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



# Function Implementation

Once imported from CanterburyCommuto, the Overlap_Function will implement the main goal of this package. 

This function takes the csv file containing the GPS coordinates of route pairs and the API key as the necessary inputs. 
Other optional inputs are a threshold, a width, and a buffer distance, which are used for approximations. 
The function will first ask the user about his/her willingness to have approximations in the overlaps. 

If you answer 'no', then the function will consider that an overlap starts from the first common point of a route pair and ends at the last common point.

Otherwise, there are two types of approximation. 

The first type uses route segments before the first common point and after the last common point, since humans are free entities that can move around and decide to meet early or part later from the common points. Rectangles are created around the route segments before and after the common points. The intersection of the rectangles of the given width is evaluated. If the value of the intersection area over the smaller rectangle area is larger than a certain threshold, the route segment pairs will be kept. The first and last overlapping nodes will be redetermined through these route pairs kept by the rectangle approximation.

After selecting any of the two methods mentioned above, you will receive a follow-up question asking if you would like to obtain the information before and after the overlap, but this will lead to higher costs, as your API is called for more times. You may answer 'no', if you are operating on a tight budget. 

The second type of approximation uses a buffer, whose distance can be chosen by the user optionally. The intersection area of the buffers created along the two routes within a pair will be recorded. The ratios of the intersection over the two buffers will then be calculated. 

# Output
The output will be a csv file including the GPS coordinates of the route pairs' origins and destinations and the values describing the overlaps of route pairs. Graphs are also produced to visualize the commuting paths on the **OpenStreetMap** background. Distances are measured in kilometers and the time unit is minute. Areas are measured in square meters. Users are able to calculate percentages of overlaps, for instance, with the values of the following variables. As shown below, the list explaining the meaning of the output variables:

1. **OriginA**: The starting location of route A.
2. **DestinationA**: The ending location of route A.
3. **OriginB**: The starting location of route B.
4. **DestinationB**: The ending location of route B.

5. **aDist**: Total distance of route A. 
6. **aTime**: Total time to traverse route A.
7. **bDist**: Total distance of route B.
8. **bTime**: Total time to traverse route B.

9. **overlapDist**: Distance of the overlapping segment between route A and route B.
10. **overlapTime**: Time to traverse the overlapping segment between route A and route B.

11. **aBeforeDist**: Distance covered on route A before the overlap begins.
12. **aBeforeTime**: Time spent on route A before the overlap begins.
13. **bBeforeDist**: Distance covered on route B before the overlap begins.
14. **bBeforeTime**: Time spent on route B before the overlap begins.

15. **aAfterDist**: Distance covered on route A after the overlap ends.
16. **aAfterTime**: Time spent on route A after the overlap ends.
17. **bAfterDist**: Distance covered on route B after the overlap ends.
18. **bAfterTime**: Time spent on route B after the overlap ends.
19. **IntersectionArea**: The geographic area where the buffers of Route A and Route B intersect.
20. **aArea**: The total area of the buffer around Route A.
21. **bArea**: The total area of the buffer around Route B.

Acknowledgment: The **Specification on API Usage** section of this README.md was written with assistance from OpenAI's ChatGPT, as its explanation on the details of API utilization is relatively clear. 

If you have any question, feel free to write in the comment section.

Thank you!

Best regards,

Peirong Shi






