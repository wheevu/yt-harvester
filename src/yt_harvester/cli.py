import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a single discussion pack from one YouTube video URL or ID.",
    )
    parser.add_argument("input", help="YouTube video URL or 11-character video ID")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Optional output .txt path (default: output/<title> [<id>].txt).",
    )

    return parser.parse_args()
