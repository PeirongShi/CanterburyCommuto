import csv
import requests
import polyline
import matplotlib.pyplot as plt


# Function to read a CSV file
def read_csv_file(csv_file: str) -> list:
    """
    Reads a CSV file and returns its content as a list of dictionaries.

    Parameters:
    - csv_file (str): The path to the CSV file.

    Returns:
    - list: A list of dictionaries, where each dictionary represents a row in the CSV.
    """
    with open(csv_file, mode='r') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

# Function to write results to a CSV file
def write_csv_file(output_csv: str, results: list, fieldnames: list) -> None:
    """
    Writes the results to a CSV file.

    Parameters:
    - output_csv (str): The path to the output CSV file.
    - results (list): A list of dictionaries containing the data to write.
    - fieldnames (list): A list of field names for the CSV file.

    Returns:
    - None
    """
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

# Function to fetch route data
def get_route_data(origin: str, destination: str, api_key: str) -> tuple:
    """
    Fetches route data from the Google Maps Directions API and decodes it.

    Parameters:
    - origin (str): The starting point of the route (latitude,longitude).
    - destination (str): The endpoint of the route (latitude,longitude).
    - api_key (str): The API key for accessing the Google Maps Directions API.

    Returns:
    - tuple:
        - list: A list of (latitude, longitude) tuples representing the route.
        - float: Total route distance in kilometers.
        - float: Total route time in minutes.
    """
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
    response = requests.get(url)
    directions_data = response.json()

    if directions_data['status'] == 'OK':
        route_polyline = directions_data['routes'][0]['overview_polyline']['points']
        coordinates = polyline.decode(route_polyline)
        total_distance = directions_data['routes'][0]['legs'][0]['distance']['value'] / 1000  # kilometers
        total_time = directions_data['routes'][0]['legs'][0]['duration']['value'] / 60  # minutes
        return coordinates, total_distance, total_time
    else:
        print("Error fetching directions:", directions_data['status'])
        return [], 0, 0


# Function to find common nodes
def find_common_nodes(coordinates_a: list, coordinates_b: list) -> tuple:
    """
    Finds the first and last common nodes between two routes.

    Parameters:
    - coordinates_a (list): A list of (latitude, longitude) tuples representing route A.
    - coordinates_b (list): A list of (latitude, longitude) tuples representing route B.

    Returns:
    - tuple:
        - tuple or None: The first common node (latitude, longitude) or None if not found.
        - tuple or None: The last common node (latitude, longitude) or None if not found.
    """
    first_common_node = next((coord for coord in coordinates_a if coord in coordinates_b), None)
    last_common_node = next((coord for coord in reversed(coordinates_a) if coord in coordinates_b), None)
    return first_common_node, last_common_node


# Function to split route segments
def split_segments(coordinates: list, first_common: tuple, last_common: tuple) -> tuple:
    """
    Splits a route into 'before', 'overlap', and 'after' segments.

    Parameters:
    - coordinates (list): A list of (latitude, longitude) tuples representing the route.
    - first_common (tuple): The first common node (latitude, longitude).
    - last_common (tuple): The last common node (latitude, longitude).

    Returns:
    - tuple:
        - list: The 'before' segment of the route.
        - list: The 'overlap' segment of the route.
        - list: The 'after' segment of the route.
    """
    index_first = coordinates.index(first_common)
    index_last = coordinates.index(last_common)
    return coordinates[:index_first + 1], coordinates[index_first:index_last + 1], coordinates[index_last:]


# Function to compute percentages
def compute_percentages(segment_value: float, total_value: float) -> float:
    """
    Computes the percentage of a segment relative to the total.

    Parameters:
    - segment_value (float): The value of the segment (e.g., distance or time).
    - total_value (float): The total value (e.g., total distance or time).

    Returns:
    - float: The percentage of the segment relative to the total, or 0 if total_value is 0.
    """
    return (segment_value / total_value) * 100 if total_value > 0 else 0

# Function to plot routes
def plot_routes(coordinates_a: list, coordinates_b: list, first_common: tuple, last_common: tuple) -> None:
    """
    Plots routes A and B with common nodes highlighted.

    Parameters:
    - coordinates_a (list): A list of (latitude, longitude) tuples for route A.
    - coordinates_b (list): A list of (latitude, longitude) tuples for route B.
    - first_common (tuple): The first common node (latitude, longitude).
    - last_common (tuple): The last common node (latitude, longitude).

    Returns:
    - None
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    latitudes_a = [coord[0] for coord in coordinates_a]
    longitudes_a = [coord[1] for coord in coordinates_a]
    latitudes_b = [coord[0] for coord in coordinates_b]
    longitudes_b = [coord[1] for coord in coordinates_b]

    ax.plot(longitudes_a, latitudes_a, marker='o', color='blue', label='Route A')
    ax.plot(longitudes_b, latitudes_b, marker='o', color='red', label='Route B')

    if first_common:
        ax.scatter(*reversed(first_common), color='green', label='First Common Node', zorder=5)
    if last_common:
        ax.scatter(*reversed(last_common), color='orange', label='Last Common Node', zorder=5)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Route Visualization with Common Nodes")
    ax.legend()
    plt.show()

def process_routes_with_csv(csv_file: str, api_key: str, output_csv: str = "output.csv") -> list:
    """
    Processes routes from a CSV file, computes time and distance travelled before, during, and after overlaps, and writes results to a CSV file.

    Parameters:
    - csv_file (str): The path to the input CSV file.
    - api_key (str): The API key for accessing the Google Maps Directions API.
    - output_csv (str): The path to the output CSV file.

    Returns:
    - list: A list of dictionaries containing the computed results.
    """
    data = read_csv_file(csv_file)
    results = []

    for row in data:
        origin_a, destination_a = row['Origin of A'], row['Destination of A']
        origin_b, destination_b = row['Origin of B'], row['Destination of B']

        # Get full route details for A and B
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)

        # Find common nodes
        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            print("No common nodes found for these routes.")
            continue

        # Split segments
        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        # Calculate distances and times for A
        _, before_a_distance, before_a_time = get_route_data(origin_a, f"{before_a[-1][0]},{before_a[-1][1]}", api_key)
        _, overlap_a_distance, overlap_a_time = get_route_data(f"{overlap_a[0][0]},{overlap_a[0][1]}", f"{overlap_a[-1][0]},{overlap_a[-1][1]}", api_key)
        _, after_a_distance, after_a_time = get_route_data(f"{after_a[0][0]},{after_a[0][1]}", destination_a, api_key)

        # Calculate distances and times for B
        _, before_b_distance, before_b_time = get_route_data(origin_b, f"{before_b[-1][0]},{before_b[-1][1]}", api_key)
        #_, overlap_b_distance, overlap_b_time = get_route_data(f"{overlap_b[0][0]},{overlap_b[0][1]}", f"{overlap_b[-1][0]},{overlap_b[-1][1]}", api_key)
        _, after_b_distance, after_b_time = get_route_data(f"{after_b[0][0]},{after_b[0][1]}", destination_b, api_key)

        # Compute percentages for A
        a_overlap_distance_percentage = compute_percentages(overlap_a_distance, total_distance_a)
        a_overlap_time_percentage = compute_percentages(overlap_a_time, total_time_a)
        a_before_distance_percentage = compute_percentages(before_a_distance, total_distance_a)
        a_before_time_percentage = compute_percentages(before_a_time, total_time_a)
        a_after_distance_percentage = compute_percentages(after_a_distance, total_distance_a)
        a_after_time_percentage = compute_percentages(after_a_time, total_time_a)

        # Compute percentages for B
        b_overlap_distance_percentage = compute_percentages(overlap_a_distance, total_distance_b)
        b_overlap_time_percentage = compute_percentages(overlap_a_time, total_time_b)
        b_before_distance_percentage = compute_percentages(before_b_distance, total_distance_b)
        b_before_time_percentage = compute_percentages(before_b_time, total_time_b)
        b_after_distance_percentage = compute_percentages(after_b_distance, total_distance_b)
        b_after_time_percentage = compute_percentages(after_b_time, total_time_b)

        # Append results
        results.append({
            "Overlap Distance": overlap_a_distance,
            "Overlap Time": overlap_a_time,
            "A Overlap Distance Percentage": a_overlap_distance_percentage,
            "A Overlap Time Percentage": a_overlap_time_percentage,
            "B Overlap Distance Percentage": b_overlap_distance_percentage,
            "B Overlap Time Percentage": b_overlap_time_percentage,
            "A Before Distance Percentage": a_before_distance_percentage,
            "A Before Time Percentage": a_before_time_percentage,
            "A After Distance Percentage": a_after_distance_percentage,
            "A After Time Percentage": a_after_time_percentage,
            "B Before Distance Percentage": b_before_distance_percentage,
            "B Before Time Percentage": b_before_time_percentage,
            "B After Distance Percentage": b_after_distance_percentage,
            "B After Time Percentage": b_after_time_percentage
        })

        # Plot routes
        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

    # Write results to CSV
    fieldnames = [
        "Overlap Distance", "Overlap Time",
        "A Overlap Distance Percentage", "A Overlap Time Percentage",
        "B Overlap Distance Percentage", "B Overlap Time Percentage",
        "A Before Distance Percentage", "A Before Time Percentage",
        "A After Distance Percentage", "A After Time Percentage",
        "B Before Distance Percentage", "B Before Time Percentage",
        "B After Distance Percentage", "B After Time Percentage"
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results

def process_routes_only_overlap_with_csv(csv_file: str, api_key: str, output_csv: str = "output.csv") -> list:
    """
    Processes routes from a CSV file, computes time and distance travelled during overlaps, and writes results to a CSV file.

    Parameters:
    - csv_file (str): The path to the input CSV file.
    - api_key (str): The API key for accessing the Google Maps Directions API.
    - output_csv (str): The path to the output CSV file.

    Returns:
    - list: A list of dictionaries containing the computed results.
    """
    data = read_csv_file(csv_file)
    results = []

    for row in data:
        origin_a, destination_a = row['Origin of A'], row['Destination of A']
        origin_b, destination_b = row['Origin of B'], row['Destination of B']

        # Get full route details for A and B
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)

        # Find common nodes
        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            print("No common nodes found for these routes.")
            continue

        # Split segments
        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        # Calculate overlap distance and time
        _, overlap_a_distance, overlap_a_time = get_route_data(f"{overlap_a[0][0]},{overlap_a[0][1]}", f"{overlap_a[-1][0]},{overlap_a[-1][1]}", api_key)

        # Compute percentages for A
        a_overlap_distance_percentage = compute_percentages(overlap_a_distance, total_distance_a)
        a_overlap_time_percentage = compute_percentages(overlap_a_time, total_time_a)

        # Compute percentages for B
        b_overlap_distance_percentage = compute_percentages(overlap_a_distance, total_distance_b)
        b_overlap_time_percentage = compute_percentages(overlap_a_time, total_time_b)

        # Append results
        results.append({
            "Overlap Distance": overlap_a_distance,
            "Overlap Time": overlap_a_time,
            "A Overlap Distance Percentage": a_overlap_distance_percentage,
            "A Overlap Time Percentage": a_overlap_time_percentage,
            "B Overlap Distance Percentage": b_overlap_distance_percentage,
            "B Overlap Time Percentage": b_overlap_time_percentage
        })

        # Plot routes
        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

    # Write results to CSV
    fieldnames = [
        "Overlap Distance", "Overlap Time",
        "A Overlap Distance Percentage", "A Overlap Time Percentage",
        "B Overlap Distance Percentage", "B Overlap Time Percentage"
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results

def Overlap_Function(
    csv_file: str, api_key: str, width_ratio: float = 0.5, threshold: float = 0.05
) -> None:
    """
    Analyze route overlaps and optionally gather commuting information.

    Args:
        csv_file (str): Path to the input CSV file containing route data.
        api_key (str): Google API key for route calculations.
        width_ratio (float, optional): Width ratio parameter for overlap approximation. Defaults to 0.5.
        threshold (float, optional): Threshold for determining overlapping nodes. Defaults to 0.05.

    Interactive Prompts:
        - Whether to approximate overlapping nodes.
        - Whether to gather commuting information before and after overlap.
    
    The function calls specific processing methods based on user input.
    """
    option: str = input('Would you like to have approximation for the overlapping nodes? Please enter yes or no: ') 
    if option.lower() == 'yes':
        call: str = input('Would you like to have information regarding commuting before and after the overlap? Note that this can incur higher costs by calling Google API for multiple times. Please enter yes or no: ')
        if call.lower() == 'yes':
            process_routes_with_csv_Rec(csv_file, api_key, width_ratio, threshold)
        elif call.lower() == 'no':
            process_routes_with_csv_EI_only_overlap(csv_file, api_key, threshold)
    elif option.lower() == 'no':
        call: str = input('Would you like to have information regarding commuting before and after the overlap? Note that this can incur higher costs by calling Google API for multiple times. Please enter yes or no: ')
        if call.lower() == 'yes':
            process_routes_with_csv(csv_file, api_key)
        elif call.lower() == 'no':
            process_routes_only_overlap_with_csv(csv_file, api_key)

