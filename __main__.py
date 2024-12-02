"""
Marco Polo CLI: Command-Line Interface for Route Overlap Analysis

This script serves as the entry point for the Marco Polo package, providing a
command-line interface to process routes and analyze overlaps.

Usage:
    python -m Marco_Polo <csv_file> <api_key> [--width_ratio VALUE] [--threshold VALUE]

Arguments:
    csv_file: Path to the input CSV file containing route data.
    api_key: Google API key for route calculations.

Optional Arguments:
    --width_ratio: Width ratio parameter for overlap approximation (default: 0.5).
    --threshold: Threshold for determining overlapping nodes (default: 0.05).
"""

import argparse
from Marco_Polo import Overlap_Function

def main() -> None:
    """
    CLI entry point for the Marco Polo package.
    Parses command-line arguments and invokes the `Overlap_Function`.
    """
    parser = argparse.ArgumentParser(
        description="CLI for the Marco Polo tool to analyze route overlaps."
    )
    parser.add_argument(
        "csv_file", type=str, help="Path to the input CSV file."
    )  # csv_file must be a string path
    parser.add_argument(
        "api_key", type=str, help="Google API key for processing routes."
    )  # api_key must be a string
    parser.add_argument(
        "--width_ratio", 
        type=float, 
        default=0.5, 
        help="Width ratio parameter for overlap approximation (default: 0.5)."
    )  # width_ratio must be a float
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=0.05, 
        help="Threshold for determining overlapping nodes (default: 0.05)."
    )  # threshold must be a float

    args = parser.parse_args()

    # Passing arguments to Overlap_Function
    try:
        Overlap_Function(
            csv_file=args.csv_file,
            api_key=args.api_key,
            width_ratio=args.width_ratio,
            threshold=args.threshold,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

