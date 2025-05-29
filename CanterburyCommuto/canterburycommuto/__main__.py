"""
CanterburyCommuto CLI: Command-Line Interface for Route Overlap Analysis and Cost Estimation.

This script provides a command-line interface to:
- Analyze route overlaps and buffer intersections
- Estimate the number of Google API requests and the corresponding cost

Usage:

    # Run overlap and buffer analysis:
    python -m your_project.main overlap <csv_file> <api_key>
        [--threshold VALUE] [--width VALUE] [--buffer VALUE]
        [--approximation VALUE] [--commuting_info VALUE]
        [--colorna COLUMN_NAME] [--coldesta COLUMN_NAME]
        [--colorib COLUMN_NAME] [--colfestb COLUMN_NAME]
        [--output_overlap FILENAME] [--output_buffer FILENAME]
        [--skip_invalid True|False] [--save_api_info] [--yes]

    # Estimate number of API requests and cost (no actual API calls):
    python -m your_project.main estimate <csv_file>
        [--approximation VALUE] [--commuting_info VALUE]
        [--colorna COLUMN_NAME] [--coldesta COLUMN_NAME]
        [--colorib COLUMN_NAME] [--colfestb COLUMN_NAME]
        [--output_overlap FILENAME] [--output_buffer FILENAME]
        [--skip_invalid True|False]
"""

import argparse
from canterburycommuto.CanterburyCommuto import Overlap_Function, request_cost_estimation

def run_overlap(args):
    try:
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
            save_api_info=args.save_api_info,
            auto_confirm=args.yes
        )
    except ValueError as ve:
        print(f"Input Validation Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def run_estimation(args):
    try:
        n_requests, cost = request_cost_estimation(
            csv_file=args.csv_file,
            approximation=args.approximation,
            commuting_info=args.commuting_info,
            colorna=args.colorna,
            coldesta=args.coldesta,
            colorib=args.colorib,
            colfestb=args.colfestb,
            output_overlap=args.output_overlap,
            output_buffer=args.output_buffer,
            skip_invalid=args.skip_invalid
        )
        print(f"Estimated API requests: {n_requests}")
        print(f"Estimated cost (USD): ${cost:.2f}")
    except Exception as e:
        print(f"Error during estimation: {e}")

def main():
    parser = argparse.ArgumentParser(description="CanterburyCommuto CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for "overlap"
    overlap_parser = subparsers.add_parser("overlap", help="Analyze route overlaps and buffers.")
    overlap_parser.add_argument("csv_file", type=str)
    overlap_parser.add_argument("--api_key", type=str, required=False, default=None, help="Google API key. If not provided, the tool will try to read from config.yaml.")
    overlap_parser.add_argument("--threshold", type=float, default=50.0)
    overlap_parser.add_argument("--width", type=float, default=100.0)
    overlap_parser.add_argument("--buffer", type=float, default=100.0)
    overlap_parser.add_argument("--approximation", type=str, choices=["yes", "no", "yes with buffer", "closer to precision", "exact"], default="no")
    overlap_parser.add_argument("--commuting_info", type=str, choices=["yes", "no"], default="no")
    overlap_parser.add_argument("--colorna", type=str)
    overlap_parser.add_argument("--coldesta", type=str)
    overlap_parser.add_argument("--colorib", type=str)
    overlap_parser.add_argument("--colfestb", type=str)
    overlap_parser.add_argument("--output_overlap", type=str)
    overlap_parser.add_argument("--output_buffer", type=str)
    overlap_parser.add_argument("--skip_invalid", type=lambda x: x == "True", choices=[True, False], default=True)
    overlap_parser.add_argument("--save_api_info", action="store_true", help="If set, saves API responses to a pickle file (api_response_cache.pkl)")
    overlap_parser.add_argument("--yes", action="store_true")
    overlap_parser.set_defaults(func=run_overlap)

    # Subparser for "estimate"
    estimate_parser = subparsers.add_parser("estimate", help="Estimate number of API requests and cost.")
    estimate_parser.add_argument("csv_file", type=str)
    estimate_parser.add_argument("--approximation", type=str, choices=["yes", "no", "yes with buffer", "closer to precision", "exact"], default="no")
    estimate_parser.add_argument("--commuting_info", type=str, choices=["yes", "no"], default="no")
    estimate_parser.add_argument("--colorna", type=str)
    estimate_parser.add_argument("--coldesta", type=str)
    estimate_parser.add_argument("--colorib", type=str)
    estimate_parser.add_argument("--colfestb", type=str)
    estimate_parser.add_argument("--output_overlap", type=str)
    estimate_parser.add_argument("--output_buffer", type=str)
    estimate_parser.add_argument("--skip_invalid", type=lambda x: x == "True", choices=[True, False], default=True)
    estimate_parser.set_defaults(func=run_estimation)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
