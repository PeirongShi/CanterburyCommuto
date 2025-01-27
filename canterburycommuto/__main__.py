"""
CanterburyCommuto CLI: Command-Line Interface for Route Overlap Analysis and Buffer Intersection.

This script serves as the main entry point for the CanterburyCommuto package, providing a
command-line interface to process routes, analyze overlaps, and compare outputs.

Usage:
    python -m your_project.main <csv_file> <api_key> [--threshold VALUE] [--width VALUE] [--buffer VALUE] 
        [--approximation] [--colorna COLUMN_NAME] [--coldesta COLUMN_NAME] [--colorib COLUMN_NAME] 
        [--colfestb COLUMN_NAME]

Arguments:
    csv_file: Path to the input CSV file containing route data.
    api_key: Google API key for route calculations.

Optional Arguments:
    --threshold: Overlap threshold percentage for node overlap calculations (default: 50).
    --width: Width for node overlap calculations in meters (default: 100).
    --buffer: Buffer distance for route buffer intersection analysis in meters (default: 100).
    --approximation: Enable approximation for overlapping nodes (default: disabled).
    --colorna: Column name for the origin of route A.
    --coldesta: Column name for the destination of route A.
    --colorib: Column name for the origin of route B.
    --colfestb: Column name for the destination of route B.
"""

import argparse
import os
import re
import csv
from .CanterburyCommuto import Overlap_Function


def validate_csv_file(csv_file: str) -> None:
    """
    Validates if the provided CSV file exists, is readable, and contains at least 4 columns.

    Args:
        csv_file (str): The path to the CSV file.

    Raises:
        ValueError: If the file does not exist, is not a valid CSV file, or has fewer than 4 columns.
    """
    # Check if the file exists
    if not os.path.exists(csv_file):
        raise ValueError(f"The CSV file '{csv_file}' does not exist.")

    # Check if the file has a valid CSV extension
    if not csv_file.lower().endswith('.csv'):
        raise ValueError(f"The file '{csv_file}' is not a valid CSV file.")
    
    # Check if the file has at least 4 columns
    try:
        with open(csv_file, mode='r') as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Read the first row (header)
            if header is None or len(header) < 4:
                raise ValueError(f"The CSV file '{csv_file}' must contain at least 4 columns.")
    except Exception as e:
        raise ValueError(f"Error reading the CSV file '{csv_file}': {e}")


def validate_api_key(api_key: str) -> None:
    """
    Validates if the provided API key has a correct format (basic check).

    Args:
        api_key (str): The API key.

    Raises:
        ValueError: If the API key format does not match the expected pattern.
    """
    # A basic check for API key format (adjust regex based on your specific API provider)
    if not re.match(r"^[A-Za-z0-9_-]{35,}$", api_key):
        raise ValueError("The provided API key does not have the correct format.")


def main() -> None:
    """
    CLI entry point for the CanterburyCommuto package.
    Parses command-line arguments, validates inputs, and invokes the `Overlap_Function`.
    """
    parser = argparse.ArgumentParser(
        description="CLI for CanterburyCommuto to analyze route overlaps and buffer intersections."
    )
    parser.add_argument(
        "csv_file", 
        type=str, 
        help="Path to the input CSV file containing route data."
    )
    parser.add_argument(
        "api_key", 
        type=str, 
        help="Google API key for route calculations."
    )
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=50.0, 
        help="Overlap threshold percentage for node overlap calculations (default: 50)."
    )
    parser.add_argument(
        "--width", 
        type=float, 
        default=100.0, 
        help="Width for node overlap calculations in meters (default: 100)."
    )
    parser.add_argument(
        "--buffer", 
        type=float, 
        default=100.0, 
        help="Buffer distance for route buffer intersection analysis in meters (default: 100)."
    )
    parser.add_argument(
        "--approximation", 
        action="store_true", 
        help="Enable approximation for overlapping nodes (default: disabled)."
    )
    parser.add_argument(
        "--colorna", 
        type=str, 
        help="Column name for the origin of route A."
    )
    parser.add_argument(
        "--coldesta", 
        type=str, 
        help="Column name for the destination of route A."
    )
    parser.add_argument(
        "--colorib", 
        type=str, 
        help="Column name for the origin of route B."
    )
    parser.add_argument(
        "--colfestb", 
        type=str, 
        help="Column name for the destination of route B."
    )

    args = parser.parse_args()

    try:
        # Validate inputs
        validate_csv_file(args.csv_file)
        validate_api_key(args.api_key)

        # Invoke the Overlap_Function with validated arguments
        Overlap_Function(
            csv_file=args.csv_file,
            api_key=args.api_key,
            threshold=args.threshold,
            width=args.width,
            buffer=args.buffer,
            approximation=args.approximation,
            colorna=args.colorna,
            coldesta=args.coldesta,
            colorib=args.colorib,
            colfestb=args.colfestb
        )
    except ValueError as ve:
        print(f"Input Validation Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
