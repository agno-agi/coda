"""CLI entry point: python -m evals"""

import argparse

from evals import CATEGORIES
from evals.run import run_evals

parser = argparse.ArgumentParser(description="Run Coda evals")
parser.add_argument("--category", type=str, choices=list(CATEGORIES.keys()), help="Run a single category")
parser.add_argument("--verbose", action="store_true", help="Show response previews and failure reasons")
args = parser.parse_args()
run_evals(category=args.category, verbose=args.verbose)
