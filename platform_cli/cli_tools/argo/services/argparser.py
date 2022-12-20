"""
TODO: multilevel argparse:
https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
https://mike.depalatis.net/blog/simplifying-argparse.html
"""

import argparse
import json

from platform_cli.libs.others import LOG_LEVEL


def get_args():
    example_text = """
    pl-cli --tool argo --context $ctx --no-sync --sync-app ${app}
    pl-cli --tool argo --context $ctx --sync --sync-app ${root-app}
    """

    parser = argparse.ArgumentParser(
        description="CLI for enable / disable AutoSync on ArgoCD Applications",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--context", help="Arg=(kubernetes context)")
    parser.add_argument("-n", "--namespace", help="Arg=(kubernetes namespace)", default="argocd")
    # argo
    parser.add_argument(
        "--sync",
        help="Arg=(Enable AutoSync for sync-app)",
        action="store_true",
    )
    parser.add_argument(
        "--no-sync",
        help="Arg=(Disable AutoSync for sync-app)",
        action="store_false",
    )
    parser.add_argument(
        "--sync-app",
        help="Arg=(Enable AutoSync for app)",
        default="cluster-init",
    )

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
