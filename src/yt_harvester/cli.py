import argparse
from .config import DEFAULT_CONFIG

def parse_args():
    parser = argparse.ArgumentParser(
        description="Harvest transcript and comments from a YouTube video or process multiple videos from a file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single video processing:
  yt-harvester https://www.youtube.com/watch?v=dQw4w9WgXcQ
  yt-harvester dQw4w9WgXcQ -c 10 -f json
  
  # Bulk processing:
  yt-harvester --bulk links.txt
  yt-harvester --bulk links.txt -f json --bulk-output-dir ./outputs
        """
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="The URL or Video ID of the YouTube video (not used with --bulk)"
    )
    parser.add_argument(
        "-c", "--comments",
        type=int,
        default=DEFAULT_CONFIG["comments"]["top_n"],
        metavar="N",
        help=f"Number of top-level comments to fetch. Default: {DEFAULT_CONFIG['comments']['top_n']}"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["txt", "json"],
        default=DEFAULT_CONFIG["output"]["format"],
        help=f"Output format. Default: {DEFAULT_CONFIG['output']['format']}"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=DEFAULT_CONFIG["comments"]["max_download"],
        metavar="N",
        help=f"Maximum total comments to download. Default: {DEFAULT_CONFIG['comments']['max_download']}"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Specify an output file name."
    )
    parser.add_argument(
        "--bulk",
        metavar="FILE",
        help="Process multiple videos from a file."
    )
    parser.add_argument(
        "--bulk-output-dir",
        metavar="DIR",
        help="Directory to save outputs when using --bulk mode."
    )
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Disable sentiment analysis."
    )
    parser.add_argument(
        "--no-keywords",
        action="store_true",
        help="Disable keyword extraction."
    )
    
    return parser.parse_args()
