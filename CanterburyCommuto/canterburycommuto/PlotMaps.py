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

