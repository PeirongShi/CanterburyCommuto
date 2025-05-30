import time
import logging
import math
from typing import Dict, List, Tuple

from pyproj import Geod, Transformer
from shapely.geometry import LineString, Polygon, Point, MultiPoint

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

#The following functions are used for finding approximations around the first and last common node. The approximation is probably more relevant when two routes crosses each other. The code can still be improved.
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

# The following functions create buffers along the commuting routes to find the ratios of buffers' intersection area over the two routes' total buffer areas.
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

def calculate_precise_travel_segments(
    route_coords: List[List[float]],
    intersections: List[List[float]],
    api_key: str,
    save_api_info: bool = False
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
                api_key,
                save_api_info=save_api_info
            )
            after_data = get_route_data(
                f"{start[0]},{start[1]}",
                f"{route_coords[-1][0]},{route_coords[-1][1]}",
                api_key,
                save_api_info=save_api_info
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
        api_key,
        save_api_info=save_api_info
    )
    during_data = get_route_data(
        f"{start[0]},{start[1]}",
        f"{end[0]},{end[1]}",
        api_key,
        save_api_info=save_api_info
    )
    after_data = get_route_data(
        f"{end[0]},{end[1]}",
        f"{route_coords[-1][0]},{route_coords[-1][1]}",
        api_key,
        save_api_info=save_api_info
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
    


