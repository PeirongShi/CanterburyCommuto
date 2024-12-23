"""
Marco Polo CLI: Command-Line Interface for Route Overlap Analysis

This script serves as the entry point for the Marco Polo package, providing a
command-line interface to process routes and analyze overlaps.

Usage:
    python -m Marco_Polo <csv_file> <api_key> [--width VALUE] [--threshold VALUE]

Arguments:
    csv_file: Path to the input CSV file containing route data.
    api_key: Google API key for route calculations.

Optional Arguments:
    --width: Width (in meters) for creating rectangles around route segments (default: 100).
    --threshold: Threshold for determining overlapping nodes (default: 50.0).
"""

import argparse
from Marco_Polo import Overlap_Function

def main() -> None:
    """
    CLI entry point for the Marco Polo package.
    Parses command-line arguments and invokes the `Overlap_Function`.

    Args:
        None

    Command-line Arguments:
        csv_file (str): Path to the input CSV file.
        api_key (str): Google API key for processing routes.
        --width (int): Width in meters for creating rectangles (default: 100).
        --threshold (float): Overlap threshold as a percentage (default: 50.0).
    """
    parser = argparse.ArgumentParser(
        description="CLI for the Marco Polo tool to analyze route overlaps."
    )
    parser.add_argument(
        "csv_file", 
        type=str, 
        help="Path to the input CSV file containing route data."
    )
    parser.add_argument(
        "api_key", 
        type=str, 
        help="Google API key for processing routes and fetching distances."
    )
    parser.add_argument(
        "--width", 
        type=int, 
        default=100, 
        help="Width (in meters) for overlap approximation (default: 100)."
    )
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=50.0, 
        help="Threshold percentage for overlap approximation (default: 50.0)."
    )

    args = parser.parse_args()

    # Passing arguments to Overlap_Function
    try:
        Overlap_Function(
            csv_file=args.csv_file,
            api_key=args.api_key,
            threshold=args.threshold,
            width=args.width
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
