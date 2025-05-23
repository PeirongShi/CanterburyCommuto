import csv
import time
import datetime
import logging
import math
import os
import random
from typing import Dict, List, Tuple, Optional
from multiprocessing.dummy import Pool

import folium
import polyline
import requests
from IPython.display import display, IFrame
from pyproj import Geod, Transformer
from shapely.geometry import LineString, Polygon, mapping, MultiLineString, Point, GeometryCollection, MultiPoint

# Global function to generate URL
def generate_url(origin: str, destination: str, api_key: str) -> str:
    """
    Generates the Google Maps Directions API URL with the given parameters.

    Parameters:
    - origin (str): The starting point of the route (latitude,longitude).
    - destination (str): The endpoint of the route (latitude,longitude).
    - api_key (str): The API key for accessing the Google Maps Directions API.

    Returns:
    - str: The full URL for the API request.
    """
    return f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"


# Function to read a csv file and then asks the users to manually enter their corresponding column variables with respect to OriginA, DestinationA, OriginB, and DestinationB.
# The following functions also help determine if there are errors in the code. 
# Point to the notebooks directory instead of the script's directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "notebooks"))
log_path = os.path.join(project_root, "results", "validation_errors_timing.log")

# Ensure the results folder exists inside notebooks
os.makedirs(os.path.dirname(log_path), exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=log_path,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def is_valid_coordinate(coord: str) -> bool:
    """
    Checks if the coordinate string is a valid latitude,longitude pair.
    Validates format, numeric values, and geographic bounds.

    Returns True if valid, False otherwise.
    """
    if not isinstance(coord, str):
        return False
    parts = coord.strip().split(",")
    if len(parts) != 2:
        return False

    try:
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        if not (-90 <= lat <= 90):
            return False
        if not (-180 <= lon <= 180):
            return False
        return True
    except ValueError:
        return False

def read_csv_file(
    csv_file: str,
    colorna: str,
    coldesta: str,
    colorib: str,
    colfestb: str,
    skip_invalid: bool = True
) -> Tuple[List[Dict[str, str]], int]:
    """
    Reads a CSV file and maps user-specified column names to standardized names
    (OriginA, DestinationA, OriginB, DestinationB). Returns a list of dictionaries
    with standardized column names. Logs any coordinate errors encountered.

    Parameters:
    - csv_file (str): Path to the CSV file.
    - colorna (str): Column name for the origin of route A.
    - coldesta (str): Column name for the destination of route A.
    - colorib (str): Column name for the origin of route B.
    - colfestb (str): Column name for the destination of route B.
    - skip_invalid (bool): If True, skip rows with invalid coordinates and log them.

    Returns:
    - Tuple[List[Dict[str, str]], int]: List of dictionaries with standardized column names,
      and the count of rows with invalid coordinates.
    """
    with open(csv_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        csv_columns = reader.fieldnames

        required_columns = [colorna, coldesta, colorib, colfestb]
        for column in required_columns:
            if column not in csv_columns:
                raise ValueError(f"Column '{column}' not found in the CSV file.")

        column_mapping = {
            colorna: "OriginA",
            coldesta: "DestinationA",
            colorib: "OriginB",
            colfestb: "DestinationB",
        }

        mapped_data = []
        error_count = 0
        row_number = 1
        for row in reader:
            mapped_row = {
                column_mapping.get(col, col): value for col, value in row.items()
            }
            coords = [
                mapped_row["OriginA"],
                mapped_row["DestinationA"],
                mapped_row["OriginB"],
                mapped_row["DestinationB"],
            ]
            invalids = [c for c in coords if not is_valid_coordinate(c)]

            if invalids:
                error_msg = f"Row {row_number} - Invalid coordinates: {invalids}"
                logging.warning(error_msg)
                error_count += 1
                if not skip_invalid:
                    raise ValueError(error_msg)

            mapped_data.append(mapped_row)
            row_number += 1

        return mapped_data, error_count
    

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
    with open(output_csv, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

def request_cost_estimation(
    csv_file: str,
    approximation: str = "no",
    commuting_info: str = "no",
    colorna: Optional[str] = None,
    coldesta: Optional[str] = None,
    colorib: Optional[str] = None,
    colfestb: Optional[str] = None,
    output_overlap: Optional[str] = None,
    output_buffer: Optional[str] = None,
    skip_invalid: bool = True
) -> Tuple[int, float]:
    """
    Estimates the number of Google API requests needed based on route pair data
    and approximates the cost.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - approximation (str): Approximation strategy to apply.
    - commuting_info (str): Whether commuting info is to be considered.
    - colorna, coldesta, colorib, colfestb (str): Column names for routes.
    - skip_invalid (bool): Whether to skip invalid rows.

    Returns:
    - Tuple[int, float]: Estimated number of API requests and corresponding cost in USD.
    """
    data_set, pre_api_error_count = read_csv_file(csv_file, colorna, coldesta, colorib, colfestb, skip_invalid=skip_invalid)
    n = 0

    for row in data_set:
        origin_a = row["OriginA"]
        destination_a = row["DestinationA"]
        origin_b = row["OriginB"]
        destination_b = row["DestinationB"]

        same_a = origin_a == origin_b
        same_b = destination_a == destination_b
        same_a_dest = origin_a == destination_a
        same_b_dest = origin_b == destination_b

        if approximation == "no":
            n += 1 if same_a and same_b else (7 if commuting_info == "yes" else 3)

        elif approximation == "yes":
            n += 1 if same_a and same_b else (8 if commuting_info == "yes" else 4)

        elif approximation == "yes with buffer":
            if same_a_dest and same_b_dest:
                n += 0
            elif same_a_dest or same_b_dest or (same_a and same_b):
                n += 1
            else:
                n += 2

        elif approximation == "closer to precision" or approximation == "exact":
            if same_a_dest and same_b_dest:
                n += 0
            elif same_a_dest or same_b_dest or (same_a and same_b):
                n += 1
            else:
                n += 8 if commuting_info == "yes" else 4

        else:
            raise ValueError(f"Invalid approximation option: '{approximation}'")

    cost = (n / 1000) * 5  # USD estimate
    return n, cost

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
    # Use the global function to generate the URL
    url = generate_url(origin, destination, api_key)
    response = requests.get(url)
    directions_data = response.json()

    if directions_data["status"] == "OK":
        route_polyline = directions_data["routes"][0]["overview_polyline"]["points"]
        coordinates = polyline.decode(route_polyline)
        total_distance = (
            directions_data["routes"][0]["legs"][0]["distance"]["value"] / 1000
        )  # kilometers
        total_time = (
            directions_data["routes"][0]["legs"][0]["duration"]["value"] / 60
        )  # minutes
        return coordinates, total_distance, total_time
    else:
        print("Error fetching directions:", directions_data["status"])
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
    first_common_node = next(
        (coord for coord in coordinates_a if coord in coordinates_b), None
    )
    last_common_node = next(
        (coord for coord in reversed(coordinates_a) if coord in coordinates_b), None
    )
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
    return (
        coordinates[: index_first + 1],
        coordinates[index_first : index_last + 1],
        coordinates[index_last:],
    )


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


# Function to generate unique file names for storing the outputs and maps
def generate_unique_filename(base_name: str, extension: str = ".csv") -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    random_id = random.randint(10000, 99999)
    return f"{base_name}-{timestamp}_{random_id}{extension}"


# Function to save the maps
def save_map(map_object, base_name: str) -> str:
    os.makedirs("results", exist_ok=True)
    filename = generate_unique_filename(os.path.join("results", base_name), ".html")
    map_object.save(filename)
    print(f"Map saved to: {os.path.abspath(filename)}")
    return filename


# Function to plot routes to display on maps
def plot_routes(
    coordinates_a: list, coordinates_b: list, first_common: tuple, last_common: tuple
) -> None:
    """
    Plots routes A and B with common nodes highlighted over an OpenStreetMap background.

    Parameters:
    - coordinates_a (list): A list of (latitude, longitude) tuples for route A.
    - coordinates_b (list): A list of (latitude, longitude) tuples for route B.
    - first_common (tuple): The first common node (latitude, longitude).
    - last_common (tuple): The last common node (latitude, longitude).

    Returns:
    - None
    """

    # If the routes completely overlap, set Route B to be the same as Route A
    if not coordinates_b:
        coordinates_b = coordinates_a

    # Calculate the center of the map
    avg_lat = sum(coord[0] for coord in coordinates_a + coordinates_b) / len(
        coordinates_a + coordinates_b
    )
    avg_lon = sum(coord[1] for coord in coordinates_a + coordinates_b) / len(
        coordinates_a + coordinates_b
    )

    # Create a map centered at the average location of the routes
    map_osm = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    # Add Route A to the map
    folium.PolyLine(
        locations=coordinates_a, color="blue", weight=5, opacity=1, tooltip="Route A"
    ).add_to(map_osm)

    # Add Route B to the map
    folium.PolyLine(
        locations=coordinates_b, color="red", weight=5, opacity=1, tooltip="Route B"
    ).add_to(map_osm)

    # Add circular marker for the first common node (Cadet Blue)
    if first_common:
        folium.CircleMarker(
            location=[first_common[0], first_common[1]],
            radius=8,  
            color="cadetblue",  
            fill=True,
            fill_color="cadetblue",  
            fill_opacity=1,
            tooltip="First Common Node",
        ).add_to(map_osm)

    # Add circular marker for the last common node (Pink)
    if last_common:
        folium.CircleMarker(
            location=[last_common[0], last_common[1]],
            radius=8,
            color="pink",
            fill=True,
            fill_color="pink",
            fill_opacity=1,
            tooltip="Last Common Node",
        ).add_to(map_osm)

    # Add origin markers for Route A (Red) and Route B (Green)
    folium.Marker(
        location=coordinates_a[0],  
        icon=folium.Icon(color="red", icon="info-sign"), 
        tooltip="Origin A"
    ).add_to(map_osm)

    folium.Marker(
        location=coordinates_b[0],  
        icon=folium.Icon(color="green", icon="info-sign"), 
        tooltip="Origin B"
    ).add_to(map_osm)

    # Add destination markers as stars using DivIcon
    folium.Marker(
        location=coordinates_a[-1],
        icon=folium.DivIcon(
            html=f"""
            <div style="font-size: 16px; color: red; transform: scale(1.4);">
                <i class='fa fa-star'></i>
            </div>
            """
        ),
        tooltip="Destination A",
    ).add_to(map_osm)

    folium.Marker(
        location=coordinates_b[-1],
        icon=folium.DivIcon(
            html=f"""
            <div style="font-size: 16px; color: green; transform: scale(1.4);">
                <i class='fa fa-star'></i>
            </div>
            """
        ),
        tooltip="Destination B",
    ).add_to(map_osm)

    # Save the map using the save_map function
    map_filename = save_map(map_osm, "routes_map")

    # Display the map inline (only for Jupyter Notebooks)
    try:
        display(IFrame(map_filename, width="100%", height="500px"))
    except NameError:
        print(f"Map saved as '{map_filename}'. Open it in a browser.")

def wrap_row(args):
    """
    Wraps a single row-processing task for multithreading.

    This function is used inside a thread pool (via multiprocessing.dummy)
    to process each row of the dataset with the provided row_function.
    If an exception occurs, it logs the error and either skips the row
    (if skip_invalid is True) or re-raises the exception to halt execution.

    Args:
        args (tuple): A tuple containing:
            - row (dict): The data row to process.
            - api_key (str): API key for route data fetching.
            - row_function (callable): Function to apply to the row.
            - skip_invalid (bool): Whether to skip errors or halt on first error.

    Returns:
        dict or None: Result of processing the row, or None if skipped.
    """
    row, api_key, row_function, skip_invalid = args
    return row_function((row, api_key), skip_invalid=skip_invalid)


def process_rows(data, api_key, row_function, processes=None, skip_invalid=True):
    """
    Processes rows using multithreading by applying a row_function to each row.

    This function prepares arguments for each row, including the API key, 
    the processing function, and the skip_invalid flag. It then uses a 
    thread pool (via multiprocessing.dummy.Pool) to apply the function in parallel.

    Args:
        data (list): List of row dictionaries (each row with keys like 'OriginA', 'DestinationB', etc.).
        api_key (str): API key for route data fetching.
        row_function (callable): A function that processes a single row.
            It must return a tuple: (processed_row_dict, api_calls, api_errors).
        processes (int, optional): Number of threads to use (defaults to all available).
        skip_invalid (bool, optional): If True, logs and skips rows with errors;
                                       if False, stops on first error.

    Returns:
        tuple:
            - processed_rows (list): List of processed row dictionaries (with distance, time, etc.).
            - total_api_calls (int): Total number of API calls made across all rows.
            - total_api_errors (int): Total number of rows that encountered errors during API calls.
    """
    args = [(row, api_key, row_function, skip_invalid) for row in data]
    with Pool(processes=processes) as pool:
        results = pool.map(wrap_row, args)

    processed_rows = []
    total_api_calls = 0
    total_api_errors = 0

    for result in results:
        if result is None:
            continue
        row_result, api_calls, api_errors = result
        processed_rows.append(row_result)
        total_api_calls += api_calls
        total_api_errors += api_errors

    return processed_rows, total_api_calls, total_api_errors


def process_row_overlap(row_and_api_key, skip_invalid=True):
    """
    Processes one pair of routes, finds overlap, segments travel, and handles errors based on skip_invalid.

    Args:
        row_and_api_key_skip (tuple): (row, api_key)

    Returns:
        tuple: (result_dict, api_calls, api_errors)
    """
    row, api_key = row_and_api_key
    api_calls = 0

    try:
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            plot_routes(coordinates_a, [], None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": a_dist, "bTime": a_time,
                "overlapDist": a_dist, "overlapTime": a_time,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }, api_calls, 0)

        api_calls += 1
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        api_calls += 1
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": total_distance_a, "aTime": total_time_a,
                "bDist": total_distance_b, "bTime": total_time_b,
                "overlapDist": 0.0, "overlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }, api_calls, 0)

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        api_calls += 1
        start_time = time.time()
        _, before_a_distance, before_a_time = get_route_data(origin_a, f"{before_a[-1][0]},{before_a[-1][1]}", api_key)
        logging.info(f"Time for before_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_a_distance, overlap_a_time = get_route_data(
            f"{overlap_a[0][0]},{overlap_a[0][1]}", f"{overlap_a[-1][0]},{overlap_a[-1][1]}", api_key)
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_a_distance, after_a_time = get_route_data(f"{after_a[0][0]},{after_a[0][1]}", destination_a, api_key)
        logging.info(f"Time for after_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, before_b_distance, before_b_time = get_route_data(origin_b, f"{before_b[-1][0]},{before_b[-1][1]}", api_key)
        logging.info(f"Time for before_b API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_b_distance, after_b_time = get_route_data(f"{after_b[0][0]},{after_b[0][1]}", destination_b, api_key)
        logging.info(f"Time for after_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return ({
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": total_distance_a, "aTime": total_time_a,
            "bDist": total_distance_b, "bTime": total_time_b,
            "overlapDist": overlap_a_distance, "overlapTime": overlap_a_time,
            "aBeforeDist": before_a_distance, "aBeforeTime": before_a_time,
            "bBeforeDist": before_b_distance, "bBeforeTime": before_b_time,
            "aAfterDist": after_a_distance if after_a else 0.0,
            "aAfterTime": after_a_time if after_a else 0.0,
            "bAfterDist": after_b_distance if after_b else 0.0,
            "bAfterTime": after_b_time if after_b else 0.0,
        }, api_calls, 0)

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error in process_row_overlap for row {row}: {str(e)}")
            return ({
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None, "aTime": None,
                "bDist": None, "bTime": None,
                "overlapDist": None, "overlapTime": None,
                "aBeforeDist": None, "aBeforeTime": None,
                "bBeforeDist": None, "bBeforeTime": None,
                "aAfterDist": None, "aAfterTime": None,
                "bAfterDist": None, "bAfterTime": None,
            }, api_calls, 1)
        else:
            raise


def process_routes_with_csv(
    csv_file: str,
    api_key: str,
    output_csv: str = "output.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> tuple:
    """
    Processes route pairs from a CSV file using a row-processing function and writes results to a new CSV file.

    This function:
    - Reads route origin/destination pairs from a CSV file.
    - Maps the user-provided column names to standard labels.
    - Optionally skips or halts on invalid coordinate entries.
    - Uses multithreading.
    - Writes the processed route data to an output CSV file.

    Parameters:
    - csv_file (str): Path to the input CSV file containing the route pairs.
    - api_key (str): Google Maps API key used for fetching travel route data.
    - output_csv (str): File path for saving the output CSV file (default: "output.csv").
    - colorna (str): Column name in the CSV for the origin of route A.
    - coldesta (str): Column name for the destination of route A.
    - colorib (str): Column name for the origin of route B.
    - colfestb (str): Column name for the destination of route B.
    - skip_invalid (bool): If True (default), invalid rows are logged and skipped; if False, processing halts on the first invalid row.

    Returns:
    - tuple: (
        results (list of dicts),
        pre_api_error_count (int),
        total_api_calls (int),
        total_api_errors (int)
      )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    results, total_api_calls, total_api_errors = process_rows(
        data, api_key, process_row_overlap, skip_invalid=skip_invalid
    )

    fieldnames = [
        "OriginA", "DestinationA", "OriginB", "DestinationB",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
        "aBeforeDist", "aBeforeTime", "bBeforeDist", "bBeforeTime",
        "aAfterDist", "aAfterTime", "bAfterDist", "bAfterTime",
    ]

    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, total_api_calls, total_api_errors


def process_row_only_overlap(row_and_api_key, skip_invalid=True):
    """
    Processes a single route pair to compute overlapping travel segments.

    Returns:
    - result_dict (dict): Metrics including distances, times, and overlaps
    - api_calls (int): Number of API calls made for this row
    - api_errors (int): 1 if an exception occurred during processing; 0 otherwise
    """
    row, api_key = row_and_api_key
    api_calls = 0

    try:
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            plot_routes(coordinates_a, [], None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": a_dist, "bTime": a_time,
                "overlapDist": a_dist, "overlapTime": a_time,
            }, api_calls, 0)

        api_calls += 1
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        api_calls += 1
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": total_distance_a, "aTime": total_time_a,
                "bDist": total_distance_b, "bTime": total_time_b,
                "overlapDist": 0.0, "overlapTime": 0.0,
            }, api_calls, 0)

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        api_calls += 1
        start_time = time.time()
        _, overlap_a_distance, overlap_a_time = get_route_data(
            f"{overlap_a[0][0]},{overlap_a[0][1]}",
            f"{overlap_a[-1][0]},{overlap_a[-1][1]}",
            api_key
        )
        logging.info(f"API call for overlap_a took {time.time() - start_time:.2f} seconds")

        overlap_b_distance, overlap_b_time = overlap_a_distance, overlap_a_time

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return ({
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": total_distance_a, "aTime": total_time_a,
            "bDist": total_distance_b, "bTime": total_time_b,
            "overlapDist": overlap_a_distance, "overlapTime": overlap_a_time,
        }, api_calls, 0)

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            return ({
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None, "aTime": None,
                "bDist": None, "bTime": None,
                "overlapDist": None, "overlapTime": None,
            }, api_calls, 1)
        else:
            raise

def process_routes_only_overlap_with_csv(
    csv_file: str,
    api_key: str,
    output_csv: str = "output.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> tuple:
    """
    Processes all route pairs in a CSV to compute overlaps only.

    Returns:
    - results (list): List of processed route dictionaries
    - pre_api_error_count (int): Number of invalid rows skipped before API calls
    - api_call_count (int): Total number of API calls made
    - post_api_error_count (int): Number of errors encountered during processing
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    results, api_call_count, post_api_error_count = process_rows(
        data, api_key, process_row_only_overlap, skip_invalid=skip_invalid
    )

    fieldnames = [
        "OriginA", "DestinationA", "OriginB", "DestinationB",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, api_call_count, post_api_error_count

##The following functions are used for finding approximations around the first and last common node. The approximation is probably more relevant when two routes crosses each other. The code can still be improved.
def great_circle_distance(
    coord1, coord2
):  # Function from Urban Economics and Real Estate course, taught by Professor Benoit Schmutz, Homework 1.
    """
    Compute the great-circle distance between two points using the provided formula.

    Parameters:
    - coord1: tuple of (latitude, longitude)
    - coord2: tuple of (latitude, longitude)

    Returns:
    - float: Distance in meters
    """
    OLA, OLO = coord1
    DLA, DLO = coord2

    # Convert latitude and longitude from degrees to radians
    L1 = OLA * math.pi / 180
    L2 = DLA * math.pi / 180
    DLo = abs(OLO - DLO) * math.pi / 180

    # Apply the great circle formula
    cosd = (math.sin(L1) * math.sin(L2)) + (math.cos(L1) * math.cos(L2) * math.cos(DLo))
    cosd = min(1, max(-1, cosd))  # Ensure cosd is in the range [-1, 1]

    # Take the arc cosine
    dist_degrees = math.acos(cosd) * 180 / math.pi

    # Convert degrees to miles
    dist_miles = 69.16 * dist_degrees

    # Convert miles to kilometers
    dist_km = 1.609 * dist_miles

    return dist_km * 1000  # Convert to meters


def calculate_distances(segment: list, label_prefix: str) -> list:
    """
    Calculates distances and creates labeled segments for a given list of coordinates.

    Parameters:
    - segment (list): A list of (latitude, longitude) tuples.
    - label_prefix (str): The prefix for labeling segments (e.g., 't' or 'T').

    Returns:
    - list: A list of dictionaries, each containing:
        - 'label': The label of the segment (e.g., t1, t2, ...).
        - 'start': Start coordinates of the segment.
        - 'end': End coordinates of the segment.
        - 'distance': Distance (in meters) for the segment.
    """
    segment_details = []
    for i in range(len(segment) - 1):
        start = segment[i]
        end = segment[i + 1]
        distance = great_circle_distance(start, end)
        label = f"{label_prefix}{i + 1}"
        segment_details.append(
            {"label": label, "start": start, "end": end, "distance": distance}
        )
    return segment_details


def calculate_segment_distances(before: list, after: list) -> dict:
    """
    Calculates the distance between each consecutive pair of coordinates in the
    'before' and 'after' segments from the split_segments function.
    Labels the segments as t1, t2, ... for before, and T1, T2, ... for after.

    Parameters:
    - before (list): A list of (latitude, longitude) tuples representing the route before the overlap.
    - after (list): A list of (latitude, longitude) tuples representing the route after the overlap.

    Returns:
    - dict: A dictionary with two keys:
        - 'before_segments': A list of dictionaries containing details about each segment in the 'before' route.
        - 'after_segments': A list of dictionaries containing details about each segment in the 'after' route.
    """
    # Calculate labeled segments for 'before' and 'after'
    before_segments = calculate_distances(before, label_prefix="t")
    after_segments = calculate_distances(after, label_prefix="T")

    return {"before_segments": before_segments, "after_segments": after_segments}


def calculate_rectangle_coordinates(start, end, width: float) -> list:
    """
    Calculates the coordinates of the corners of a rectangle for a given segment.

    Parameters:
    - start (tuple): The starting coordinate of the segment (latitude, longitude).
    - end (tuple): The ending coordinate of the segment (latitude, longitude).
    - width (float): The width of the rectangle in meters.

    Returns:
    - list: A list of 5 tuples representing the corners of the rectangle,
            including the repeated first corner to close the polygon.
    """
    # Calculate unit direction vector of the segment
    dx = end[1] - start[1]
    dy = end[0] - start[0]
    magnitude = (dx**2 + dy**2) ** 0.5
    unit_dx = dx / magnitude
    unit_dy = dy / magnitude

    # Perpendicular vector for the rectangle width
    perp_dx = -unit_dy
    perp_dy = unit_dx

    # Convert width to degrees (approximately)
    half_width = width / 2 / 111_111  # 111,111 meters per degree of latitude

    # Rectangle corner offsets
    offset_x = perp_dx * half_width
    offset_y = perp_dy * half_width

    # Define rectangle corners
    bottom_left = (start[0] - offset_y, start[1] - offset_x)
    top_left = (start[0] + offset_y, start[1] + offset_x)
    bottom_right = (end[0] - offset_y, end[1] - offset_x)
    top_right = (end[0] + offset_y, end[1] + offset_x)

    return [bottom_left, top_left, top_right, bottom_right, bottom_left]


def create_segment_rectangles(segments: list, width: float = 100) -> list:
    """
    Creates rectangles for each segment, where the length of the rectangle is the segment's distance
    and the width is the given default width.

    Parameters:
    - segments (list): A list of dictionaries, each containing:
        - 'label': The label of the segment (e.g., t1, t2, T1, T2).
        - 'start': Start coordinates of the segment.
        - 'end': End coordinates of the segment.
        - 'distance': Length of the segment in meters.
    - width (float): The width of the rectangle in meters (default: 100).

    Returns:
    - list: A list of dictionaries, each containing:
        - 'label': The label of the segment.
        - 'rectangle': A Shapely Polygon representing the rectangle.
    """
    rectangles = []
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        rectangle_coords = calculate_rectangle_coordinates(start, end, width)
        rectangle_polygon = Polygon(rectangle_coords)
        rectangles.append({"label": segment["label"], "rectangle": rectangle_polygon})

    return rectangles


def find_segment_combinations(rectangles_a: list, rectangles_b: list) -> dict:
    """
    Finds all combinations of segments between two routes (A and B).
    Each combination consists of one segment from A and one segment from B.

    Parameters:
    - rectangles_a (list): A list of dictionaries, each representing a rectangle segment from Route A.
        - Each dictionary contains:
            - 'label': The label of the segment (e.g., t1, t2, T1, T2).
            - 'rectangle': A Shapely Polygon representing the rectangle.
    - rectangles_b (list): A list of dictionaries, each representing a rectangle segment from Route B.

    Returns:
    - dict: A dictionary with two keys:
        - 'before_combinations': A list of tuples, each containing:
            - 'segment_a': The label of a segment from Route A.
            - 'segment_b': The label of a segment from Route B.
        - 'after_combinations': A list of tuples, with the same structure as above.
    """
    before_combinations = []
    after_combinations = []

    # Separate rectangles into before and after overlap based on labels
    before_a = [rect for rect in rectangles_a if rect["label"].startswith("t")]
    after_a = [rect for rect in rectangles_a if rect["label"].startswith("T")]
    before_b = [rect for rect in rectangles_b if rect["label"].startswith("t")]
    after_b = [rect for rect in rectangles_b if rect["label"].startswith("T")]

    # Find all combinations for "before" segments
    for rect_a in before_a:
        for rect_b in before_b:
            before_combinations.append((rect_a["label"], rect_b["label"]))

    # Find all combinations for "after" segments
    for rect_a in after_a:
        for rect_b in after_b:
            after_combinations.append((rect_a["label"], rect_b["label"]))

    return {
        "before_combinations": before_combinations,
        "after_combinations": after_combinations,
    }


def calculate_overlap_ratio(polygon_a, polygon_b) -> float:
    """
    Calculates the overlap area ratio between two polygons.

    Parameters:
    - polygon_a: A Shapely Polygon representing the first rectangle.
    - polygon_b: A Shapely Polygon representing the second rectangle.

    Returns:
    - float: The ratio of the overlapping area to the smaller polygon's area, as a percentage.
    """
    intersection = polygon_a.intersection(polygon_b)
    if intersection.is_empty:
        return 0.0

    overlap_area = intersection.area
    smaller_area = min(polygon_a.area, polygon_b.area)
    return (overlap_area / smaller_area) * 100 if smaller_area > 0 else 0.0


def filter_combinations_by_overlap(
    rectangles_a: list, rectangles_b: list, threshold: float = 50
) -> dict:
    """
    Finds and filters segment combinations based on overlapping area ratios.
    Retains only those combinations where the overlapping area is greater than
    the specified threshold of the smaller rectangle's area.

    Parameters:
    - rectangles_a (list): A list of dictionaries representing segments from Route A.
        - Each dictionary contains:
            - 'label': The label of the segment (e.g., t1, t2, T1, T2).
            - 'rectangle': A Shapely Polygon representing the rectangle.
    - rectangles_b (list): A list of dictionaries representing segments from Route B.
    - threshold (float): The minimum percentage overlap required (default: 50).

    Returns:
    - dict: A dictionary with two keys:
        - 'before_combinations': A list of tuples with retained combinations for "before overlap".
        - 'after_combinations': A list of tuples with retained combinations for "after overlap".
    """
    filtered_before_combinations = []
    filtered_after_combinations = []

    # Separate rectangles into before and after overlap
    before_a = [rect for rect in rectangles_a if rect["label"].startswith("t")]
    after_a = [rect for rect in rectangles_a if rect["label"].startswith("T")]
    before_b = [rect for rect in rectangles_b if rect["label"].startswith("t")]
    after_b = [rect for rect in rectangles_b if rect["label"].startswith("T")]

    # Process "before overlap" combinations
    for rect_a in before_a:
        for rect_b in before_b:
            overlap_ratio = calculate_overlap_ratio(
                rect_a["rectangle"], rect_b["rectangle"]
            )
            if overlap_ratio >= threshold:
                filtered_before_combinations.append(
                    (rect_a["label"], rect_b["label"], overlap_ratio)
                )

    # Process "after overlap" combinations
    for rect_a in after_a:
        for rect_b in after_b:
            overlap_ratio = calculate_overlap_ratio(
                rect_a["rectangle"], rect_b["rectangle"]
            )
            if overlap_ratio >= threshold:
                filtered_after_combinations.append(
                    (rect_a["label"], rect_b["label"], overlap_ratio)
                )

    return {
        "before_combinations": filtered_before_combinations,
        "after_combinations": filtered_after_combinations,
    }


def get_segment_by_label(rectangles: list, label: str) -> dict:
    """
    Finds a segment dictionary by its label.

    Parameters:
    - rectangles (list): A list of dictionaries, each representing a segment.
        - Each dictionary contains:
            - 'label': The label of the segment.
            - 'rectangle': A Shapely Polygon representing the rectangle.
    - label (str): The label of the segment to find.

    Returns:
    - dict: The dictionary representing the segment with the matching label.
    - None: If no matching segment is found.
    """
    for rect in rectangles:
        if rect["label"] == label:
            return rect
    return None


def find_overlap_boundary_nodes(
    filtered_combinations: dict, rectangles_a: list, rectangles_b: list
) -> dict:
    """
    Finds the first node of overlapping segments before the overlap and the last node of overlapping
    segments after the overlap for both Route A and Route B.

    Parameters:
    - filtered_combinations (dict): The filtered combinations output from filter_combinations_by_overlap.
        Contains 'before_combinations' and 'after_combinations'.
    - rectangles_a (list): A list of dictionaries representing segments from Route A.
    - rectangles_b (list): A list of dictionaries representing segments from Route B.

    Returns:
    - dict: A dictionary containing:
        - 'first_node_before_overlap': The first overlapping node and its label for Route A and B.
        - 'last_node_after_overlap': The last overlapping node and its label for Route A and B.
    """
    # Get the first combination before the overlap
    first_before_combination = (
        filtered_combinations["before_combinations"][0]
        if filtered_combinations["before_combinations"]
        else None
    )
    # Get the last combination after the overlap
    last_after_combination = (
        filtered_combinations["after_combinations"][-1]
        if filtered_combinations["after_combinations"]
        else None
    )

    first_node_before = None
    last_node_after = None

    if first_before_combination:
        # Extract labels from the first before overlap combination
        label_a, label_b, _ = first_before_combination

        # Find the corresponding segments
        segment_a = get_segment_by_label(rectangles_a, label_a)
        segment_b = get_segment_by_label(rectangles_b, label_b)

        # Get the first node of the segment
        if segment_a and segment_b:
            first_node_before = {
                "label_a": segment_a["label"],
                "node_a": segment_a["rectangle"].exterior.coords[0],
                "label_b": segment_b["label"],
                "node_b": segment_b["rectangle"].exterior.coords[0],
            }

    if last_after_combination:
        # Extract labels from the last after overlap combination
        label_a, label_b, _ = last_after_combination

        # Find the corresponding segments
        segment_a = get_segment_by_label(rectangles_a, label_a)
        segment_b = get_segment_by_label(rectangles_b, label_b)

        # Get the last node of the segment
        if segment_a and segment_b:
            last_node_after = {
                "label_a": segment_a["label"],
                "node_a": segment_a["rectangle"].exterior.coords[
                    -2
                ],  # Second-to-last for the last node
                "label_b": segment_b["label"],
                "node_b": segment_b["rectangle"].exterior.coords[
                    -2
                ],  # Second-to-last for the last node
            }

    return {
        "first_node_before_overlap": first_node_before,
        "last_node_after_overlap": last_node_after,
    }

def wrap_row_multiproc(args):
    """
    Wraps a single row-processing task for use with multithreading.

    This function is intended for use with a multithreading pool. It handles:
    - Passing the required arguments to the row-processing function.
    - Capturing and logging any errors during execution.
    - Respecting the `skip_invalid` flag: either skipping or halting on error.

    Args:
        args (tuple): A tuple containing:
            - row (dict): A dictionary representing one row of the dataset.
            - api_key (str): API key for route data fetching.
            - row_function (callable): The function to process the row.
            - skip_invalid (bool): Whether to skip or raise on error.
            - *extra_args: Additional arguments required by the row function.

    Returns:
        dict or None: Processed row result, or None if skipped due to an error.
    """
    row, api_key, row_function, skip_invalid, *extra_args = args
    return row_function((row, api_key, *extra_args))

def process_rows_multiproc(data, api_key, row_function, processes=None, extra_args=(), skip_invalid=True):
    """
    Processes rows using multithreading and aggregates API call/error counts.

    Returns:
    - results (list): List of processed result dicts
    - api_call_count (int): Total number of API calls across all rows
    - api_error_count (int): Total number of API errors across all rows
    """
    args = [(row, api_key, row_function, skip_invalid, *extra_args) for row in data]
    with Pool(processes=processes) as pool:
        results = pool.map(wrap_row_multiproc, args)

    processed_rows = []
    api_call_count = 0
    api_error_count = 0

    for result in results:
        if result is None:
            continue
        row_result, row_api_calls, row_api_errors = result
        processed_rows.append(row_result)
        api_call_count += row_api_calls
        api_error_count += row_api_errors

    return processed_rows, api_call_count, api_error_count

def process_row_overlap_rec_multiproc(row_and_args):
    """
    Processes a single row using the rectangular overlap method.

    This version includes error handling via the skip_invalid flag:
    - If skip_invalid is True, errors are logged and the row is skipped.
    - If False, exceptions are raised to halt processing.

    Tracks the number of API calls and any errors encountered during processing.

    Args:
        row_and_args (tuple): A tuple containing:
            - row (dict): Route data with OriginA/B and DestinationA/B
            - api_key (str): Google Maps API key
            - width (int): Width for rectangular overlap
            - threshold (int): Overlap filtering threshold
            - skip_invalid (bool): Whether to log and skip or raise on errors

    Returns:
        tuple:
            - result_dict (dict): Processed route metrics
            - api_calls (int): Number of API calls made during processing
            - api_errors (int): 1 if error occurred and was skipped; 0 otherwise
    """
    api_calls = 0

    try:
        row, api_key, width, threshold, skip_invalid = row_and_args

        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            start_time = time.time()
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            logging.info(f"Time for same-route API call: {time.time() - start_time:.2f} seconds")
            plot_routes(coordinates_a, [], None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": a_dist, "bTime": a_time,
                "overlapDist": a_dist, "overlapTime": a_time,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }, api_calls, 0)

        api_calls += 1
        start_time = time.time()
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        logging.info(f"Time for coordinates_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)
        logging.info(f"Time for coordinates_b API call: {time.time() - start_time:.2f} seconds")

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return ({
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": total_distance_a, "aTime": total_time_a,
                "bDist": total_distance_b, "bTime": total_time_b,
                "overlapDist": 0.0, "overlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }, api_calls, 0)

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        a_segment_distances = calculate_segment_distances(before_a, after_a)
        b_segment_distances = calculate_segment_distances(before_b, after_b)

        rectangles_a = create_segment_rectangles(
            a_segment_distances["before_segments"] + a_segment_distances["after_segments"], width=width)
        rectangles_b = create_segment_rectangles(
            b_segment_distances["before_segments"] + b_segment_distances["after_segments"], width=width)

        filtered_combinations = filter_combinations_by_overlap(
            rectangles_a, rectangles_b, threshold=threshold)

        boundary_nodes = find_overlap_boundary_nodes(
            filtered_combinations, rectangles_a, rectangles_b)

        if (
            not boundary_nodes["first_node_before_overlap"]
            or not boundary_nodes["last_node_after_overlap"]
        ):
            boundary_nodes = {
                "first_node_before_overlap": {
                    "node_a": first_common_node,
                    "node_b": first_common_node,
                },
                "last_node_after_overlap": {
                    "node_a": last_common_node,
                    "node_b": last_common_node,
                },
            }

        api_calls += 1
        start_time = time.time()
        _, before_a_dist, before_a_time = get_route_data(
            origin_a,
            f"{boundary_nodes['first_node_before_overlap']['node_a'][0]},{boundary_nodes['first_node_before_overlap']['node_a'][1]}",
            api_key,
        )
        logging.info(f"Time for before_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_a_dist, overlap_a_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_a'][0]},{boundary_nodes['first_node_before_overlap']['node_a'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_a'][0]},{boundary_nodes['last_node_after_overlap']['node_a'][1]}",
            api_key,
        )
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_a_dist, after_a_time = get_route_data(
            f"{boundary_nodes['last_node_after_overlap']['node_a'][0]},{boundary_nodes['last_node_after_overlap']['node_a'][1]}",
            destination_a,
            api_key,
        )
        logging.info(f"Time for after_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, before_b_dist, before_b_time = get_route_data(
            origin_b,
            f"{boundary_nodes['first_node_before_overlap']['node_b'][0]},{boundary_nodes['first_node_before_overlap']['node_b'][1]}",
            api_key,
        )
        logging.info(f"Time for before_b API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_b_dist, overlap_b_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_b'][0]},{boundary_nodes['first_node_before_overlap']['node_b'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_b'][0]},{boundary_nodes['last_node_after_overlap']['node_b'][1]}",
            api_key,
        )
        logging.info(f"Time for overlap_b API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_b_dist, after_b_time = get_route_data(
            f"{boundary_nodes['last_node_after_overlap']['node_b'][0]},{boundary_nodes['last_node_after_overlap']['node_b'][1]}",
            destination_b,
            api_key,
        )
        logging.info(f"Time for after_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return ({
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": total_distance_a, "aTime": total_time_a,
            "bDist": total_distance_b, "bTime": total_time_b,
            "overlapDist": overlap_a_dist, "overlapTime": overlap_a_time,
            "aBeforeDist": before_a_dist, "aBeforeTime": before_a_time,
            "bBeforeDist": before_b_dist, "bBeforeTime": before_b_time,
            "aAfterDist": after_a_dist, "aAfterTime": after_a_time,
            "bAfterDist": after_b_dist, "bAfterTime": after_b_time,
        }, api_calls, 0)

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error in process_row_overlap_rec_multiproc for row {row}: {str(e)}")
            return ({
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None, "aTime": None,
                "bDist": None, "bTime": None,
                "overlapDist": None, "overlapTime": None,
                "aBeforeDist": None, "aBeforeTime": None,
                "bBeforeDist": None, "bBeforeTime": None,
                "aAfterDist": None, "aAfterTime": None,
                "bAfterDist": None, "bAfterTime": None,
            }, api_calls, 1)
        else:
            raise

def overlap_rec(
    csv_file: str,
    api_key: str,
    output_csv: str = "outputRec.csv",
    threshold: int = 50,
    width: int = 100,
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> tuple:
    """
    Processes routes using the rectangular overlap method with a defined threshold and width.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - api_key (str): Google API key for routing.
    - output_csv (str): Path for the output CSV file.
    - threshold (int): Overlap threshold distance.
    - width (int): Buffer width for rectangular overlap.
    - colorna, coldesta, colorib, colfestb (str): Column names for route endpoints.
    - skip_invalid (bool): If True, skips invalid rows and logs them.

    Returns:
    - tuple: (
        results (list): Processed results with travel and overlap metrics,
        pre_api_error_count (int),
        api_call_count (int),
        post_api_error_count (int)
      )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    results, api_call_count, post_api_error_count = process_rows_multiproc(
        data,
        api_key,
        process_row_overlap_rec_multiproc,
        extra_args=(width, threshold, skip_invalid)
    )

    fieldnames = [
        "OriginA", "DestinationA", "OriginB", "DestinationB",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
        "aBeforeDist", "aBeforeTime", "bBeforeDist", "bBeforeTime",
        "aAfterDist", "aAfterTime", "bAfterDist", "bAfterTime",
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, api_call_count, post_api_error_count

def process_row_only_overlap_rec(row_and_args):
    """
    Processes a single row to compute only the overlapping portion of two routes
    using the rectangular buffer approximation method.

    Args:
        row_and_args (tuple): A tuple containing:
            - row (dict): Contains "OriginA", "DestinationA", "OriginB", "DestinationB"
            - api_key (str): Google Maps API key
            - width (int): Width of buffer for overlap detection
            - threshold (int): Distance threshold for overlap detection
            - skip_invalid (bool): Whether to skip errors or halt on first error

    Returns:
        tuple:
            - dict: Dictionary of route and overlap metrics (or None values if error)
            - int: Number of API calls made
            - int: Number of errors encountered (0 or 1)
    """
    row, api_key, width, threshold, skip_invalid = row_and_args
    api_calls = 0

    try:
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            start_time = time.time()
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            logging.info(f"Time for same-route API call: {time.time() - start_time:.2f} seconds")
            plot_routes(coordinates_a, [], None, None)
            return ({
                "OriginA": origin_a,
                "DestinationA": destination_a,
                "OriginB": origin_b,
                "DestinationB": destination_b,
                "aDist": a_dist,
                "aTime": a_time,
                "bDist": a_dist,
                "bTime": a_time,
                "overlapDist": a_dist,
                "overlapTime": a_time,
            }, api_calls, 0)

        api_calls += 1
        start_time = time.time()
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key)
        logging.info(f"Time for coordinates_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key)
        logging.info(f"Time for coordinates_b API call: {time.time() - start_time:.2f} seconds")

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return ({
                "OriginA": origin_a,
                "DestinationA": destination_a,
                "OriginB": origin_b,
                "DestinationB": destination_b,
                "aDist": total_distance_a,
                "aTime": total_time_a,
                "bDist": total_distance_b,
                "bTime": total_time_b,
                "overlapDist": 0.0,
                "overlapTime": 0.0,
            }, api_calls, 0)

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        a_segment_distances = calculate_segment_distances(before_a, after_a)
        b_segment_distances = calculate_segment_distances(before_b, after_b)

        rectangles_a = create_segment_rectangles(
            a_segment_distances["before_segments"] + a_segment_distances["after_segments"], width=width)
        rectangles_b = create_segment_rectangles(
            b_segment_distances["before_segments"] + b_segment_distances["after_segments"], width=width)

        filtered_combinations = filter_combinations_by_overlap(
            rectangles_a, rectangles_b, threshold=threshold)

        boundary_nodes = find_overlap_boundary_nodes(
            filtered_combinations, rectangles_a, rectangles_b)

        if (
            not boundary_nodes["first_node_before_overlap"]
            or not boundary_nodes["last_node_after_overlap"]
        ):
            boundary_nodes = {
                "first_node_before_overlap": {
                    "node_a": first_common_node,
                    "node_b": first_common_node,
                },
                "last_node_after_overlap": {
                    "node_a": last_common_node,
                    "node_b": last_common_node,
                },
            }

        api_calls += 1
        start_time = time.time()
        _, overlap_a_dist, overlap_a_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_a'][0]},{boundary_nodes['first_node_before_overlap']['node_a'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_a'][0]},{boundary_nodes['last_node_after_overlap']['node_a'][1]}",
            api_key,
        )
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_b_dist, overlap_b_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_b'][0]},{boundary_nodes['first_node_before_overlap']['node_b'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_b'][0]},{boundary_nodes['last_node_after_overlap']['node_b'][1]}",
            api_key,
        )
        logging.info(f"Time for overlap_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return ({
            "OriginA": origin_a,
            "DestinationA": destination_a,
            "OriginB": origin_b,
            "DestinationB": destination_b,
            "aDist": total_distance_a,
            "aTime": total_time_a,
            "bDist": total_distance_b,
            "bTime": total_time_b,
            "overlapDist": overlap_a_dist,
            "overlapTime": overlap_a_time,
        }, api_calls, 0)

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            return ({
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "overlapDist": None,
                "overlapTime": None,
            }, api_calls, 1)
        else:
            raise

def only_overlap_rec(
    csv_file: str,
    api_key: str,
    output_csv: str = "outputRec.csv",
    threshold: float = 50,
    width: float = 100,
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> tuple:
    """
    Processes routes to compute only the overlapping rectangular segments based on a threshold and width.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - api_key (str): Google API key for route requests.
    - output_csv (str): Output path for results.
    - threshold (float): Distance threshold for overlap detection.
    - width (float): Width of the rectangular overlap zone.
    - colorna, coldesta, colorib, colfestb (str): Column names for route coordinates.
    - skip_invalid (bool): If True, skips rows with invalid input and logs them.

    Returns:
    - tuple: (
        results (list): Processed results with overlap metrics only,
        pre_api_error_count (int),
        api_call_count (int),
        post_api_error_count (int)
      )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, width, threshold, skip_invalid) for row in data]

    api_call_count = 0
    post_api_error_count = 0
    results = []

    with Pool() as pool:
        raw_results = pool.map(process_row_only_overlap_rec, args_with_flags)

    for res in raw_results:
        if res is None:
            continue
        row_data, row_api_calls, row_errors = res
        api_call_count += row_api_calls
        post_api_error_count += row_errors
        results.append(row_data)

    fieldnames = [
        "OriginA", "DestinationA", "OriginB", "DestinationB",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, api_call_count, post_api_error_count

## The following functions create buffers along the commuting routes to find the ratios of buffers' intersection area over the two routes' total buffer areas.
def calculate_geodetic_area(polygon: Polygon) -> float:
    """
    Calculate the geodetic area of a polygon or multipolygon in square meters using the WGS84 ellipsoid.

    Args:
        polygon (Polygon or MultiPolygon): A shapely Polygon or MultiPolygon object in geographic coordinates (latitude/longitude).

    Returns:
        float: The total area of the polygon or multipolygon in square meters (absolute value).
    """
    geod = Geod(ellps="WGS84")

    start_time = time.time()
    if polygon.geom_type == "Polygon":
        lon, lat = zip(*polygon.exterior.coords)
        area, _ = geod.polygon_area_perimeter(lon, lat)
        logging.info(f"Time to compute geodesic area: {time.time() - start_time:.6f} seconds")
        return abs(area)

    elif polygon.geom_type == "MultiPolygon":
        total_area = 0
        for single_polygon in polygon.geoms:
            lon, lat = zip(*single_polygon.exterior.coords)
            area, _ = geod.polygon_area_perimeter(lon, lat)
            total_area += abs(area)
        logging.info(f"Time to compute geodesic area: {time.time() - start_time:.6f} seconds")
        return total_area

    else:
        raise ValueError(f"Unsupported geometry type: {polygon.geom_type}")

def create_buffered_route(
    route_coords: List[Tuple[float, float]],
    buffer_distance_meters: float,
    projection: str = "EPSG:3857",
) -> Polygon:
    """
    Create a buffer around a geographic route (lat/lon) by projecting to a Cartesian plane.

    Args:
        route_coords (List[Tuple[float, float]]): List of (latitude, longitude) coordinates representing the route.
        buffer_distance_meters (float): Buffer distance in meters.
        projection (str): EPSG code for the projection (default: Web Mercator - EPSG:3857).

    Returns:
        Polygon: Buffered polygon around the route in geographic coordinates (lat/lon), or None if not possible.
    """
    if not route_coords or len(route_coords) < 2:
        print("Warning: Not enough points to create buffer. Returning None.")
        return None

    transformer = Transformer.from_crs("EPSG:4326", projection, always_xy=True)
    inverse_transformer = Transformer.from_crs(projection, "EPSG:4326", always_xy=True)

    projected_coords = [transformer.transform(lon, lat) for lat, lon in route_coords]

    if len(projected_coords) < 2:
        print("Error: Not enough points after projection to create LineString.")
        return None

    start_time = time.time()
    projected_line = LineString(projected_coords)
    logging.info(f"Time to create LineString: {time.time() - start_time:.6f} seconds")

    buffered_polygon = projected_line.buffer(buffer_distance_meters)

    return Polygon([
        inverse_transformer.transform(x, y)
        for x, y in buffered_polygon.exterior.coords
    ])

def plot_routes_and_buffers(
    route_a_coords: List[Tuple[float, float]],
    route_b_coords: List[Tuple[float, float]],
    buffer_a: Polygon,
    buffer_b: Polygon,
) -> None:
    """
    Plot two routes and their respective buffers over an OpenStreetMap background and display it inline.

    Args:
        route_a_coords (List[Tuple[float, float]]): Route A coordinates (latitude, longitude).
        route_b_coords (List[Tuple[float, float]]): Route B coordinates (latitude, longitude).
        buffer_a (Polygon): Buffered polygon for Route A.
        buffer_b (Polygon): Buffered polygon for Route B.

    Returns:
        None
    """

    # Calculate the center of the map
    avg_lat = sum(coord[0] for coord in route_a_coords + route_b_coords) / len(
        route_a_coords + route_b_coords
    )
    avg_lon = sum(coord[1] for coord in route_a_coords + route_b_coords) / len(
        route_a_coords + route_b_coords
    )

    # Create a map centered at the average location of the routes
    map_osm = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    # Add Route A to the map
    folium.PolyLine(
        locations=route_a_coords, color="red", weight=5, opacity=1, tooltip="Route A"
    ).add_to(map_osm)

    # Add Route B to the map
    folium.PolyLine(
        locations=route_b_coords, color="orange", weight=5, opacity=1, tooltip="Route B"
    ).add_to(map_osm)

    # Add Buffer A to the map
    start_time = time.time()
    buffer_a_geojson = mapping(buffer_a)
    logging.info(f"Time to convert buffer A to GeoJSON: {time.time() - start_time:.6f} seconds")
    folium.GeoJson(
        buffer_a_geojson,
        style_function=lambda x: {
            "fillColor": "blue",
            "color": "blue",
            "fillOpacity": 0.5,
            "weight": 2,
        },
        tooltip="Buffer A",
    ).add_to(map_osm)

    # Add Buffer B to the map
    start_time = time.time()
    buffer_b_geojson = mapping(buffer_b)
    logging.info(f"Time to convert buffer B to GeoJSON: {time.time() - start_time:.6f} seconds")
    folium.GeoJson(
        buffer_b_geojson,
        style_function=lambda x: {
            "fillColor": "darkred",
            "color": "darkred",
            "fillOpacity": 0.5,
            "weight": 2,
        },
        tooltip="Buffer B",
    ).add_to(map_osm)

    # Add markers for O1 (Origin A) and O2 (Origin B)
    folium.Marker(
        location=route_a_coords[0],  
        icon=folium.Icon(color="red", icon="info-sign"), 
        tooltip="O1 (Origin A)"
    ).add_to(map_osm)

    folium.Marker(
        location=route_b_coords[0],  
        icon=folium.Icon(color="green", icon="info-sign"), 
        tooltip="O2 (Origin B)"
    ).add_to(map_osm)

    # Add markers for D1 (Destination A) and D2 (Destination B) as stars
    folium.Marker(
        location=route_a_coords[-1],
        tooltip="D1 (Destination A)",
        icon=folium.DivIcon(
            html="""
            <div style="font-size: 16px; color: red; transform: scale(1.4);">
                <i class='fa fa-star'></i>
            </div>
            """
        ),
    ).add_to(map_osm)

    folium.Marker(
        location=route_b_coords[-1],
        tooltip="D2 (Destination B)",
        icon=folium.DivIcon(
            html="""
            <div style="font-size: 16px; color: green; transform: scale(1.4);">
                <i class='fa fa-star'></i>
            </div>
            """
        ),
    ).add_to(map_osm)

    # Save the map using save_map function
    map_filename = save_map(map_osm, "routes_with_buffers_map")

    # Display the map inline
    display(IFrame(map_filename, width="100%", height="600px"))
    print(f"Map has been displayed inline and saved as '{map_filename}'.")


def calculate_area_ratios(
    buffer_a: Polygon, buffer_b: Polygon, intersection: Polygon
) -> Dict[str, float]:
    """
    Calculate the area ratios for the intersection relative to buffer A and buffer B.

    Args:
        buffer_a (Polygon): Buffered polygon for Route A.
        buffer_b (Polygon): Buffered polygon for Route B.
        intersection (Polygon): Intersection polygon of buffers A and B.

    Returns:
        Dict[str, float]: Dictionary containing the area ratios and intersection area.
    """
    # Calculate areas using geodetic area function
    intersection_area = calculate_geodetic_area(intersection)
    area_a = calculate_geodetic_area(buffer_a)
    area_b = calculate_geodetic_area(buffer_b)

    # Compute ratios
    ratio_over_a = (intersection_area / area_a) * 100 if area_a > 0 else 0
    ratio_over_b = (intersection_area / area_b) * 100 if area_b > 0 else 0

    # Return results
    return {
        "IntersectionArea": intersection_area,
        "aAreaRatio": ratio_over_a,
        "bAreaRatio": ratio_over_b,
    }

def process_row_route_buffers(row_and_args):
    """
    Processes a single row to compute route buffers and their intersection ratios.

    This function:
    - Retrieves route data for two routes (A and B).
    - Creates buffered polygons around each route using a specified buffer distance.
    - Computes the intersection area between the buffers.
    - Calculates and returns the intersection ratios for both routes.
    - Handles trivial routes where origin equals destination.
    - Plots the routes and their buffers.
    - Optionally logs and skips invalid rows based on `skip_invalid`.

    Args:
        row_and_args (tuple): Contains:
            - row (dict): Dictionary with OriginA, DestinationA, OriginB, DestinationB
            - api_key (str): Google Maps API key
            - buffer_distance (float): Distance in meters for route buffering
            - skip_invalid (bool): Whether to skip and log errors or raise them

    Returns:
        dict or None: Metrics for the route pair, or None if skipped due to error.
    """
    row, api_key, buffer_distance, skip_invalid = row_and_args

    try:
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == destination_a and origin_b == destination_b:
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0, "aTime": 0, "bDist": 0, "bTime": 0,
                "aIntersecRatio": 0.0, "bIntersecRatio": 0.0,
            }

        if origin_a == destination_a and origin_b != destination_b:
            route_b_coords, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0, "aTime": 0, "bDist": b_dist, "bTime": b_time,
                "aIntersecRatio": 0.0, "bIntersecRatio": 0.0,
            }

        if origin_a != destination_a and origin_b == destination_b:
            route_a_coords, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": 0, "bTime": 0,
                "aIntersecRatio": 0.0, "bIntersecRatio": 0.0,
            }

        route_a_coords, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
        route_b_coords, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(route_a_coords, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(route_a_coords, route_b_coords, buffer_a, buffer_b)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": a_dist, "bTime": a_time,
                "aIntersecRatio": 1.0, "bIntersecRatio": 1.0,
            }

        buffer_a = create_buffered_route(route_a_coords, buffer_distance)
        buffer_b = create_buffered_route(route_b_coords, buffer_distance)

        start_time = time.time()
        intersection = buffer_a.intersection(buffer_b)
        logging.info(f"Time to compute buffer intersection of A and B: {time.time() - start_time:.6f} seconds")

        plot_routes_and_buffers(route_a_coords, route_b_coords, buffer_a, buffer_b)

        if intersection.is_empty:
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": b_dist, "bTime": b_time,
                "aIntersecRatio": 0.0, "bIntersecRatio": 0.0,
            }

        intersection_area = intersection.area
        a_area = buffer_a.area
        b_area = buffer_b.area
        a_intersec_ratio = intersection_area / a_area
        b_intersec_ratio = intersection_area / b_area

        return {
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": a_dist, "aTime": a_time,
            "bDist": b_dist, "bTime": b_time,
            "aIntersecRatio": a_intersec_ratio,
            "bIntersecRatio": b_intersec_ratio,
        }

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            return {
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "aIntersecRatio": None,
                "bIntersecRatio": None,
            }
        else:
            raise

def process_routes_with_buffers(
    csv_file: str,
    output_csv: str,
    api_key: str,
    buffer_distance: float = 100,
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> None:
    """
    Processes two routes from a CSV file to compute buffer intersection ratios.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - output_csv (str): Output file for writing the results.
    - api_key (str): Google API key for route data.
    - buffer_distance (float): Distance in meters for buffering each route.
    - colorna, coldesta, colorib, colfestb (str): Column names in the input CSV.
    - skip_invalid (bool): If True, skips invalid rows and logs them instead of halting.

    Returns:
    - None
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    # Pass skip_invalid flag to each row's args
    args = [(row, api_key, buffer_distance, skip_invalid) for row in data]

    with Pool() as pool:
        results = pool.map(process_row_route_buffers, args)

    # Remove None results if skip_invalid is True
    if skip_invalid:
        results = [r for r in results if r is not None]

    fieldnames = [
        "OriginA", "DestinationA", "OriginB", "DestinationB",
        "aDist", "aTime", "bDist", "bTime",
        "aIntersecRatio", "bIntersecRatio",
    ]

    write_csv_file(output_csv, results, fieldnames)

def calculate_precise_travel_segments(
    route_coords: List[List[float]],
    intersections: List[List[float]],
    api_key: str
) -> Dict[str, float]:
    """
    Calculates travel distances and times for segments of a route before, during,
    and after overlaps using Google Maps Directions API.
    Returns a dictionary with travel segment details.
    All coordinates are in the format [latitude, longitude].
    """

    if len(intersections) < 2:
        print(f"Only {len(intersections)} intersection(s) found, skipping during segment calculation.")
        if len(intersections) == 1:
            start = intersections[0]
            before_data = get_route_data(
                f"{route_coords[0][0]},{route_coords[0][1]}",
                f"{start[0]},{start[1]}",
                api_key
            )
            after_data = get_route_data(
                f"{start[0]},{start[1]}",
                f"{route_coords[-1][0]},{route_coords[-1][1]}",
                api_key
            )
            return {
                "before_distance": before_data[1],
                "before_time": before_data[2],
                "during_distance": 0.0,
                "during_time": 0.0,
                "after_distance": after_data[1],
                "after_time": after_data[2],
            }
        else:
            return {
                "before_distance": 0.0,
                "before_time": 0.0,
                "during_distance": 0.0,
                "during_time": 0.0,
                "after_distance": 0.0,
                "after_time": 0.0,
            }

    start = intersections[0]
    end = intersections[-1]

    before_data = get_route_data(
        f"{route_coords[0][0]},{route_coords[0][1]}",
        f"{start[0]},{start[1]}",
        api_key
    )
    during_data = get_route_data(
        f"{start[0]},{start[1]}",
        f"{end[0]},{end[1]}",
        api_key
    )
    after_data = get_route_data(
        f"{end[0]},{end[1]}",
        f"{route_coords[-1][0]},{route_coords[-1][1]}",
        api_key
    )

    print(f"Before segment: {before_data}")
    print(f"During segment: {during_data}")
    print(f"After segment: {after_data}")

    return {
        "before_distance": before_data[1],
        "before_time": before_data[2],
        "during_distance": during_data[1],
        "during_time": during_data[2],
        "after_distance": after_data[1],
        "after_time": after_data[2],
    }

def get_buffer_intersection(buffer1: Polygon, buffer2: Polygon) -> Polygon:
    """
    Returns the intersection of two buffer polygons.

    Args:
        buffer1 (Polygon): First buffer polygon.
        buffer2 (Polygon): Second buffer polygon.

    Returns:
        Polygon: Intersection polygon of the two buffers, or None if no intersection or invalid input.
    """
    if buffer1 is None or buffer2 is None:
        print("Warning: One or both buffer polygons are None. Cannot compute intersection.")
        return None

    start_time = time.time()
    intersection = buffer1.intersection(buffer2)
    logging.info(f"Time to compute buffer intersection: {time.time() - start_time:.6f} seconds")
    return intersection if not intersection.is_empty else None

def get_route_polygon_intersections(route_coords: List[Tuple[float, float]], polygon: Polygon) -> List[Tuple[float, float]]:
    """
    Finds exact intersection points between a route LineString and a polygon.

    Args:
        route_coords (List[Tuple[float, float]]): The route as list of (lat, lon).
        polygon (Polygon): Polygon to intersect with.

    Returns:
        List[Tuple[float, float]]: List of intersection points in (lat, lon).
    """
    start_time = time.time()
    route_line = LineString([(lon, lat) for lat, lon in route_coords])  # shapely uses (x, y) = (lon, lat)
    logging.info(f"Time to create LineString: {time.time() - start_time:.6f} seconds") 
    intersection = route_line.intersection(polygon)

    if intersection.is_empty:
        return []
    
    # Handle different geometry types
    if isinstance(intersection, Point):
        return [(intersection.y, intersection.x)]
    elif isinstance(intersection, MultiPoint):
        return [(pt.y, pt.x) for pt in intersection.geoms]
    elif isinstance(intersection, LineString):
        return [(pt[1], pt[0]) for pt in intersection.coords]
    else:
        # Can include cases like MultiLineString or GeometryCollection
        return [
            (pt.y, pt.x) for geom in getattr(intersection, 'geoms', []) 
            if isinstance(geom, Point) for pt in [geom]
        ]

# The function calculates travel metrics and overlapping segments between two routes based on their closest nodes and shared buffer intersection.
def process_row_closest_nodes(row_and_args):
    """
    Processes a row of route data to compute overlap metrics using buffered intersection and closest nodes.

    This function:
    - Fetches Google Maps API data for two routes (A and B).
    - Computes buffers for both routes and checks for intersection.
    - Identifies nodes within the intersection and computes before/during/after segments for each route.
    - Returns all relevant travel and overlap metrics.

    Args:
        row_and_args (tuple): A tuple containing:
            - row (dict): The input row with origin and destination fields.
            - api_key (str): Google API key.
            - buffer_distance (float): Buffer distance in meters.
        skip_invalid (bool): Whether to skip rows with errors (default: True).

    Returns:
        dict or None: A dictionary of computed metrics or None if error and skip_invalid is True.
    """
    try:
        row, api_key, buffer_distance, skip_invalid = row_and_args
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == destination_a and origin_b == destination_b:
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        if origin_a == destination_a and origin_b != destination_b:
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": b_dist, "bTime": b_time,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        if origin_a != destination_a and origin_b == destination_b:
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        if origin_a == origin_b and destination_a == destination_b:
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            coords_b = coords_a
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": a_dist, "bTime": a_time,
                "aoverlapDist": a_dist, "aoverlapTime": a_time,
                "boverlapDist": a_dist, "boverlapTime": a_time,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        start_time_a = time.time()
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
        logging.info(f"Time to fetch route A from API: {time.time() - start_time_a:.6f} seconds")
        start_time_b = time.time()
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
        logging.info(f"Time to fetch route B from API: {time.time() - start_time_b:.6f} seconds")

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            overlap_a = overlap_b = {
                "during_distance": 0.0, "during_time": 0.0,
                "before_distance": 0.0, "before_time": 0.0,
                "after_distance": 0.0, "after_time": 0.0,
            }
        else:
            start_time = time.time()
            nodes_inside_a = [pt for pt in coords_a if Point(pt[1], pt[0]).within(intersection_polygon)]
            logging.info(f"Time to check route A points inside intersection: {time.time() - start_time:.6f} seconds")
            start_time = time.time()
            nodes_inside_b = [pt for pt in coords_b if Point(pt[1], pt[0]).within(intersection_polygon)]
            logging.info(f"Time to check route B points inside intersection: {time.time() - start_time:.6f} seconds")

            if len(nodes_inside_a) >= 2:
                entry_a, exit_a = nodes_inside_a[0], nodes_inside_a[-1]
                overlap_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key)
            else:
                overlap_a = {"during_distance": 0.0, "during_time": 0.0,
                             "before_distance": 0.0, "before_time": 0.0,
                             "after_distance": 0.0, "after_time": 0.0}

            if len(nodes_inside_b) >= 2:
                entry_b, exit_b = nodes_inside_b[0], nodes_inside_b[-1]
                overlap_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key)
            else:
                overlap_b = {"during_distance": 0.0, "during_time": 0.0,
                             "before_distance": 0.0, "before_time": 0.0,
                             "after_distance": 0.0, "after_time": 0.0}

        return {
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": a_dist, "aTime": a_time, "bDist": b_dist, "bTime": b_time,
            "aoverlapDist": overlap_a["during_distance"], "aoverlapTime": overlap_a["during_time"],
            "boverlapDist": overlap_b["during_distance"], "boverlapTime": overlap_b["during_time"],
            "aBeforeDist": overlap_a["before_distance"], "aBeforeTime": overlap_a["before_time"],
            "aAfterDist": overlap_a["after_distance"], "aAfterTime": overlap_a["after_time"],
            "bBeforeDist": overlap_b["before_distance"], "bBeforeTime": overlap_b["before_time"],
            "bAfterDist": overlap_b["after_distance"], "bAfterTime": overlap_b["after_time"]
        }

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row if 'row' in locals() else 'unknown'}: {str(e)}")
            return {
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "aoverlapDist": None,
                "aoverlapTime": None,
                "boverlapDist": None,
                "boverlapTime": None,
                "aBeforeDist": None,
                "aBeforeTime": None,
                "aAfterDist": None,
                "aAfterTime": None,
                "bBeforeDist": None,
                "bBeforeTime": None,
                "bAfterDist": None,
                "bAfterTime": None,
            }
        else:
            raise

def process_routes_with_closest_nodes(
    csv_file: str,
    api_key: str,
    buffer_distance: float = 100.0,
    output_csv: str = "output_closest_nodes.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> list:
    """
    Processes two routes using buffered geometries to compute travel overlap details
    based on closest nodes within the intersection.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - api_key (str): Google API key.
    - buffer_distance (float): Distance for the route buffer in meters.
    - output_csv (str): Path to save the output results.
    - colorna, coldesta, colorib, colfestb (str): Column mappings for input.
    - skip_invalid (bool): If True, skips invalid input rows and logs them.

    Returns:
    - list: Processed results written to the output CSV.
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, buffer_distance, skip_invalid) for row in data]

    with Pool() as pool:
        results = pool.map(process_row_closest_nodes, args_with_flags)

    if skip_invalid:
        results = [r for r in results if r is not None]

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results

def process_row_closest_nodes_simple(row_and_args):
    """
    Processes a single row to calculate overlapping travel distances and times between two routes.

    This simplified version:
    - Fetches coordinates and travel info for Route A and B.
    - Buffers both routes and computes their geometric intersection.
    - Finds the nodes that lie within the intersection polygon.
    - Estimates the overlapping segments' travel distance and time based on entry/exit points.

    Args:
        row_and_args (tuple): Tuple containing:
            - row (dict): Input row with OriginA, DestinationA, OriginB, DestinationB.
            - api_key (str): API key for route requests.
            - buffer_distance (float): Distance for route buffer in meters.
        skip_invalid (bool): If True, logs and skips invalid rows on error; otherwise raises the error.

    Returns:
        dict or None: Travel and overlap metrics or None if skipped.
    """
    try:
        row, api_key, buffer_distance, skip_invalid = row_and_args
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == destination_a and origin_b == destination_b:
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        if origin_a == destination_a:
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": b_dist, "bTime": b_time,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        if origin_b == destination_b:
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": a_dist, "bTime": a_time,
                "aoverlapDist": a_dist, "aoverlapTime": a_time,
                "boverlapDist": a_dist, "boverlapTime": a_time,
            }

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            print(f"No intersection for {origin_a} → {destination_a} and {origin_b} → {destination_b}")
            overlap_a_dist = overlap_a_time = overlap_b_dist = overlap_b_time = 0.0
        else:
            nodes_inside_a = [pt for pt in coords_a if Point(pt[1], pt[0]).within(intersection_polygon)]
            nodes_inside_b = [pt for pt in coords_b if Point(pt[1], pt[0]).within(intersection_polygon)]

            if len(nodes_inside_a) >= 2:
                entry_a, exit_a = nodes_inside_a[0], nodes_inside_a[-1]
                segments_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key)
                overlap_a_dist = segments_a.get("during_distance", 0.0)
                overlap_a_time = segments_a.get("during_time", 0.0)
            else:
                overlap_a_dist = overlap_a_time = 0.0

            if len(nodes_inside_b) >= 2:
                entry_b, exit_b = nodes_inside_b[0], nodes_inside_b[-1]
                segments_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key)
                overlap_b_dist = segments_b.get("during_distance", 0.0)
                overlap_b_time = segments_b.get("during_time", 0.0)
            else:
                overlap_b_dist = overlap_b_time = 0.0

        return {
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": a_dist, "aTime": a_time,
            "bDist": b_dist, "bTime": b_time,
            "aoverlapDist": overlap_a_dist, "aoverlapTime": overlap_a_time,
            "boverlapDist": overlap_b_dist, "boverlapTime": overlap_b_time,
        }

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            return {
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "aoverlapDist": None,
                "aoverlapTime": None,
                "boverlapDist": None,
                "boverlapTime": None,
            }
        else:
            raise

def process_routes_with_closest_nodes_simple(
    csv_file: str,
    api_key: str,
    buffer_distance: float = 100.0,
    output_csv: str = "output_closest_nodes_simple.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> list:
    """
    Computes total and overlapping travel segments for two routes using closest-node
    intersection logic without splitting before/during/after, and writes results to CSV.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - api_key (str): Google API key for route data.
    - buffer_distance (float): Distance used for the buffer zone.
    - output_csv (str): Output path for CSV file with results.
    - colorna, coldesta, colorib, colfestb (str): Column names in the CSV.
    - skip_invalid (bool): If True, skips rows with invalid coordinate values.

    Returns:
    - list: Processed result rows.
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, buffer_distance, skip_invalid) for row in data]

    with Pool() as pool:
        results = pool.map(process_row_closest_nodes_simple, args_with_flags)

    if skip_invalid:
        results = [r for r in results if r is not None]

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results

def wrap_row_multiproc_exact(args):
    """
    Wraps a row-processing call for exact intersection calculations using buffered routes.

    This function is intended for use in multithreading. It calls the
    `process_row_exact_intersections` function with the provided row data, API key,
    and buffer distance. If an error occurs and `skip_invalid` is True, the error
    is logged and the row is skipped by returning None.

    Args:
        args (tuple): A tuple containing:
            - row (dict): A dictionary representing a single CSV row.
            - api_key (str): Google Maps API key.
            - buffer_distance (float): Distance for buffer creation in meters.
            - skip_invalid (bool): If True, logs and skips rows with errors.

    Returns:
        dict or None: Processed result or None if skipped due to error.
    """
    row, api_key, buffer_distance, skip_invalid = args
    return process_row_exact_intersections(row, api_key, buffer_distance)

def process_row_exact_intersections(row, api_key, buffer_distance, skip_invalid=True):
    """
    Computes precise overlapping segments between two routes using buffered polygon intersections.

    This function:
    - Fetches route data from origin to destination for both Route A and Route B.
    - Buffers both routes by a specified distance to compute spatial overlap.
    - Determines entry and exit points for overlapping sections within the intersection polygon.
    - Calculates total and segmented travel distances/times (before, during, after overlap).
    - Plots both routes and their buffer zones.
    - Handles errors gracefully based on skip_invalid flag.

    Args:
        row (dict): Dictionary with keys "OriginA", "DestinationA", "OriginB", "DestinationB".
        api_key (str): Google Maps API key.
        buffer_distance (float): Buffer distance in meters to apply to each route.
        skip_invalid (bool): If True, logs and skips errors instead of raising them.

    Returns:
        dict or None: Dictionary of computed metrics, or None if an error occurred and skip_invalid is True.
    """
    try:
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == destination_a and origin_b == destination_b:
            print(f"Skipping row: Origin A == Destination A and Origin B == Destination B ({origin_a}, {destination_a})")
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        if origin_a == destination_a and origin_b != destination_b:
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": b_dist, "bTime": b_time,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        if origin_a != destination_a and origin_b == destination_b:
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
                "aBeforeDist": 0.0, "aBeforeTime": 0.0,
                "aAfterDist": 0.0, "aAfterTime": 0.0,
                "bBeforeDist": 0.0, "bBeforeTime": 0.0,
                "bAfterDist": 0.0, "bAfterTime": 0.0,
            }

        start_time_a = time.time()
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
        logging.info(f"Time to fetch route A from API: {time.time() - start_time_a:.6f} seconds")

        start_time_b = time.time()
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
        logging.info(f"Time to fetch route B from API: {time.time() - start_time_b:.6f} seconds")

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            print(f"No intersection for {origin_a} → {destination_a} and {origin_b} → {destination_b}")
            overlap_a = overlap_b = {
                "during_distance": 0.0, "during_time": 0.0,
                "before_distance": 0.0, "before_time": 0.0,
                "after_distance": 0.0, "after_time": 0.0,
            }
        else:
            points_a = get_route_polygon_intersections(coords_a, intersection_polygon)
            points_b = get_route_polygon_intersections(coords_b, intersection_polygon)

            if len(points_a) >= 2:
                entry_a, exit_a = points_a[0], points_a[-1]
                overlap_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key)
            else:
                print("Not enough route A intersections.")
                overlap_a = {
                    "during_distance": 0.0, "during_time": 0.0,
                    "before_distance": 0.0, "before_time": 0.0,
                    "after_distance": 0.0, "after_time": 0.0,
                }

            if len(points_b) >= 2:
                entry_b, exit_b = points_b[0], points_b[-1]
                overlap_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key)
            else:
                print("Not enough route B intersections.")
                overlap_b = {
                    "during_distance": 0.0, "during_time": 0.0,
                    "before_distance": 0.0, "before_time": 0.0,
                    "after_distance": 0.0, "after_time": 0.0,
                }

        return {
            "OriginA": origin_a,
            "DestinationA": destination_a,
            "OriginB": origin_b,
            "DestinationB": destination_b,
            "aDist": a_dist,
            "aTime": a_time,
            "bDist": b_dist,
            "bTime": b_time,
            "aoverlapDist": overlap_a["during_distance"],
            "aoverlapTime": overlap_a["during_time"],
            "boverlapDist": overlap_b["during_distance"],
            "boverlapTime": overlap_b["during_time"],
            "aBeforeDist": overlap_a["before_distance"],
            "aBeforeTime": overlap_a["before_time"],
            "aAfterDist": overlap_a["after_distance"],
            "aAfterTime": overlap_a["after_time"],
            "bBeforeDist": overlap_b["before_distance"],
            "bBeforeTime": overlap_b["before_time"],
            "bAfterDist": overlap_b["after_distance"],
            "bAfterTime": overlap_b["after_time"],
        }

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            return {
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "aoverlapDist": None,
                "aoverlapTime": None,
                "boverlapDist": None,
                "boverlapTime": None,
                "aBeforeDist": None,
                "aBeforeTime": None,
                "aAfterDist": None,
                "aAfterTime": None,
                "bBeforeDist": None,
                "bBeforeTime": None,
                "bAfterDist": None,
                "bAfterTime": None,
            }
        else:
            raise

def process_routes_with_exact_intersections(
    csv_file: str,
    api_key: str,
    buffer_distance: float = 100.0,
    output_csv: str = "output_exact_intersections.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> list:
    """
    Calculates travel metrics for two routes using exact geometric intersections within buffer polygons,
    including overlapping segments for both routes, and writes results to CSV.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - api_key (str): Google API key for route data.
    - buffer_distance (float): Distance for buffer zone around each route.
    - output_csv (str): Output CSV file path.
    - colorna, coldesta, colorib, colfestb (str): Column names in the CSV.
    - skip_invalid (bool): If True, skip invalid coordinate rows and log them.

    Returns:
    - list: Processed result rows.
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    # Include skip_invalid in the argument tuple
    args_list = [(row, api_key, buffer_distance, skip_invalid) for row in data]

    with Pool() as pool:
        results = pool.map(wrap_row_multiproc_exact, args_list)

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results

def wrap_row_multiproc_simple(args):
    """
    Wraps a single row-processing function for multithreading with error handling.

    This wrapper is designed to work with process pools (e.g., multiprocessing.Pool)
    and supports optional error skipping for robust batch processing.

    Args:
        args (tuple): A tuple containing:
            - row (dict): The input row with origin/destination fields.
            - api_key (str): API key for Google Maps routing.
            - buffer_distance (float): Distance for creating buffer polygons around the route.
            - skip_invalid (bool): If True, log and skip rows that raise exceptions; else re-raise.

    Returns:
        dict or None: The result of processing the row, or None if an error occurred and skip_invalid is True.
    """
    row, api_key, buffer_distance, skip_invalid = args
    return process_row_exact_intersections_simple((row, api_key, buffer_distance))

def process_row_exact_intersections_simple(row_and_args, skip_invalid=True):
    """
    Processes a single row to compute total and overlapping travel metrics between two routes
    using exact geometric intersections of buffered route polygons.

    This simplified version:
    - Uses the Google Maps API to fetch coordinates, distance, and time for both routes.
    - Creates buffers around each route and computes the exact polygon intersection.
    - Finds entry/exit points from each route within the intersection polygon.
    - Calculates travel metrics for overlapping segments using those entry/exit points.
    - Handles degenerate and edge cases (identical routes or points).

    Args:
        row_and_args (tuple): Tuple containing:
            - row (dict): Input with "OriginA", "DestinationA", "OriginB", "DestinationB"
            - api_key (str): Google Maps API key
            - buffer_distance (float): Buffer distance in meters
        skip_invalid (bool): If True, logs and skips errors; if False, raises them.

    Returns:
        dict or None: Dictionary with route and overlap metrics, or None if error and skip_invalid is True.
    """
    try:
        row, api_key, buffer_distance = row_and_args
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        if origin_a == destination_a and origin_b == destination_b:
            print(f"Skipping row: Origin A == Destination A and Origin B == Destination B ({origin_a}, {destination_a})")
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        if origin_a == destination_a:
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)
            logging.info(f"Fetched route B only (A is a point)")
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": 0.0, "aTime": 0.0, "bDist": b_dist, "bTime": b_time,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        if origin_b == destination_b:
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
            logging.info(f"Fetched route A only (B is a point)")
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time, "bDist": 0.0, "bTime": 0.0,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key)
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": a_dist, "bTime": a_time,
                "aoverlapDist": a_dist, "aoverlapTime": a_time,
                "boverlapDist": a_dist, "boverlapTime": a_time,
            }

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            print(f"No intersection for {origin_a} → {destination_a} and {origin_b} → {destination_b}")
            return {
                "OriginA": origin_a, "DestinationA": destination_a,
                "OriginB": origin_b, "DestinationB": destination_b,
                "aDist": a_dist, "aTime": a_time,
                "bDist": b_dist, "bTime": b_time,
                "aoverlapDist": 0.0, "aoverlapTime": 0.0,
                "boverlapDist": 0.0, "boverlapTime": 0.0,
            }

        points_a = get_route_polygon_intersections(coords_a, intersection_polygon)
        points_b = get_route_polygon_intersections(coords_b, intersection_polygon)

        if len(points_a) >= 2:
            entry_a, exit_a = points_a[0], points_a[-1]
            segments_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key)
            overlap_a_dist = segments_a.get("during_distance", 0.0)
            overlap_a_time = segments_a.get("during_time", 0.0)
        else:
            print("Not enough route A intersections.")
            overlap_a_dist = overlap_a_time = 0.0

        if len(points_b) >= 2:
            entry_b, exit_b = points_b[0], points_b[-1]
            segments_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key)
            overlap_b_dist = segments_b.get("during_distance", 0.0)
            overlap_b_time = segments_b.get("during_time", 0.0)
        else:
            print("Not enough route B intersections.")
            overlap_b_dist = overlap_b_time = 0.0

        return {
            "OriginA": origin_a, "DestinationA": destination_a,
            "OriginB": origin_b, "DestinationB": destination_b,
            "aDist": a_dist, "aTime": a_time,
            "bDist": b_dist, "bTime": b_time,
            "aoverlapDist": overlap_a_dist, "aoverlapTime": overlap_a_time,
            "boverlapDist": overlap_b_dist, "boverlapTime": overlap_b_time,
        }

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row if 'row' in locals() else 'unknown'}: {str(e)}")
            return {
                "OriginA": row.get("OriginA", ""),
                "DestinationA": row.get("DestinationA", ""),
                "OriginB": row.get("OriginB", ""),
                "DestinationB": row.get("DestinationB", ""),
                "aDist": None,
                "aTime": None,
                "bDist": None,
                "bTime": None,
                "aoverlapDist": None,
                "aoverlapTime": None,
                "boverlapDist": None,
                "boverlapTime": None,
            }
        else:
            raise

def process_routes_with_exact_intersections_simple(
    csv_file: str,
    api_key: str,
    buffer_distance: float = 100.0,
    output_csv: str = "output_exact_intersections_simple.csv",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    skip_invalid: bool = True
) -> list:
    """
    Processes routes to compute total and overlapping segments using exact geometric intersections,
    without splitting into before/during/after segments. Supports optional skipping of invalid rows.

    Parameters:
    - csv_file (str): Path to input CSV file.
    - api_key (str): Google API key for routing data.
    - buffer_distance (float): Distance for buffering each route.
    - output_csv (str): File path to write the output CSV.
    - colorna, coldesta, colorib, colfestb (str): Column names for route endpoints.
    - skip_invalid (bool): If True, skips invalid coordinate rows and logs them.

    Returns:
    - list: Resulting route overlap metrics.
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        colorna=colorna,
        coldesta=coldesta,
        colorib=colorib,
        colfestb=colfestb,
        skip_invalid=skip_invalid
    )

    # Include skip_invalid in the args tuple
    args = [(row, api_key, buffer_distance, skip_invalid) for row in data]

    with Pool() as pool:
        results = pool.map(wrap_row_multiproc_simple, args)

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results

# Function to write txt file for displaying inputs for the package to run.
def write_log(file_path: str, options: dict) -> None:
    """
    Writes a log file summarizing the inputs used for running the package.

    Args:
        file_path (str): Path of the main CSV result file.
        options (dict): Dictionary of options and their values.
    Returns:
        None
    """
    # Ensure results folder exists
    os.makedirs("results", exist_ok=True)
    base_filename = os.path.basename(file_path).replace(".csv", ".log")

    # Force the log file to be saved inside the results folder
    log_file_path = os.path.join("results", base_filename)

    # Write the log file
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write("Options:\n")
        for key, value in options.items():
            log_file.write(f"{key}: {value}\n")
        log_file.write(f"Generated on: {datetime.datetime.now()}\n")

    print(f"Log file saved to: {os.path.abspath(log_file_path)}")


## This is the main function with user interaction.
def Overlap_Function(
    csv_file: str,
    api_key: str,
    threshold: float = 50,
    width: float = 100,
    buffer: float = 100,
    approximation: str = "no",
    commuting_info: str = "no",
    colorna: str = None,
    coldesta: str = None,
    colorib: str = None,
    colfestb: str = None,
    output_overlap: str = None,
    output_buffer: str = None,
    skip_invalid: bool = True,
    auto_confirm: bool = False
) -> None:
    """
    Main dispatcher function to handle various route overlap and buffer analysis strategies.

    Based on the 'approximation' and 'commuting_info' flags, it routes the execution to one of
    several processing functions that compute route overlaps and buffer intersections, and writes
    results to CSV output files. It also logs options and configurations.

    Parameters:
    - csv_file (str): Path to input CSV file.
    - api_key (str): Google Maps API key.
    - threshold (float): Distance threshold for overlap (if applicable).
    - width (float): Width used for line buffering (if applicable).
    - buffer (float): Buffer radius in meters.
    - approximation (str): Mode of processing (e.g., "no", "yes", "yes with buffer", etc.).
    - commuting_info (str): Whether commuting detail is needed ("yes" or "no").
    - colorna (str): Column name for origin A.
    - coldesta (str): Column name for destination A.
    - colorib (str): Column name for origin B.
    - colfestb (str): Column name for destination B.
    - output_overlap (str): Optional custom filename for overlap results.
    - output_buffer (str): Optional custom filename for buffer results.
    - skip_invalid (bool): If True, skips invalid coordinates and logs the error; if False, halts on error.
    - auto_confirm: bool = False： If True, skips the user confirmation prompt and proceeds automatically.

    Returns:
    - None
    """
    os.makedirs("results", exist_ok=True)

    options = {
        "csv_file": csv_file,
        "api_key": "********",
        "threshold": threshold,
        "width": width,
        "buffer": buffer,
        "approximation": approximation,
        "commuting_info": commuting_info,
        "colorna": colorna,
        "coldesta": coldesta,
        "colorib": colorib,
        "colfestb": colfestb,
    }
    if output_overlap:
        output_overlap = os.path.join("results", os.path.basename(output_overlap))
    if output_buffer:
        output_buffer = os.path.join("results", os.path.basename(output_buffer))

    # Estimate request count and cost 
    try:
        num_requests, estimated_cost = request_cost_estimation(
            csv_file=csv_file,
            approximation=approximation,
            commuting_info=commuting_info,
            colorna=colorna,
            coldesta=coldesta,
            colorib=colorib,
            colfestb=colfestb,
            output_overlap=output_overlap,
            output_buffer=output_buffer,
            skip_invalid=skip_invalid
        )
    except Exception as e:
        print(f"[ERROR] Unable to estimate cost: {e}")
        return

    # Display estimation to user
    print(f"\n[INFO] Estimated number of API requests: {num_requests}")
    print(f"[INFO] Estimated cost: ${estimated_cost:.2f}")
    print("[NOTICE] Actual cost may be higher or lower depending on Google’s pricing tiers and route pair complexity.\n")

    # Ask for user confirmation unless auto_confirm is True
    if not auto_confirm:
        user_input = input("Do you want to proceed with this operation? (yes/no): ").strip().lower()
        if user_input != "yes":
            print("[CANCELLED] Operation aborted by the user.")
            return
    else:
        print("[AUTO-CONFIRM] Skipping user prompt and proceeding...\n")

    # Proceed with processing
    print("[PROCESSING] Proceeding with route analysis...\n")

    if approximation == "yes":
        if commuting_info == "yes":
            output_overlap = output_overlap or generate_unique_filename("results/outputRec", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = overlap_rec(csv_file, api_key, output_csv=output_overlap, threshold=threshold, width=width, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_overlap, options)

        elif commuting_info == "no":
            output_overlap = output_overlap or generate_unique_filename("results/outputRec_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = only_overlap_rec(csv_file, api_key, output_csv=output_overlap, threshold=threshold, width=width, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_overlap, options)

    elif approximation == "no":
        if commuting_info == "yes":
            output_overlap = output_overlap or generate_unique_filename("results/outputRoutes", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_csv(csv_file, api_key, output_csv=output_overlap, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_overlap, options)

        elif commuting_info == "no":
            output_overlap = output_overlap or generate_unique_filename("results/outputRoutes_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_only_overlap_with_csv(csv_file, api_key, output_csv=output_overlap, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_overlap, options)

    elif approximation == "yes with buffer":
        output_buffer = output_buffer or generate_unique_filename("results/buffer_intersection_results", ".csv")
        results, pre_api_errors, api_calls, post_api_errors = process_routes_with_buffers(csv_file=csv_file, output_csv=output_buffer, api_key=api_key, buffer_distance=buffer, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
        options["Pre-API Error Count"] = pre_api_errors
        options["Post-API Error Count"] = post_api_errors
        options["Total API Calls"] = api_calls    
        write_log(output_buffer, options)

    elif approximation == "closer to precision":
        if commuting_info == "yes":
            output_buffer = output_buffer or generate_unique_filename("results/closest_nodes_buffer_results", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_closest_nodes(csv_file=csv_file, api_key=api_key, buffer_distance=buffer, output_csv=output_buffer, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_buffer, options)

        elif commuting_info == "no":
            output_buffer = output_buffer or generate_unique_filename("results/closest_nodes_buffer_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_closest_nodes_simple(csv_file=csv_file, api_key=api_key, buffer_distance=buffer, output_csv=output_buffer, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_buffer, options)

    elif approximation == "exact":
        if commuting_info == "yes":
            output_buffer = output_buffer or generate_unique_filename("results/exact_intersection_buffer_results", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_exact_intersections(csv_file=csv_file, api_key=api_key, buffer_distance=buffer, output_csv=output_buffer, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_buffer, options)

        elif commuting_info == "no":
            output_buffer = output_buffer or generate_unique_filename("results/exact_intersection_buffer_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_exact_intersections_simple(csv_file=csv_file, api_key=api_key, buffer_distance=buffer, output_csv=output_buffer, colorna=colorna, coldesta=coldesta, colorib=colorib, colfestb=colfestb, skip_invalid=skip_invalid)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_buffer, options)
