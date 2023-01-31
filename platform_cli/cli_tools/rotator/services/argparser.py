import argparse

from platform_cli.libs.others import LOG_LEVEL


def get_args():
    example_text = """
    pl-cli --tool rotator --context $ctx -l 'node.kubernetes.io/owner=project' -v INFO
    """

    parser = argparse.ArgumentParser(
        description="CLI for rotate kubernetes worker nodes",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--context", help="Arg=(kubernetes context)")
    parser.add_argument("-l", "--selector", help="Arg=(Selector (label query) for nodes)")
    parser.add_argument("-m", "--mode", help="Arg=()", choices=["chunks", "manual", "cordon", "uncordon"], default="chunks")
    parser.add_argument("--sleep", help="Arg=(Pause between mode=<chunks> drains in seconds)", type=int, default=90)
    parser.add_argument("--ratio", help="Arg=(How much need to wait between chunks drains?)", type=float, default=0.1)
    # logs
    parser.add_argument(
        "-v",
        "--verbose",
        help="Arg=(Logging Level)",
        # default="ERROR",
        default="INFO",
        choices=list(LOG_LEVEL.keys()),
    )

    args, _ = parser.parse_known_args()

    return args
