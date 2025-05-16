"""
CanterburyCommuto CLI: Command-Line Interface for Route Overlap Analysis and Buffer Intersection.

This script provides a command-line interface to process routes, analyze overlaps,
and compare outputs.

Usage:
    python -m your_project.main <csv_file> <api_key> [--threshold VALUE] [--width VALUE]
        [--buffer VALUE] [--approximation VALUE] [--commuting_info VALUE]
        [--colorna COLUMN_NAME] [--coldesta COLUMN_NAME] [--colorib COLUMN_NAME]
        [--colfestb COLUMN_NAME] [--output_overlap FILENAME] [--output_buffer FILENAME]
        [--skip_invalid True|False] [--yes]
"""

import argparse
from canterburycommuto.CanterburyCommuto import Overlap_Function

def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(
        description="CLI for analyzing route overlaps and buffer intersections."
    )

    # Required arguments
    parser.add_argument("csv_file", type=str, help="Path to the input CSV file containing route data.")
    parser.add_argument("api_key", type=str, help="Google API key for route calculations.")

    # Optional arguments
    parser.add_argument("--threshold", type=float, default=50.0, help="Overlap threshold percentage for node overlap calculations (default: 50).")
    parser.add_argument("--width", type=float, default=100.0, help="Width for node overlap calculations in meters (default: 100).")
    parser.add_argument("--buffer", type=float, default=100.0, help="Buffer distance for route buffer intersection analysis in meters (default: 100).")
    parser.add_argument("--approximation", type=str, choices=["yes", "no", "yes with buffer", "closer to precision", "exact"], default="no", help="Overlap processing method: 'yes', 'no', 'yes with buffer', 'closer to precision', or 'exact'. (default: no).")
    parser.add_argument("--commuting_info", type=str, choices=["yes", "no"], default="no", help="Include commuting information: 'yes' or 'no' (default: no).")
    parser.add_argument("--colorna", type=str, help="Column name for the origin of route A.")
    parser.add_argument("--coldesta", type=str, help="Column name for the destination of route A.")
    parser.add_argument("--colorib", type=str, help="Column name for the origin of route B.")
    parser.add_argument("--colfestb", type=str, help="Column name for the destination of route B.")
    parser.add_argument("--output_overlap", type=str, help="Path to save the overlap results (optional).")
    parser.add_argument("--output_buffer", type=str, help="Path to save the buffer intersection results (optional).")
    parser.add_argument("--skip_invalid", type=lambda x: x == "True", choices=[True, False], default=True, help="Whether to skip invalid coordinate rows (True or False). Default is True.")

    # NEW: Add --yes flag to skip confirmation prompt
    parser.add_argument("--yes", action="store_true", help="Automatically confirm the cost prompt and proceed without asking.")

    args = parser.parse_args()

    try:
        # Call the Overlap_Function with parsed arguments
        Overlap_Function(
            csv_file=args.csv_file,
            api_key=args.api_key,
            threshold=args.threshold,
            width=args.width,
            buffer=args.buffer,
            approximation=args.approximation,
            commuting_info=args.commuting_info,
            colorna=args.colorna,
            coldesta=args.coldesta,
            colorib=args.colorib,
            colfestb=args.colfestb,
            output_overlap=args.output_overlap,
            output_buffer=args.output_buffer,
            skip_invalid=args.skip_invalid,
            auto_confirm=args.yes  # NEW: pass the flag to control prompt
        )
    except ValueError as ve:
        print(f"Input Validation Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
