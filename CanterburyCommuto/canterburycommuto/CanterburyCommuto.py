import csv
import time
import datetime
import logging
import os
import pickle
from typing import Dict, List, Tuple, Optional, Any
from multiprocessing.dummy import Pool

import polyline
import requests
import yaml
from pydantic import BaseModel
from shapely.geometry import Point

# Import functions from modules
from PlotMaps import plot_routes, plot_routes_and_buffers
from HelperFunctions import generate_unique_filename, write_csv_file, generate_url, safe_split
from Computations import (
    find_common_nodes,
    split_segments,
    calculate_segment_distances,
    create_segment_rectangles,
    filter_combinations_by_overlap,
    find_overlap_boundary_nodes,
    create_buffered_route,
    calculate_precise_travel_segments,
    get_buffer_intersection,
    get_route_polygon_intersections,
)

class RouteBase(BaseModel):
    """Base model for route endpoints (split lat/lon) and basic metrics."""
    ID: str
    OriginAlat: float
    OriginAlong: float
    DestinationAlat: float
    DestinationAlong: float
    OriginBlat: float
    OriginBlong: float
    DestinationBlat: float
    DestinationBlong: float
    aDist: Optional[float] = None
    aTime: Optional[float] = None
    bDist: Optional[float] = None
    bTime: Optional[float] = None

class FullOverlapResult(RouteBase):
    """Detailed result with full segment and overlap analysis."""
    overlapDist: Optional[float] = None
    overlapTime: Optional[float] = None
    aBeforeDist: Optional[float] = None
    aBeforeTime: Optional[float] = None
    bBeforeDist: Optional[float] = None
    bBeforeTime: Optional[float] = None
    aAfterDist: Optional[float] = None
    aAfterTime: Optional[float] = None
    bAfterDist: Optional[float] = None
    bAfterTime: Optional[float] = None


class SimpleOverlapResult(RouteBase):
    """Simplified result with only overlap distance and time."""
    overlapDist: Optional[float] = None
    overlapTime: Optional[float] = None


class IntersectionRatioResult(RouteBase):
    """Result showing ratio of route overlap for A and B."""
    aIntersecRatio: Optional[float] = None
    bIntersecRatio: Optional[float] = None

class DetailedDualOverlapResult(RouteBase):
    """Detailed result with A/B overlaps and pre/post overlap segments."""
    aoverlapDist: Optional[float] = None
    aoverlapTime: Optional[float] = None
    boverlapDist: Optional[float] = None
    boverlapTime: Optional[float] = None

    aBeforeDist: Optional[float] = None
    aBeforeTime: Optional[float] = None
    aAfterDist: Optional[float] = None
    aAfterTime: Optional[float] = None

    bBeforeDist: Optional[float] = None
    bBeforeTime: Optional[float] = None
    bAfterDist: Optional[float] = None
    bAfterTime: Optional[float] = None

class SimpleDualOverlapResult(RouteBase):
    """Simplified result with only A/B overlap distances and times."""
    aoverlapDist: Optional[float] = None
    aoverlapTime: Optional[float] = None
    boverlapDist: Optional[float] = None
    boverlapTime: Optional[float] = None

# Global cache for Google API responses
api_response_cache = {}

# Function to read a csv file and then asks the users to manually enter their corresponding column variables with respect to OriginA, DestinationA, OriginB, and DestinationB.
# The following functions also help determine if there are errors in the code. 

# Point to the notebooks directory instead of the script's directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "notebooks"))
log_path = os.path.join(os.getcwd(), "results", "validation_errors_timing.log")

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
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    skip_invalid: bool = True
) -> Tuple[List[Dict[str, str]], int]:
    """
    Reads a CSV file with separate latitude/longitude columns for each endpoint,
    combines them into coordinate strings, and maps to standardized names.
    Optionally handles/generates an ID column.
    Parameters:
    -----------
    csv_file : str
        Path to the input CSV file.
    home_a_lat : str
        Column name for the latitude of home A.
    home_a_lon : str
        Column name for the longitude of home A.
    work_a_lat : str
        Column name for the latitude of work A.
    work_a_lon : str
        Column name for the longitude of work A.
    home_b_lat : str
        Column name for the latitude of home B.
    home_b_lon : str
        Column name for the longitude of home B.
    work_b_lat : str
        Column name for the latitude of work B.
    work_b_lon : str
        Column name for the longitude of work B.
    id_column : Optional[str], default=None
        Column name for the unique ID of each row. If None or not found, IDs are auto-generated as R1, R2, ...
    skip_invalid : bool, default=True
        If True, rows with invalid coordinates are skipped and logged. If False, the function raises an error on invalid data.

    Returns:
    --------
    Tuple[List[Dict[str, str]], int]
        - List of dictionaries, each with standardized keys:
            'ID', 'OriginA', 'DestinationA', 'OriginB', 'DestinationB'
        - Integer count of rows with invalid coordinates that were skipped (0 if skip_invalid is False).

    Notes:
    ------
    - The function expects the CSV to have 8 columns for latitude and longitude, as specified by the input arguments.
    - The function combines each latitude/longitude pair into a single string "lat,lon" for each endpoint.
    - The function ensures each row has an 'ID' field, either from the CSV or auto-generated.
    """
    with open(csv_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        csv_columns = reader.fieldnames

        # Check all required columns exist
        required_columns = [
            home_a_lat, home_a_lon, work_a_lat, work_a_lon,
            home_b_lat, home_b_lon, work_b_lat, work_b_lon
        ]
        for column in required_columns:
            if column not in csv_columns:
                raise ValueError(f"Column '{column}' not found in the CSV file.")

        rows = list(reader)

        # Combine lat/lon into coordinate strings
        for idx, row in enumerate(rows, 1):
            row["OriginA"] = f"{row[home_a_lat].strip()},{row[home_a_lon].strip()}"
            row["DestinationA"] = f"{row[work_a_lat].strip()},{row[work_a_lon].strip()}"
            row["OriginB"] = f"{row[home_b_lat].strip()},{row[home_b_lon].strip()}"
            row["DestinationB"] = f"{row[work_b_lat].strip()},{row[work_b_lon].strip()}"
            # Handle ID column
            if id_column and id_column in csv_columns:
                row["ID"] = row[id_column]
            else:
                row["ID"] = f"R{idx}"

        mapped_data = []
        error_count = 0
        row_number = 1
        for row in rows:
            coords = [
                row["OriginA"],
                row["DestinationA"],
                row["OriginB"],
                row["DestinationB"],
            ]
            invalids = [c for c in coords if not is_valid_coordinate(c)]

            if invalids:
                error_msg = f"Row {row_number} - Invalid coordinates: {invalids}"
                logging.warning(error_msg)
                error_count += 1
                if not skip_invalid:
                    raise ValueError(error_msg)

            # Only keep standardized columns (and ID)
            mapped_row = {
                "ID": row["ID"],
                "OriginA": row["OriginA"],
                "DestinationA": row["DestinationA"],
                "OriginB": row["OriginB"],
                "DestinationB": row["DestinationB"],
            }
            mapped_data.append(mapped_row)
            row_number += 1

        return mapped_data, error_count

def request_cost_estimation(
    csv_file: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    approximation: str = "no",
    commuting_info: str = "no",
    skip_invalid: bool = True
) -> Tuple[int, float]:
    """
    Estimates the number of Google API requests needed based on route pair data
    and approximates the cost.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - home_a_lat : Column name for the latitude of home A.
    - home_a_lon : Column name for the longitude of home A.
    - work_a_lat : Column name for the latitude of work A.
    - work_a_lon : Column name for the longitude of work A.
    - home_b_lat : Column name for the latitude of home B.
    - home_b_lon : Column name for the longitude of home B.
    - work_b_lat : Column name for the latitude of work B.
    - work_b_lon : Column name for the longitude of work B.
    - id_column : Column name for the unique ID of each row. If None or not found, IDs are auto-generated as R1, R2, ...
    - approximation (str): Approximation strategy to apply.
    - commuting_info (str): Whether commuting info is to be considered.
    - skip_invalid (bool): Whether to skip invalid rows.

    Returns:
    - Tuple[int, float]: Estimated number of API requests and corresponding cost in USD.
    """
    data_set, pre_api_error_count = read_csv_file(csv_file, home_a_lat, home_a_lon,
    work_a_lat,
    work_a_lon,
    home_b_lat,
    home_b_lon,
    work_b_lat,
    work_b_lon,
    id_column, skip_invalid=skip_invalid)
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
            n += 1 if same_a and same_b else (7 if commuting_info == "yes" else 4)

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

def get_route_data(origin: str, destination: str, api_key: str, save_api_info: bool = False) -> tuple:
    """
    Fetches route data from the Google Maps Directions API and decodes it.

    Parameters:
    - origin (str): The starting point of the route (latitude,longitude).
    - destination (str): The endpoint of the route (latitude,longitude).
    - api_key (str): The API key for accessing the Google Maps Directions API.
    - save_api_info (bool): Whether to save the raw API response in a global dictionary.

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

    # Save the raw response if required
    if save_api_info:
        api_response_cache[(origin, destination)] = directions_data

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
            - save_api_info (bool): whether to save the Googel API response.

    Returns:
        dict or None: Result of processing the row, or None if skipped.
    """
    row, api_key, row_function, skip_invalid, save_api_info = args
    return row_function((row, api_key, save_api_info), skip_invalid=skip_invalid)


def process_rows(data, api_key, row_function, processes=None, skip_invalid=True, save_api_info=False):
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
        save_api_info (bool, optional): If True, saves API response;
                                        if False, does not save the API response.

    Returns:
        tuple:
            - processed_rows (list): List of processed row dictionaries (with distance, time, etc.).
            - total_api_calls (int): Total number of API calls made across all rows.
            - total_api_errors (int): Total number of rows that encountered errors during API calls.
    """
    args = [(row, api_key, row_function, skip_invalid, save_api_info) for row in data]
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


def process_row_overlap(row_and_api_key_and_flag, skip_invalid=True):
    """
    Processes one pair of routes, finds overlap, segments travel, and handles errors based on skip_invalid.

    Args:
        row_and_api_key_and_flag (tuple): (row, api_key, save_api_info)

    Returns:
        tuple: (result_dict, api_calls, api_errors)
    """
    row, api_key, save_api_info = row_and_api_key_and_flag
    api_calls = 0

    try:
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        # Split "lat,lon" into separate variables for each endpoint
        origin_a_lat, origin_a_lon = map(str.strip, origin_a.split(","))
        destination_a_lat, destination_a_lon = map(str.strip, destination_a.split(","))
        origin_b_lat, origin_b_lon = map(str.strip, origin_b.split(","))
        destination_b_lat, destination_b_lon = map(str.strip, destination_b.split(","))

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info)
            plot_routes(coordinates_a, [], None, None)
            # Return structured full overlap result as a dictionary, along with API stats
            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,           
                    bTime=a_time,
                    overlapDist=a_dist,
                    overlapTime=a_time,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0  # no error flag
            )
        
        api_calls += 1
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key, save_api_info)
        api_calls += 1
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key, save_api_info)

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=total_distance_a,
                    aTime=total_time_a,
                    bDist=total_distance_b,
                    bTime=total_time_b,
                    overlapDist=0.0,
                    overlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        api_calls += 1
        start_time = time.time()
        _, before_a_distance, before_a_time = get_route_data(origin_a, f"{before_a[-1][0]},{before_a[-1][1]}", api_key, save_api_info)
        logging.info(f"Time for before_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_a_distance, overlap_a_time = get_route_data(
            f"{overlap_a[0][0]},{overlap_a[0][1]}", f"{overlap_a[-1][0]},{overlap_a[-1][1]}", api_key, save_api_info)
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_a_distance, after_a_time = get_route_data(f"{after_a[0][0]},{after_a[0][1]}", destination_a, api_key, save_api_info)
        logging.info(f"Time for after_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, before_b_distance, before_b_time = get_route_data(origin_b, f"{before_b[-1][0]},{before_b[-1][1]}", api_key, save_api_info)
        logging.info(f"Time for before_b API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_b_distance, after_b_time = get_route_data(f"{after_b[0][0]},{after_b[0][1]}", destination_b, api_key, save_api_info)
        logging.info(f"Time for after_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return (
            FullOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=total_distance_a,
                aTime=total_time_a,
                bDist=total_distance_b,
                bTime=total_time_b,
                overlapDist=overlap_a_distance,
                overlapTime=overlap_a_time,
                aBeforeDist=before_a_distance,
                aBeforeTime=before_a_time,
                bBeforeDist=before_b_distance,
                bBeforeTime=before_b_time,
                aAfterDist=after_a_distance if after_a else 0.0,
                aAfterTime=after_a_time if after_a else 0.0,
                bAfterDist=after_b_distance if after_b else 0.0,
                bAfterTime=after_b_time if after_b else 0.0,
            ).model_dump(),
            api_calls,
            0
        )


    except Exception as e:
        if skip_invalid:
            logging.error(f"Error in process_row_overlap for row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))
            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    overlapDist=None,
                    overlapTime=None,
                    aBeforeDist=None,
                    aBeforeTime=None,
                    bBeforeDist=None,
                    bBeforeTime=None,
                    aAfterDist=None,
                    aAfterTime=None,
                    bAfterDist=None,
                    bAfterTime=None,
                ).model_dump(),
                api_calls,
                1
            )

        else:
            raise


def process_routes_with_csv(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    output_csv: str = "output.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
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
    - home_a_lat : Column name for the latitude of home A.
    - home_a_lon : Column name for the longitude of home A.
    - work_a_lat : Column name for the latitude of work A.
    - work_a_lon : Column name for the longitude of work A.
    - home_b_lat : Column name for the latitude of home B.
    - home_b_lon : Column name for the longitude of home B.
    - work_b_lat : Column name for the latitude of work B.
    - work_b_lon : Column name for the longitude of work B.
    - id_column : Column name for the unique ID of each row. If None or not found, IDs are auto-generated as R1, R2, ...
    - output_csv (str): File path for saving the output CSV file (default: "output.csv").
    - skip_invalid (bool): If True (default), invalid rows are logged and skipped; if False, processing halts on the first invalid row.
    - save_api_info (bool): If True, API responses are saved; if False, API responses are not saved.

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
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    results, total_api_calls, total_api_errors = process_rows(
        data, api_key, process_row_overlap, skip_invalid=skip_invalid, save_api_info=save_api_info
    )

    fieldnames = [
        "ID", "OriginAlat", "OriginAlong", "DestinationAlat", "DestinationAlong", 
        "OriginBlat", "OriginBlong", "DestinationBlat", "DestinationBlong",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
        "aBeforeDist", "aBeforeTime", "bBeforeDist", "bBeforeTime",
        "aAfterDist", "aAfterTime", "bAfterDist", "bAfterTime",
    ]

    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, total_api_calls, total_api_errors


def process_row_only_overlap(row_api_and_flag, skip_invalid=True):
    """
    Processes a single route pair to compute overlapping travel segments.

    Returns:
    - result_dict (dict): Metrics including distances, times, and overlaps
    - api_calls (int): Number of API calls made for this row
    - api_errors (int): 1 if an exception occurred during processing; 0 otherwise
    """
    row, api_key, save_api_info = row_api_and_flag
    api_calls = 0

    try:
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        # Split and convert to float
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info)
            plot_routes(coordinates_a, [], None, None)
            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    overlapDist=a_dist,
                    overlapTime=a_time,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key, save_api_info)
        api_calls += 1
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key, save_api_info)

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=total_distance_a,
                    aTime=total_time_a,
                    bDist=total_distance_b,
                    bTime=total_time_b,
                    overlapDist=0.0,
                    overlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        before_a, overlap_a, after_a = split_segments(coordinates_a, first_common_node, last_common_node)
        before_b, overlap_b, after_b = split_segments(coordinates_b, first_common_node, last_common_node)

        api_calls += 1
        start_time = time.time()
        _, overlap_a_distance, overlap_a_time = get_route_data(
            f"{overlap_a[0][0]},{overlap_a[0][1]}",
            f"{overlap_a[-1][0]},{overlap_a[-1][1]}",
            api_key,
            save_api_info
        )
        logging.info(f"API call for overlap_a took {time.time() - start_time:.2f} seconds")

        overlap_b_distance, overlap_b_time = overlap_a_distance, overlap_a_time

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return (
            SimpleOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=total_distance_a,
                aTime=total_time_a,
                bDist=total_distance_b,
                bTime=total_time_b,
                overlapDist=overlap_a_distance,
                overlapTime=overlap_a_time,
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    overlapDist=None,
                    overlapTime=None,
                ).model_dump(),
                api_calls,
                1
            )
        else:
            raise

def process_routes_only_overlap_with_csv(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    output_csv: str = "output.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
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
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    results, api_call_count, post_api_error_count = process_rows(
        data, api_key, process_row_only_overlap, skip_invalid=skip_invalid, save_api_info=save_api_info
    )

    fieldnames = [
        "ID", "OriginAlat", "OriginAlong", "DestinationAlat", "DestinationAlong", 
        "OriginBlat", "OriginBlong", "DestinationBlat", "DestinationBlong",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
    ]
    write_csv_file(output_csv, results, fieldnames)

    return results, pre_api_error_count, api_call_count, post_api_error_count

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
    row, api_key, row_function, skip_invalid, save_api_info, *extra_args = args
    return row_function((row, api_key, *extra_args, skip_invalid, save_api_info))

def process_rows_multiproc(data, api_key, row_function, processes=None, extra_args=(), skip_invalid=True, save_api_info=False):
    """
    Processes rows using multithreading and aggregates API call/error counts.

    Returns:
    - results (list): List of processed result dicts
    - api_call_count (int): Total number of API calls across all rows
    - api_error_count (int): Total number of API errors across all rows
    """
    args = [(row, api_key, *extra_args, skip_invalid, save_api_info) for row in data]
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
            - save_api_info (bool): Whether to save the API response

    Returns:
        tuple:
            - result_dict (dict): Processed route metrics
            - api_calls (int): Number of API calls made during processing
            - api_errors (int): 1 if error occurred and was skipped; 0 otherwise
    """
    api_calls = 0

    try:
        row, api_key, width, threshold, skip_invalid, save_api_info = row_and_args
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            start_time = time.time()
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info)
            logging.info(f"Time for same-route API call: {time.time() - start_time:.2f} seconds")
            plot_routes(coordinates_a, [], None, None)
            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    overlapDist=a_dist,
                    overlapTime=a_time,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        start_time = time.time()
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key, save_api_info)
        logging.info(f"Time for coordinates_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key, save_api_info)
        logging.info(f"Time for coordinates_b API call: {time.time() - start_time:.2f} seconds")

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=total_distance_a,
                    aTime=total_time_a,
                    bDist=total_distance_b,
                    bTime=total_time_b,
                    overlapDist=0.0,
                    overlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )


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
            save_api_info
        )
        logging.info(f"Time for before_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_a_dist, overlap_a_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_a'][0]},{boundary_nodes['first_node_before_overlap']['node_a'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_a'][0]},{boundary_nodes['last_node_after_overlap']['node_a'][1]}",
            api_key,
            save_api_info
        )
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_a_dist, after_a_time = get_route_data(
            f"{boundary_nodes['last_node_after_overlap']['node_a'][0]},{boundary_nodes['last_node_after_overlap']['node_a'][1]}",
            destination_a,
            api_key,
            save_api_info
        )
        logging.info(f"Time for after_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, before_b_dist, before_b_time = get_route_data(
            origin_b,
            f"{boundary_nodes['first_node_before_overlap']['node_b'][0]},{boundary_nodes['first_node_before_overlap']['node_b'][1]}",
            api_key,
            save_api_info
        )
        logging.info(f"Time for before_b API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, after_b_dist, after_b_time = get_route_data(
            f"{boundary_nodes['last_node_after_overlap']['node_b'][0]},{boundary_nodes['last_node_after_overlap']['node_b'][1]}",
            destination_b,
            api_key,
            save_api_info
        )
        logging.info(f"Time for after_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return (
            FullOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=total_distance_a,
                aTime=total_time_a,
                bDist=total_distance_b,
                bTime=total_time_b,
                overlapDist=overlap_a_dist,
                overlapTime=overlap_a_time,
                aBeforeDist=before_a_dist,
                aBeforeTime=before_a_time,
                bBeforeDist=before_b_dist,
                bBeforeTime=before_b_time,
                aAfterDist=after_a_dist,
                aAfterTime=after_a_time,
                bAfterDist=after_b_dist,
                bAfterTime=after_b_time,
            ).model_dump(),
        api_calls,
        0
    )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error in process_row_overlap_rec_multiproc for row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                FullOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    overlapDist=None,
                    overlapTime=None,
                    aBeforeDist=None,
                    aBeforeTime=None,
                    bBeforeDist=None,
                    bBeforeTime=None,
                    aAfterDist=None,
                    aAfterTime=None,
                    bAfterDist=None,
                    bAfterTime=None,
                ).model_dump(),
                api_calls,
                1
            )

        else:
            raise

def overlap_rec(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    output_csv: str = "outputRec.csv",
    threshold: int = 50,
    width: int = 100,
    skip_invalid: bool = True,
    save_api_info: bool = False
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
    - save_api_info (bool): If True, save API response.

    Returns:
    - tuple: (
        results (list): Processed results with travel and overlap metrics,
        pre_api_error_count (int),
        api_call_count (int),
        post_api_error_count (int)
      )
    """
    # 1. Read input CSV
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    # 2. Prepare arguments for parallel processing
    args = [(row, api_key, width, threshold, skip_invalid, save_api_info) for row in data]

    # 3. Run in parallel
    with Pool() as pool:
        results = pool.map(process_row_overlap_rec_multiproc, args)

    # 4. Post-process results
    processed_rows = []
    api_call_count = 0
    post_api_error_count = 0

    for result in results:
        if result is None:
            continue
        row_result, calls, errors = result
        processed_rows.append(row_result)
        api_call_count += calls
        post_api_error_count += errors

    # 5. Write results to CSV
    if processed_rows:
        fieldnames = list(processed_rows[0].keys())
        write_csv_file(output_csv, processed_rows, fieldnames)

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
    row, api_key, width, threshold, skip_invalid, save_api_info = row_and_args
    api_calls = 0

    try:
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))


        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            start_time = time.time()
            coordinates_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            logging.info(f"Time for same-route API call: {time.time() - start_time:.2f} seconds")
            plot_routes(coordinates_a, [], None, None)
            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    overlapDist=a_dist,
                    overlapTime=a_time,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        start_time = time.time()
        coordinates_a, total_distance_a, total_time_a = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
        logging.info(f"Time for coordinates_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        coordinates_b, total_distance_b, total_time_b = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
        logging.info(f"Time for coordinates_b API call: {time.time() - start_time:.2f} seconds")

        first_common_node, last_common_node = find_common_nodes(coordinates_a, coordinates_b)

        if not first_common_node or not last_common_node:
            plot_routes(coordinates_a, coordinates_b, None, None)
            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=total_distance_a,
                    aTime=total_time_a,
                    bDist=total_distance_b,
                    bTime=total_time_b,
                    overlapDist=0.0,
                    overlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

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
            save_api_info=save_api_info
        )
        logging.info(f"Time for overlap_a API call: {time.time() - start_time:.2f} seconds")

        api_calls += 1
        start_time = time.time()
        _, overlap_b_dist, overlap_b_time = get_route_data(
            f"{boundary_nodes['first_node_before_overlap']['node_b'][0]},{boundary_nodes['first_node_before_overlap']['node_b'][1]}",
            f"{boundary_nodes['last_node_after_overlap']['node_b'][0]},{boundary_nodes['last_node_after_overlap']['node_b'][1]}",
            api_key,
            save_api_info=save_api_info
        )
        logging.info(f"Time for overlap_b API call: {time.time() - start_time:.2f} seconds")

        plot_routes(coordinates_a, coordinates_b, first_common_node, last_common_node)

        return (
            SimpleOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=total_distance_a,
                aTime=total_time_a,
                bDist=total_distance_b,
                bTime=total_time_b,
                overlapDist=overlap_a_dist,
                overlapTime=overlap_a_time,
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                SimpleOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    overlapDist=None,
                    overlapTime=None,
                ).model_dump(),
                api_calls,
                1
            )

        else:
            raise

def only_overlap_rec(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    output_csv: str = "outputRec.csv",
    threshold: float = 50,
    width: float = 100,
    skip_invalid: bool = True,
    save_api_info: bool = False
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
    - save_api_info (bool): If True, saves API response.

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
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, width, threshold, skip_invalid, save_api_info) for row in data]

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
        "ID", "OriginAlat", "OriginAlong", "DestinationAlat", "DestinationAlong", 
        "OriginBlat", "OriginBlong", "DestinationBlat", "DestinationBlong",
        "aDist", "aTime", "bDist", "bTime",
        "overlapDist", "overlapTime",
    ]
    write_csv_file(output_csv, results, fieldnames)

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
        tuple:
            - dict: Metrics for the route pair
            - int: Number of API calls made
            - int: 1 if skipped due to error, else 0
    """
    row, api_key, buffer_distance, skip_invalid, save_api_info = row_and_args
    api_calls = 0

    try:
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]
        # Split and convert to float
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == destination_a and origin_b == destination_b:
            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0,
                    aTime=0,
                    bDist=0,
                    bTime=0,
                    aIntersecRatio=0.0,
                    bIntersecRatio=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == destination_a and origin_b != destination_b:
            api_calls += 1
            route_b_coords, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0,
                    aTime=0,
                    bDist=b_dist,
                    bTime=b_time,
                    aIntersecRatio=0.0,
                    bIntersecRatio=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a != destination_a and origin_b == destination_b:
            api_calls += 1
            route_a_coords, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=0,
                    bTime=0,
                    aIntersecRatio=0.0,
                    bIntersecRatio=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        route_a_coords, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)

        api_calls += 1
        route_b_coords, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(route_a_coords, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(route_a_coords, route_b_coords, buffer_a, buffer_b)
            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    aIntersecRatio=1.0,
                    bIntersecRatio=1.0,
                ).model_dump(),
                api_calls,
                0
            )

        buffer_a = create_buffered_route(route_a_coords, buffer_distance)
        buffer_b = create_buffered_route(route_b_coords, buffer_distance)

        start_time = time.time()
        intersection = buffer_a.intersection(buffer_b)
        logging.info(f"Time to compute buffer intersection of A and B: {time.time() - start_time:.6f} seconds")

        plot_routes_and_buffers(route_a_coords, route_b_coords, buffer_a, buffer_b)

        if intersection.is_empty:
            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=b_dist,
                    bTime=b_time,
                    aIntersecRatio=0.0,
                    bIntersecRatio=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        intersection_area = intersection.area
        a_area = buffer_a.area
        b_area = buffer_b.area
        a_intersec_ratio = intersection_area / a_area
        b_intersec_ratio = intersection_area / b_area

        return (
            IntersectionRatioResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=a_dist,
                aTime=a_time,
                bDist=b_dist,
                bTime=b_time,
                aIntersecRatio=a_intersec_ratio,
                bIntersecRatio=b_intersec_ratio,
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                IntersectionRatioResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    aIntersecRatio=None,
                    bIntersecRatio=None,
                ).model_dump(),
                api_calls,
                1
            )

        else:
            raise

def process_routes_with_buffers(
    csv_file: str,
    api_key: str,
    output_csv: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    buffer_distance: float = 100,
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> tuple:
    """
    Processes two routes from a CSV file to compute buffer intersection ratios.

    Parameters:
    - csv_file (str): Path to the input CSV file.
    - output_csv (str): Output file for writing the results.
    - api_key (str): Google API key for route data.
    - buffer_distance (float): Distance in meters for buffering each route.
    - colorna, coldesta, colorib, colfestb (str): Column names in the input CSV.
    - skip_invalid (bool): If True, skips invalid rows and logs them instead of halting.
    - save_api_info (bool): If True, saves API response.

    Returns:
    - tuple: (
        results (list of dicts),
        pre_api_error_count (int),
        total_api_calls (int),
        post_api_error_count (int)
    )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args = [(row, api_key, buffer_distance, skip_invalid, save_api_info) for row in data]

    with Pool() as pool:
        raw_results = pool.map(process_row_route_buffers, args)

    results = []
    total_api_calls = 0
    post_api_error_count = 0

    for r in raw_results:
        if r is None:
            continue
        result_dict, api_calls, api_errors = r
        results.append(result_dict)
        total_api_calls += api_calls
        post_api_error_count += api_errors

    fieldnames = [
        "ID", "OriginAlat", "OriginAlong", "DestinationAlat", "DestinationAlong", 
        "OriginBlat", "OriginBlong", "DestinationBlat", "DestinationBlong",
        "aDist", "aTime", "bDist", "bTime",
        "aIntersecRatio", "bIntersecRatio",
    ]

    write_csv_file(output_csv, results, fieldnames)


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
        tuple: (result_dict, api_calls, api_errors)
    """
    api_calls = 0
    try:
        row, api_key, buffer_distance, skip_invalid, save_api_info = row_and_args
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]
        # Split and convert to float
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == destination_a and origin_b == destination_b:
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == destination_a and origin_b != destination_b:
            api_calls += 1
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=b_dist,
                    bTime=b_time,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a != destination_a and origin_b == destination_b:
            api_calls += 1
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == origin_b and destination_a == destination_b:
            api_calls += 1
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            coords_b = coords_a
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    aoverlapDist=a_dist,
                    aoverlapTime=a_time,
                    boverlapDist=a_dist,
                    boverlapTime=a_time,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 2
        start_time_a = time.time()
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
        logging.info(f"Time to fetch route A from API: {time.time() - start_time_a:.6f} seconds")
        start_time_b = time.time()
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
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
                api_calls += 1
                overlap_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key, save_api_info=save_api_info)
            else:
                overlap_a = {"during_distance": 0.0, "during_time": 0.0,
                             "before_distance": 0.0, "before_time": 0.0,
                             "after_distance": 0.0, "after_time": 0.0}

            if len(nodes_inside_b) >= 2:
                entry_b, exit_b = nodes_inside_b[0], nodes_inside_b[-1]
                api_calls += 1
                overlap_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key, save_api_info=save_api_info)
            else:
                overlap_b = {"during_distance": 0.0, "during_time": 0.0,
                             "before_distance": 0.0, "before_time": 0.0,
                             "after_distance": 0.0, "after_time": 0.0}

        return (
            DetailedDualOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=a_dist,
                aTime=a_time,
                bDist=b_dist,
                bTime=b_time,
                aoverlapDist=overlap_a["during_distance"],
                aoverlapTime=overlap_a["during_time"],
                boverlapDist=overlap_b["during_distance"],
                boverlapTime=overlap_b["during_time"],
                aBeforeDist=overlap_a["before_distance"],
                aBeforeTime=overlap_a["before_time"],
                aAfterDist=overlap_a["after_distance"],
                aAfterTime=overlap_a["after_time"],
                bBeforeDist=overlap_b["before_distance"],
                bBeforeTime=overlap_b["before_time"],
                bAfterDist=overlap_b["after_distance"],
                bAfterTime=overlap_b["after_time"]
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row if 'row' in locals() else 'unknown'}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    aoverlapDist=None,
                    aoverlapTime=None,
                    boverlapDist=None,
                    boverlapTime=None,
                    aBeforeDist=None,
                    aBeforeTime=None,
                    aAfterDist=None,
                    aAfterTime=None,
                    bBeforeDist=None,
                    bBeforeTime=None,
                    bAfterDist=None,
                    bAfterTime=None,
                ).model_dump(),
                api_calls,
                1
            )
        else:
            raise

def process_routes_with_closest_nodes(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    buffer_distance: float = 100.0,
    output_csv: str = "output_closest_nodes.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> tuple:
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
    - save_api_info (bool): If True, save API response.

    Returns:
    - tuple: (
        results (list): Processed route rows,
        pre_api_error_count (int): Invalid before routing,
        total_api_calls (int): Number of API calls made,
        post_api_error_count (int): Failures during processing
      )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, buffer_distance, skip_invalid, save_api_info) for row in data]

    with Pool() as pool:
        raw_results = pool.map(process_row_closest_nodes, args_with_flags)

    results = []
    total_api_calls = 0
    post_api_error_count = 0

    for res in raw_results:
        if res is None:
            continue
        row_result, api_calls, api_errors = res
        results.append(row_result)
        total_api_calls += api_calls
        post_api_error_count += api_errors

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results, pre_api_error_count, total_api_calls, post_api_error_count

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
        tuple: (result_dict, api_calls, api_errors)
    """
    api_calls = 0
    try:
        row, api_key, buffer_distance, skip_invalid, save_api_info = row_and_args
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        # Split and convert to float
        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == destination_a and origin_b == destination_b:
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == destination_a:
            api_calls += 1
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=b_dist,
                    bTime=b_time,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_b == destination_b:
            api_calls += 1
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)

        api_calls += 1
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    aoverlapDist=a_dist,
                    aoverlapTime=a_time,
                    boverlapDist=a_dist,
                    boverlapTime=a_time,
                ).model_dump(),
                api_calls,
                0
            )

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
                api_calls += 1
                entry_a, exit_a = nodes_inside_a[0], nodes_inside_a[-1]
                segments_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key, save_api_info=save_api_info)
                overlap_a_dist = segments_a.get("during_distance", 0.0)
                overlap_a_time = segments_a.get("during_time", 0.0)
            else:
                overlap_a_dist = overlap_a_time = 0.0

            if len(nodes_inside_b) >= 2:
                api_calls += 1
                entry_b, exit_b = nodes_inside_b[0], nodes_inside_b[-1]
                segments_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key, save_api_info=save_api_info)
                overlap_b_dist = segments_b.get("during_distance", 0.0)
                overlap_b_time = segments_b.get("during_time", 0.0)
            else:
                overlap_b_dist = overlap_b_time = 0.0

        return (
            SimpleDualOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=a_dist,
                aTime=a_time,
                bDist=b_dist,
                bTime=b_time,
                aoverlapDist=overlap_a_dist,
                aoverlapTime=overlap_a_time,
                boverlapDist=overlap_b_dist,
                boverlapTime=overlap_b_time,
            ).model_dump(),
            api_calls,
            0
        )
    
    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    aoverlapDist=None,
                    aoverlapTime=None,
                    boverlapDist=None,
                    boverlapTime=None,
                ).model_dump(),
                api_calls,
                1
            )
        else:
            raise

def process_routes_with_closest_nodes_simple(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    buffer_distance: float = 100.0,
    output_csv: str = "output_closest_nodes_simple.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> tuple:
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
    - save_api_info (bool): If True, saves API response.

    Returns:
    - tuple: (
        results (list): Processed result rows,
        pre_api_error_count (int): Number of errors before API calls,
        total_api_calls (int): Total number of API calls made,
        post_api_error_count (int): Number of errors during/after API calls
      )
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args_with_flags = [(row, api_key, buffer_distance, skip_invalid, save_api_info) for row in data]

    with Pool() as pool:
        results_raw = pool.map(process_row_closest_nodes_simple, args_with_flags)

    results = []
    total_api_calls = 0
    post_api_error_count = 0

    for r in results_raw:
        if r is None:
            continue
        row_result, api_calls, api_errors = r
        results.append(row_result)
        total_api_calls += api_calls
        post_api_error_count += api_errors

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results, pre_api_error_count, total_api_calls, post_api_error_count

def wrap_row_multiproc_exact(args):
    """
    Wraps a row-processing call for exact intersection calculations using buffered routes.

    This function is designed for use with multiprocessing. It unpacks the arguments and
    passes them to `process_row_exact_intersections`.

    Tracks:
    - The number of API calls made within each row.
    - Whether an error occurred during processing (used for error counts).

    Args:
        args (tuple): Contains:
            - row (dict): A dictionary representing a single CSV row.
            - api_key (str): Google Maps API key.
            - buffer_distance (float): Distance for buffer creation in meters.
            - skip_invalid (bool): If True, logs and skips rows with errors.
            - save_api_info (bool): If True, saves API response.

    Returns:
        tuple: (result_dict, api_call_count, api_error_flag)
            - result_dict (dict or None): Result of row processing.
            - api_call_count (int): Number of API calls made.
            - api_error_flag (int): 0 if successful, 1 if error occurred and skip_invalid was True.
    """
    row, api_key, buffer_distance, skip_invalid, save_api_info = args
    result, api_calls, api_errors = process_row_exact_intersections(row, api_key, buffer_distance, skip_invalid, save_api_info)
    return result, api_calls, api_errors

def process_row_exact_intersections(
    row: Dict[str, str],
    api_key: str,
    buffer_distance: float,
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> Tuple[Dict[str, Any], int, int]:
    """
    Computes precise overlapping segments between two routes using buffered polygon intersections.

    This function fetches routes, creates buffer zones, finds intersection points, and
    calculates travel metrics. It logs and tracks the number of API calls and whether
    an error was encountered during execution.

    Args:
        row (dict): Dictionary with keys "OriginA", "DestinationA", "OriginB", "DestinationB".
        api_key (str): Google Maps API key.
        buffer_distance (float): Buffer distance in meters to apply to each route.
        skip_invalid (bool): If True, logs and skips errors instead of raising them.
        save_api_info (bool): If True, saves API response.

    Returns:
        tuple: (result_dict, api_call_count, api_error_flag)
            - result_dict (dict or None): Computed metrics or None if error.
            - api_call_count (int): Number of API requests made.
            - api_error_flag (int): 0 if success, 1 if handled error.
    """
    api_calls = 0
    try:
        ID = row.get("ID", "")
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
        destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
        origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
        destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

        if origin_a == destination_a and origin_b == destination_b:
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == destination_a and origin_b != destination_b:
            api_calls += 1
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=b_dist,
                    bTime=b_time,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a != destination_a and origin_b == destination_b:
            api_calls += 1
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                    aBeforeDist=0.0,
                    aBeforeTime=0.0,
                    aAfterDist=0.0,
                    aAfterTime=0.0,
                    bBeforeDist=0.0,
                    bBeforeTime=0.0,
                    bAfterDist=0.0,
                    bAfterTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 1
        start_time_a = time.time()
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
        logging.info(f"Time to fetch route A from API: {time.time() - start_time_a:.6f} seconds")

        api_calls += 1
        start_time_b = time.time()
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
        logging.info(f"Time to fetch route B from API: {time.time() - start_time_b:.6f} seconds")

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            overlap_a = overlap_b = {"during_distance": 0.0, "during_time": 0.0, "before_distance": 0.0, "before_time": 0.0, "after_distance": 0.0, "after_time": 0.0}
        else:
            points_a = get_route_polygon_intersections(coords_a, intersection_polygon)
            points_b = get_route_polygon_intersections(coords_b, intersection_polygon)

            if len(points_a) >= 2:
                api_calls += 1
                entry_a, exit_a = points_a[0], points_a[-1]
                overlap_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key, save_api_info=save_api_info)
            else:
                overlap_a = {"during_distance": 0.0, "during_time": 0.0, "before_distance": 0.0, "before_time": 0.0, "after_distance": 0.0, "after_time": 0.0}

            if len(points_b) >= 2:
                api_calls += 1
                entry_b, exit_b = points_b[0], points_b[-1]
                overlap_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key, save_api_info=save_api_info)
            else:
                overlap_b = {"during_distance": 0.0, "during_time": 0.0, "before_distance": 0.0, "before_time": 0.0, "after_distance": 0.0, "after_time": 0.0}

        return (
            DetailedDualOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=a_dist,
                aTime=a_time,
                bDist=b_dist,
                bTime=b_time,
                aoverlapDist=overlap_a["during_distance"],
                aoverlapTime=overlap_a["during_time"],
                boverlapDist=overlap_b["during_distance"],
                boverlapTime=overlap_b["during_time"],
                aBeforeDist=overlap_a["before_distance"],
                aBeforeTime=overlap_a["before_time"],
                aAfterDist=overlap_a["after_distance"],
                aAfterTime=overlap_a["after_time"],
                bBeforeDist=overlap_b["before_distance"],
                bBeforeTime=overlap_b["before_time"],
                bAfterDist=overlap_b["after_distance"],
                bAfterTime=overlap_b["after_time"],
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                DetailedDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    aoverlapDist=None,
                    aoverlapTime=None,
                    boverlapDist=None,
                    boverlapTime=None,
                    aBeforeDist=None,
                    aBeforeTime=None,
                    aAfterDist=None,
                    aAfterTime=None,
                    bBeforeDist=None,
                    bBeforeTime=None,
                    bAfterDist=None,
                    bAfterTime=None,
                ).model_dump(),
                api_calls,
                1
            )
        else:
            raise

def process_routes_with_exact_intersections(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    buffer_distance: float = 100.0,
    output_csv: str = "output_exact_intersections.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> tuple:
    """
    Calculates travel metrics for two routes using exact geometric intersections within buffer polygons.

    It applies the processing to each row of the CSV using multiprocessing and collects:
    - The total number of API calls made across all rows.
    - The number of post-API processing errors (e.g., route failure, segment failure).

    Parameters:
        csv_file (str): Path to the input CSV file.
        api_key (str): Google API key for route data.
        buffer_distance (float): Distance for buffer zone around each route.
        output_csv (str): Output CSV file path.
        colorna, coldesta, colorib, colfestb (str): Column names in the CSV.
        skip_invalid (bool): If True, skip invalid coordinate rows and log them.
        save_api_info (bool): If True, save API response.

    Returns:
        tuple:
            - results (list): Processed result dictionaries.
            - pre_api_error_count (int): Errors before API calls (e.g., missing coordinates).
            - api_call_count (int): Total number of Google Maps API requests.
            - post_api_error_count (int): Errors during or after API processing.
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args_list = [(row, api_key, buffer_distance, skip_invalid, save_api_info) for row in data]

    with Pool() as pool:
        results_raw = pool.map(wrap_row_multiproc_exact, args_list)

    results = []
    api_call_count = 0
    post_api_error_count = 0

    for result, calls, errors in results_raw:
        results.append(result)
        api_call_count += calls
        post_api_error_count += errors

    if results:
        fieldnames = list(results[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    return results, pre_api_error_count, api_call_count, post_api_error_count

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
            - save_api_info (bool): If True, include and store raw API response data.

    Returns:
        tuple: A tuple of (result_dict, api_calls, api_errors)
    """
    row, api_key, buffer_distance, skip_invalid, save_api_info = args
    return process_row_exact_intersections_simple(
        (row, api_key, buffer_distance, save_api_info),
        skip_invalid=skip_invalid
    )

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
        tuple: A tuple of (result_dict, api_calls, api_errors)
    """
    api_calls = 0

    try:
        row, api_key, buffer_distance, save_api_info = row_and_args
        ID = row["ID"]
        origin_a, destination_a = row["OriginA"], row["DestinationA"]
        origin_b, destination_b = row["OriginB"], row["DestinationB"]

        origin_a_lat, origin_a_lon = map(float, map(str.strip, origin_a.split(",")))
        destination_a_lat, destination_a_lon = map(float, map(str.strip, destination_a.split(",")))
        origin_b_lat, origin_b_lon = map(float, map(str.strip, origin_b.split(",")))
        destination_b_lat, destination_b_lon = map(float, map(str.strip, destination_b.split(",")))

        if origin_a == destination_a and origin_b == destination_b:
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_a == destination_a:
            api_calls += 1
            coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=0.0,
                    aTime=0.0,
                    bDist=b_dist,
                    bTime=b_time,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        if origin_b == destination_b:
            api_calls += 1
            coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=0.0,
                    bTime=0.0,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        api_calls += 2
        coords_a, a_dist, a_time = get_route_data(origin_a, destination_a, api_key, save_api_info=save_api_info)
        coords_b, b_dist, b_time = get_route_data(origin_b, destination_b, api_key, save_api_info=save_api_info)

        if origin_a == origin_b and destination_a == destination_b:
            buffer_a = create_buffered_route(coords_a, buffer_distance)
            buffer_b = buffer_a
            plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=a_dist,
                    bTime=a_time,
                    aoverlapDist=a_dist,
                    aoverlapTime=a_time,
                    boverlapDist=a_dist,
                    boverlapTime=a_time,
                ).model_dump(),
                api_calls,
                0
            )

        buffer_a = create_buffered_route(coords_a, buffer_distance)
        buffer_b = create_buffered_route(coords_b, buffer_distance)
        intersection_polygon = get_buffer_intersection(buffer_a, buffer_b)

        plot_routes_and_buffers(coords_a, coords_b, buffer_a, buffer_b)

        if not intersection_polygon:
            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=a_dist,
                    aTime=a_time,
                    bDist=b_dist,
                    bTime=b_time,
                    aoverlapDist=0.0,
                    aoverlapTime=0.0,
                    boverlapDist=0.0,
                    boverlapTime=0.0,
                ).model_dump(),
                api_calls,
                0
            )

        points_a = get_route_polygon_intersections(coords_a, intersection_polygon)
        points_b = get_route_polygon_intersections(coords_b, intersection_polygon)

        if len(points_a) >= 2:
            api_calls += 1
            entry_a, exit_a = points_a[0], points_a[-1]
            segments_a = calculate_precise_travel_segments(coords_a, [entry_a, exit_a], api_key, save_api_info=save_api_info)
            overlap_a_dist = segments_a.get("during_distance", 0.0)
            overlap_a_time = segments_a.get("during_time", 0.0)
        else:
            overlap_a_dist = overlap_a_time = 0.0

        if len(points_b) >= 2:
            api_calls += 1
            entry_b, exit_b = points_b[0], points_b[-1]
            segments_b = calculate_precise_travel_segments(coords_b, [entry_b, exit_b], api_key, save_api_info=save_api_info)
            overlap_b_dist = segments_b.get("during_distance", 0.0)
            overlap_b_time = segments_b.get("during_time", 0.0)
        else:
            overlap_b_dist = overlap_b_time = 0.0

        return (
            SimpleDualOverlapResult(
                ID=ID,
                OriginAlat=origin_a_lat,
                OriginAlong=origin_a_lon,
                DestinationAlat=destination_a_lat,
                DestinationAlong=destination_a_lon,
                OriginBlat=origin_b_lat,
                OriginBlong=origin_b_lon,
                DestinationBlat=destination_b_lat,
                DestinationBlong=destination_b_lon,
                aDist=a_dist,
                aTime=a_time,
                bDist=b_dist,
                bTime=b_time,
                aoverlapDist=overlap_a_dist,
                aoverlapTime=overlap_a_time,
                boverlapDist=overlap_b_dist,
                boverlapTime=overlap_b_time,
            ).model_dump(),
            api_calls,
            0
        )

    except Exception as e:
        if skip_invalid:
            logging.error(f"Error processing row {row if 'row' in locals() else 'unknown'}: {str(e)}")
            ID = row.get("ID", "")
            origin_a_lat, origin_a_lon = safe_split(row.get("OriginA", ""))
            destination_a_lat, destination_a_lon = safe_split(row.get("DestinationA", ""))
            origin_b_lat, origin_b_lon = safe_split(row.get("OriginB", ""))
            destination_b_lat, destination_b_lon = safe_split(row.get("DestinationB", ""))

            return (
                SimpleDualOverlapResult(
                    ID=ID,
                    OriginAlat=origin_a_lat,
                    OriginAlong=origin_a_lon,
                    DestinationAlat=destination_a_lat,
                    DestinationAlong=destination_a_lon,
                    OriginBlat=origin_b_lat,
                    OriginBlong=origin_b_lon,
                    DestinationBlat=destination_b_lat,
                    DestinationBlong=destination_b_lon,
                    aDist=None,
                    aTime=None,
                    bDist=None,
                    bTime=None,
                    aoverlapDist=None,
                    aoverlapTime=None,
                    boverlapDist=None,
                    boverlapTime=None,
                ).model_dump(),
                api_calls,
                1
            )
        else:
            raise

def process_routes_with_exact_intersections_simple(
    csv_file: str,
    api_key: str,
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    buffer_distance: float = 100.0,
    output_csv: str = "output_exact_intersections_simple.csv",
    skip_invalid: bool = True,
    save_api_info: bool = False
) -> tuple:
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
    - save_api_info (bool): If True, saves API response.

    Returns:
    - tuple: (results list, pre_api_error_count, api_call_count, post_api_error_count)
    """
    data, pre_api_error_count = read_csv_file(
        csv_file=csv_file,
        home_a_lat=home_a_lat,
        home_a_lon=home_a_lon,
        work_a_lat=work_a_lat,
        work_a_lon=work_a_lon,
        home_b_lat=home_b_lat,
        home_b_lon=home_b_lon,
        work_b_lat=work_b_lat,
        work_b_lon=work_b_lon,
        id_column=id_column,
        skip_invalid=skip_invalid
    )

    args = [(row, api_key, buffer_distance, skip_invalid, save_api_info) for row in data]

    with Pool() as pool:
        results = pool.map(wrap_row_multiproc_simple, args)

    processed = []
    api_call_count = 0
    api_error_count = 0

    for result in results:
        if result is None:
            continue
        row_result, row_calls, row_errors = result
        processed.append(row_result)
        api_call_count += row_calls
        api_error_count += row_errors

    if processed:
        fieldnames = list(processed[0].keys())
        with open(output_csv, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed)

    return processed, pre_api_error_count, api_call_count, api_error_count

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
    home_a_lat: str,
    home_a_lon: str,
    work_a_lat: str,
    work_a_lon: str,
    home_b_lat: str,
    home_b_lon: str,
    work_b_lat: str,
    work_b_lon: str,
    id_column: Optional[str] = None,
    threshold: float = 50,
    width: float = 100,
    buffer: float = 100,
    approximation: str = "no",
    commuting_info: str = "no",
    output_file: str = None,
    skip_invalid: bool = True,
    save_api_info: bool = False,
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
    - home_a_lat : Column name for the latitude of home A.
    - home_a_lon : Column name for the longitude of home A.
    - work_a_lat : Column name for the latitude of work A.
    - work_a_lon : Column name for the longitude of work A.
    - home_b_lat : Column name for the latitude of home B.
    - home_b_lon : Column name for the longitude of home B.
    - work_b_lat : Column name for the latitude of work B.
    - work_b_lon : Column name for the longitude of work B.
    - id_column : Column name for the unique ID of each row. If None or not found, IDs are auto-generated as R1, R2, ...
    - threshold (float): Distance threshold for overlap (if applicable).
    - width (float): Width used for line buffering (if applicable).
    - buffer (float): Buffer radius in meters.
    - approximation (str): Mode of processing (e.g., "no", "yes", "yes with buffer", etc.).
    - commuting_info (str): Whether commuting detail is needed ("yes" or "no").
    - output_file (str): Optional custom filename for results.
    - skip_invalid (bool): If True, skips invalid coordinates and logs the error; if False, halts on error.
    - save_api_info (bool): If True, saves API response.
    - auto_confirm: bool = False： If True, skips the user confirmation prompt and proceeds automatically.

    Returns:
    - None
    """
    os.makedirs("results", exist_ok=True)

    if not api_key:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
        possible_paths = [
            os.path.join(os.getcwd(), "config.yaml"),
            os.path.join(os.path.expanduser("~"), ".canterburycommuto", "config.yaml"),
            os.path.join(base_dir, "config.yaml"),
        ]
        for config_path in possible_paths:
            print(f"[DEBUG] Checking for config.yaml in: {config_path}")
            if os.path.exists(config_path):
                break
        else:
            raise FileNotFoundError("config.yaml not found in standard locations and no API key provided.")
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                api_key = config.get("api_key")
                if not api_key:
                    raise ValueError("API key not found in config.yaml.")
        except Exception as e:
            raise RuntimeError(f"Failed to read API key from config.yaml: {e}")

    options = {
        "csv_file": csv_file,
        "api_key": "********",
        "threshold": threshold,
        "width": width,
        "buffer": buffer,
        "approximation": approximation,
        "commuting_info": commuting_info,
        "home_a_lat": str,
        "home_a_lon": str,
        "work_a_lat": str,
        "work_a_lon": str,
        "home_b_lat": str,
        "home_b_lon": str,
        "work_b_lat": str,
        "work_b_lon": str,
        "id_column": None,
        "skip_invalid": skip_invalid,
        "save_api_info": save_api_info,
    }
    if output_file:
        output_file = os.path.join("results", os.path.basename(output_file))
        if not output_file.lower().endswith(".csv"):
            output_file += ".csv"
    try:
        num_requests, estimated_cost = request_cost_estimation(
            csv_file=csv_file,
            approximation=approximation,
            commuting_info=commuting_info,
            colorna=colorna,
            coldesta=coldesta,
            colorib=colorib,
            colfestb=colfestb,
            skip_invalid=skip_invalid
        )
    except Exception as e:
        print(f"[ERROR] Unable to estimate cost: {e}")
        return

    print(f"\n[INFO] Estimated number of API requests: {num_requests}")
    print(f"[INFO] Estimated cost: ${estimated_cost:.2f}")
    print("[NOTICE] Actual cost may be higher or lower depending on Google’s pricing tiers and route pair complexity.\n")

    if not auto_confirm:
        user_input = input("Do you want to proceed with this operation? (yes/no): ").strip().lower()
        if user_input != "yes":
            print("[CANCELLED] Operation aborted by the user.")
            return
    else:
        print("[AUTO-CONFIRM] Skipping user prompt and proceeding...\n")

    print("[PROCESSING] Proceeding with route analysis...\n")

    if approximation == "yes":
        if commuting_info == "yes":
            output_file = output_file or generate_unique_filename("results/outputRec", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = overlap_rec(
                csv_file, api_key, 
                home_a_lat, home_a_lon, work_a_lat, work_a_lon, home_b_lat,
                home_b_lon, work_b_lat, work_b_lon, id_column,
                output_csv=output_file, threshold=threshold, width=width,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)
        elif commuting_info == "no":
            output_file = output_file or generate_unique_filename("results/outputRec_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = only_overlap_rec(
                csv_file, api_key, home_a_lat, home_a_lon, work_a_lat, work_a_lon, home_b_lat,
                home_b_lon, work_b_lat, work_b_lon, id_column,
                output_csv=output_file, threshold=threshold, width=width,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)

    elif approximation == "no":
        if commuting_info == "yes":
            output_file = output_file or generate_unique_filename("results/outputRoutes", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_csv(
                csv_file, api_key, home_a_lat, home_a_lon, work_a_lat, work_a_lon, home_b_lat,
                home_b_lon, work_b_lat, work_b_lon, id_column, output_csv=output_file, 
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)
        elif commuting_info == "no":
            output_file = output_file or generate_unique_filename("results/outputRoutes_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_only_overlap_with_csv(
                csv_file, api_key, home_a_lat, home_a_lon, work_a_lat, work_a_lon, home_b_lat,
                home_b_lon, work_b_lat, work_b_lon, id_column, output_csv=output_file,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)

    elif approximation == "yes with buffer":
        output_file = output_file or generate_unique_filename("results/buffer_intersection_results", ".csv")
        results, pre_api_errors, api_calls, post_api_errors = process_routes_with_buffers(
            csv_file=csv_file, api_key=api_key, 
            home_a_lat=home_a_lat, home_a_lon=home_a_lon, work_a_lat=work_a_lat, work_a_lon= work_a_lon, home_b_lat=home_b_lat,
            home_b_lon=home_b_lon, work_b_lat=work_b_lat, work_b_lon=work_b_lon, id_column=id_column, 
            output_csv=output_file, buffer_distance=buffer,
            skip_invalid=skip_invalid, save_api_info=save_api_info)
        options["Pre-API Error Count"] = pre_api_errors
        options["Post-API Error Count"] = post_api_errors
        options["Total API Calls"] = api_calls
        write_log(output_file, options)

    elif approximation == "closer to precision":
        if commuting_info == "yes":
            output_file = output_file or generate_unique_filename("results/closest_nodes_buffer_results", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_closest_nodes(
                csv_file=csv_file, api_key=api_key, 
                home_a_lat=home_a_lat, home_a_lon=home_a_lon, work_a_lat=work_a_lat, work_a_lon=work_a_lon, home_b_lat=home_b_lat,
                home_b_lon=home_b_lon, work_b_lat=work_b_lat, work_b_lon=work_b_lon, id_column=id_column, buffer_distance=buffer, output_csv=output_file,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)
        elif commuting_info == "no":
            output_file = output_file or generate_unique_filename("results/closest_nodes_buffer_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_closest_nodes_simple(
                csv_file=csv_file, api_key=api_key, 
                home_a_lat=home_a_lat, home_a_lon=home_a_lon, work_a_lat=work_a_lat, work_a_lon=work_a_lon, home_b_lat=home_b_lat,
                home_b_lon=home_b_lon, work_b_lat=work_b_lat, work_b_lon=work_b_lon, id_column=id_column, 
                buffer_distance=buffer, output_csv=output_file,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)

    elif approximation == "exact":
        if commuting_info == "yes":
            output_file = output_file or generate_unique_filename("results/exact_intersection_buffer_results", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_exact_intersections(
                csv_file=csv_file, api_key=api_key, home_a_lat=home_a_lat, home_a_lon=home_a_lon, work_a_lat=work_a_lat, work_a_lon=work_a_lon, home_b_lat=home_b_lat,
                home_b_lon=home_b_lon, work_b_lat=work_b_lat, work_b_lon=work_b_lon, id_column=id_column,
                buffer_distance=buffer, output_csv=output_file,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)
        elif commuting_info == "no":
            output_file = output_file or generate_unique_filename("results/exact_intersection_buffer_only_overlap", ".csv")
            results, pre_api_errors, api_calls, post_api_errors = process_routes_with_exact_intersections_simple(
                csv_file=csv_file, api_key=api_key, 
                home_a_lat=home_a_lat, home_a_lon=home_a_lon, work_a_lat=work_a_lat, work_a_lon=work_a_lon, home_b_lat=home_b_lat,
                home_b_lon=home_b_lon, work_b_lat=work_b_lat, work_b_lon=work_b_lon, id_column=id_column,
                buffer_distance=buffer, output_csv=output_file,
                skip_invalid=skip_invalid, save_api_info=save_api_info)
            options["Pre-API Error Count"] = pre_api_errors
            options["Post-API Error Count"] = post_api_errors
            options["Total API Calls"] = api_calls
            write_log(output_file, options)

    if save_api_info is True:
        os.makedirs("results", exist_ok=True)  # Ensure the results folder exists
        cache_path = os.path.join("results", "api_response_cache.pkl")
        with open(cache_path, "wb") as f:
            pickle.dump(api_response_cache, f)