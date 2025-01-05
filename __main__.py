"""
CanterburyCommuto CLI: Command-Line Interface for Route Overlap Analysis and Buffer Intersection

This script serves as the main entry point for the CanterburyCommuto package, providing a
command-line interface to process routes, analyze overlaps, and compare outputs.

Usage:
    python -m CanterburyCommuto <csv_file> <api_key> [--threshold VALUE] [--width VALUE] [--buffer VALUE]

Arguments:
    csv_file: Path to the input CSV file containing route data.
    api_key: Google API key for route calculations.

Optional Arguments:
    --threshold: Overlap threshold percentage for node overlap calculations (default: 50).
    --width: Width for node overlap calculations in meters (default: 100).
    --buffer: Buffer distance for route buffer intersection analysis in meters (default: 100).
"""

import argparse

from .CanterburyCommuto import Overlap_Function


def main() -> None:
    """
    CLI entry point for the CanterburyCommuto package.
    Parses command-line arguments and invokes the `Overlap_Function`.
    """
    parser = argparse.ArgumentParser(
        description="CLI for CanterburyCommuto to analyze route overlaps and buffer intersections."
    )
    parser.add_argument(
        "csv_file", type=str, help="Path to the input CSV file containing route data."
    )
    parser.add_argument(
        "api_key", type=str, help="Google API key for route calculations."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Overlap threshold percentage for node overlap calculations (default: 50).",
    )
    parser.add_argument(
        "--width",
        type=float,
        default=100.0,
        help="Width for node overlap calculations in meters (default: 100).",
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=100.0,
        help="Buffer distance for route buffer intersection analysis in meters (default: 100).",
    )

    args = parser.parse_args()

    # Invoke the Overlap_Function with parsed arguments
    try:
        Overlap_Function(
            csv_file=args.csv_file,
            api_key=args.api_key,
            threshold=args.threshold,
            width=args.width,
            buffer=args.buffer,
        )
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
