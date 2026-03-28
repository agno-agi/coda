"""CLI entry point: python -m coda"""

from coda.team import coda

if __name__ == "__main__":
    coda.cli_app(stream=True)
