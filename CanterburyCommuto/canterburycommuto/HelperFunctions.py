import csv
import os
import datetime
import random
from typing import Tuple, Optional

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

# Function to generate unique file names for storing the outputs and maps
def generate_unique_filename(base_name: str, extension: str = ".csv") -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    random_id = random.randint(10000, 99999)
    return f"{base_name}-{timestamp}_{random_id}{extension}"

# Function to write results to a CSV file
def write_csv_file(input_dir: str, results: list, fieldnames: list, output_file: str) -> None:
    """
    Writes the results to a CSV file inside a 'results' folder located under input_dir.

    Parameters:
    - input_dir (str): Base directory for input and output files.
    - results (list): A list of dictionaries containing the data to write.
    - fieldnames (list): A list of field names for the CSV file.
    - output_file (str): The name (not path) of the output CSV file.

    Returns:
    - None
    """

    # Ensure input_dir is an absolute path
    input_dir = os.path.abspath(input_dir)

    # Define path to the ResultsCommuto folder inside input_dir
    results_dir = os.path.join(input_dir, "ResultsCommuto")
    os.makedirs(results_dir, exist_ok=True)

    # Full output path
    output_csv_path = os.path.join(results_dir, output_file)

    with open(output_csv_path, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

def safe_split(coord: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Safely splits a coordinate string of the form "lat,lon" into two floats.

    Parameters:
    -----------
    coord : str
        A string representing a coordinate pair, formatted as "latitude,longitude".

    Returns:
    --------
    Tuple[Optional[float], Optional[float]]
        A tuple containing (latitude, longitude) as floats if parsing succeeds,
        or (None, None) if the input is invalid or cannot be converted to floats.
    """
    try:
        lat, lon = map(float, map(str.strip, coord.split(",")))
        return lat, lon
    except Exception:
        return None, None
    
