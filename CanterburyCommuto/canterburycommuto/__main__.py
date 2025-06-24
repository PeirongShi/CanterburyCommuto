"""
CanterburyCommuto CLI: Command-Line Interface for Route Overlap Analysis and Cost Estimation.

This script provides a command-line interface to:
- Analyze route overlaps and buffer intersections
- Estimate the number of Google API requests and the corresponding cost

Usage:

    # Run overlap and buffer analysis:
    python -m canterburycommuto.main overlap
        [--csv_file PATH] [--api_key KEY]
        [--threshold VALUE] [--width VALUE] [--buffer VALUE]
        [--approximation VALUE] [--commuting_info VALUE]
        [--home_a_lat COLUMN_NAME] [--home_a_lon COLUMN_NAME]
        [--work_a_lat COLUMN_NAME] [--work_a_lon COLUMN_NAME]
        [--home_b_lat COLUMN_NAME] [--home_b_lon COLUMN_NAME]
        [--work_b_lat COLUMN_NAME] [--work_b_lon COLUMN_NAME]
        [--id_column COLUMN_NAME]
        [--output_file FILENAME]
        [--skip_invalid True|False] [--save_api_info] [--yes]

    # Estimate number of API requests and cost (no actual API calls):
    python -m canterburycommuto.main estimate
        [--csv_file PATH]
        [--approximation VALUE] [--commuting_info VALUE]
        [--home_a_lat COLUMN_NAME] [--home_a_lon COLUMN_NAME]
        [--work_a_lat COLUMN_NAME] [--work_a_lon COLUMN_NAME]
        [--home_b_lat COLUMN_NAME] [--home_b_lon COLUMN_NAME]
        [--work_b_lat COLUMN_NAME] [--work_b_lon COLUMN_NAME]
        [--id_column COLUMN_NAME]
        [--skip_invalid True|False]

Notes:
- All arguments are optional. If not provided, values will be loaded from config.yaml (if present) or use function defaults.
- Do not provide empty strings as argument values; omit the flag to use config or default.
"""

import argparse
import os
import yaml
from canterburycommuto.CanterburyCommuto import Overlap_Function, request_cost_estimation

def run_overlap(args):
    try:
        Overlap_Function(
            csv_file=args.csv_file,
            input_dir=args.input_dir,
            api_key=args.api_key,
            threshold=args.threshold,
            width=args.width,
            buffer=args.buffer,
            approximation=args.approximation,
            commuting_info=args.commuting_info,
            home_a_lat=args.home_a_lat,
            home_a_lon=args.home_a_lon,
            work_a_lat=args.work_a_lat,
            work_a_lon=args.work_a_lon,
            home_b_lat=args.home_b_lat,
            home_b_lon=args.home_b_lon,
            work_b_lat=args.work_b_lat,
            work_b_lon=args.work_b_lon,
            id_column=args.id_column,
            output_file=args.output_file,
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
            input_dir=args.input_dir,
            home_a_lat=args.home_a_lat,
            home_a_lon=args.home_a_lon,
            work_a_lat=args.work_a_lat,
            work_a_lon=args.work_a_lon,
            home_b_lat=args.home_b_lat,
            home_b_lon=args.home_b_lon,
            work_b_lat=args.work_b_lat,
            work_b_lon=args.work_b_lon,
            id_column=args.id_column,
            approximation=args.approximation,
            commuting_info=args.commuting_info,
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
    overlap_parser.add_argument("--csv_file", type=str, required=False, help="Path to the input CSV file.")
    overlap_parser.add_argument("--input_dir", type=str, required=False, help="Directory where the input CSV file is located.")
    overlap_parser.add_argument("--api_key", type=str, required=False, default=None, help="Google API key. If not provided, the tool will try to read from config.yaml.")
    overlap_parser.add_argument("--threshold", type=float, default=50.0)
    overlap_parser.add_argument("--width", type=float, default=100.0)
    overlap_parser.add_argument("--buffer", type=float, default=100.0)
    overlap_parser.add_argument("--approximation", type=str, choices=["yes", "no", "yes with buffer", "closer to precision", "exact"], default="no")
    overlap_parser.add_argument("--commuting_info", type=str, choices=["yes", "no"], default="no")
    overlap_parser.add_argument("--home_a_lat", type=str)
    overlap_parser.add_argument("--home_a_lon", type=str)
    overlap_parser.add_argument("--work_a_lat", type=str)
    overlap_parser.add_argument("--work_a_lon", type=str)
    overlap_parser.add_argument("--home_b_lat", type=str)
    overlap_parser.add_argument("--home_b_lon", type=str)
    overlap_parser.add_argument("--work_b_lat", type=str)
    overlap_parser.add_argument("--work_b_lon", type=str)
    overlap_parser.add_argument("--id_column", type=str)
    overlap_parser.add_argument("--output_file", type=str)
    overlap_parser.add_argument("--skip_invalid", type=lambda x: x == "True", choices=[True, False], default=True)
    overlap_parser.add_argument("--save_api_info", action="store_true", help="If set, saves API responses to a pickle file (api_response_cache.pkl)")
    overlap_parser.add_argument("--yes", action="store_true")
    overlap_parser.set_defaults(func=run_overlap)

    # Subparser for "estimate"
    estimate_parser = subparsers.add_parser("estimate", help="Estimate number of API requests and cost.")
    estimate_parser.add_argument("--csv_file", type=str, required=False, help="Path to the input CSV file.")
    estimate_parser.add_argument("--input_dir", type=str, required=False, help="Directory where the input CSV file is located.")
    estimate_parser.add_argument("--approximation", type=str, choices=["yes", "no", "yes with buffer", "closer to precision", "exact"], default="no")
    estimate_parser.add_argument("--commuting_info", type=str, choices=["yes", "no"], default="no")
    estimate_parser.add_argument("--home_a_lat", type=str)
    estimate_parser.add_argument("--home_a_lon", type=str)
    estimate_parser.add_argument("--work_a_lat", type=str)
    estimate_parser.add_argument("--work_a_lon", type=str)
    estimate_parser.add_argument("--home_b_lat", type=str)
    estimate_parser.add_argument("--home_b_lon", type=str)
    estimate_parser.add_argument("--work_b_lat", type=str)
    estimate_parser.add_argument("--work_b_lon", type=str)
    estimate_parser.add_argument("--id_column", type=str)
    estimate_parser.add_argument("--skip_invalid", type=lambda x: x == "True", choices=[True, False], default=True)
    estimate_parser.set_defaults(func=run_estimation)

    args = parser.parse_args()

    # --- Begin config loading logic ---
    def load_config():
        possible_paths = [
            os.path.join(os.getcwd(), "config.yaml"),
            os.path.join(os.path.expanduser("~"), ".canterburycommuto", "config.yaml"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"),
        ]
        for config_path in possible_paths:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    return yaml.safe_load(f)
        return {}

    config = load_config()

    # For each argument, if not set by user (None or argparse default), use config value if present
    for key in vars(args):
        # Skip internal argparse attributes
        if key not in config:
            continue
        val = getattr(args, key)
        # For booleans, argparse sets False if not present, so only override if None
        if val is None or (isinstance(val, str) and val == ""):
            setattr(args, key, config[key])
        # Special handling for store_true flags (like save_api_info, yes)
        if isinstance(val, bool) and val is False and isinstance(config[key], bool) and config[key] is True:
            setattr(args, key, True)
    # --- End config loading logic ---

    args.func(args)

if __name__ == "__main__":
    main()