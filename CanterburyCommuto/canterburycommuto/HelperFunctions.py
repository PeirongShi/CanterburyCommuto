import csv
import time
import datetime
import logging
import math
import os
import pickle
import random
from typing import Dict, List, Tuple, Optional, Any
from multiprocessing.dummy import Pool

import folium
import polyline
import requests
import yaml
from IPython.display import display, IFrame
from pyproj import Geod, Transformer
from pydantic import BaseModel
from shapely.geometry import LineString, Polygon, mapping, MultiLineString, Point, GeometryCollection, MultiPoint

# Function to generate unique file names for storing the outputs and maps
def generate_unique_filename(base_name: str, extension: str = ".csv") -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    random_id = random.randint(10000, 99999)
    return f"{base_name}-{timestamp}_{random_id}{extension}"

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