import time
import logging
import os
from typing import List, Tuple

import folium
from IPython.display import display, IFrame
from shapely.geometry import Polygon, mapping

from canterburycommuto.HelperFunctions import generate_unique_filename

# Function to save the maps
def save_map(map_object, base_name: str, ID: str, input_dir: str) -> str:
    """
    Saves a map object to an HTML file in a 'results' folder inside the input directory.

    Args:
        map_object: The map object to save (e.g., a folium.Map).
        base_name (str): The base name for the output file.
        ID (str): The unique identifier to append to the filename.
        input_dir (str): The directory where the input CSV is located.

    Returns:
        str: The full path to the saved HTML file.
    """
    output_dir = os.path.join(input_dir, "ResultsCommuto")
    os.makedirs(output_dir, exist_ok=True)
    filename = generate_unique_filename(os.path.join(output_dir, f"{base_name}_{ID}"), ".html")
    map_object.save(filename)
    print(f"Map saved to: {os.path.abspath(filename)}")
    return filename

# Function to plot routes to display on maps
def plot_routes(
    coordinates_a: list, coordinates_b: list, first_common: tuple, last_common: tuple, ID: str, input_dir: str
) -> None:
    """
    Plots routes A and B with common nodes highlighted over an OpenStreetMap background.

    Parameters:
    - coordinates_a (list): A list of (latitude, longitude) tuples for route A.
    - coordinates_b (list): A list of (latitude, longitude) tuples for route B.
    - first_common (tuple): The first common node (latitude, longitude).
    - last_common (tuple): The last common node (latitude, longitude).
    - ID (str): The unique identifier to append to the filename.
    - input_dir (str): The directory where the input CSV is located.

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
            html="""
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
            html="""
            <div style="font-size: 16px; color: green; transform: scale(1.4);">
                <i class='fa fa-star'></i>
            </div>
            """
        ),
        tooltip="Destination B",
    ).add_to(map_osm)

    # Save the map using the save_map function
    map_filename = save_map(map_osm, "routes_map", ID, input_dir)

    # Display the map inline (only for Jupyter Notebooks)
    try:
        display(IFrame(map_filename, width="100%", height="500px"))
    except NameError:
        print(f"Map saved as '{map_filename}'. Open it in a browser.")

# Another type of map with buffered routes.
def plot_routes_and_buffers(
    route_a_coords: List[Tuple[float, float]],
    route_b_coords: List[Tuple[float, float]],
    buffer_a: Polygon,
    buffer_b: Polygon,
    ID: str,
    input_dir: str
) -> None:
    """
    Plot two routes and their respective buffers over an OpenStreetMap background and display it inline.

    Args:
        route_a_coords (List[Tuple[float, float]]): Route A coordinates (latitude, longitude).
        route_b_coords (List[Tuple[float, float]]): Route B coordinates (latitude, longitude).
        buffer_a (Polygon): Buffered polygon for Route A.
        buffer_b (Polygon): Buffered polygon for Route B.
        ID (str): Unique identifier to append to the filename.
        input_dir (str): Directory where the input CSV is located.

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
    map_filename = save_map(map_osm, "routes_with_buffers_map", ID, input_dir)

    # Display the map inline
    display(IFrame(map_filename, width="100%", height="600px"))
    print(f"Map has been displayed inline and saved as '{map_filename}'.")
    print(f"Map has been displayed inline and saved as '{map_filename}'.")

