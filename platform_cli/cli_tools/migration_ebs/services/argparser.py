import argparse
import json

from platform_cli.libs.others import LOG_LEVEL


def get_args():
    example_text = """
    pl-cli --tool migration-ebs --context $ctx -n $ns --pvc $pvc -v INF
    """

    parser = argparse.ArgumentParser(
        description="CLI for migrate kubernetes stateful application data",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--context", help="Arg=(kubernetes context)")
    parser.add_argument("-n", "--namespace", help="Arg=(kubernetes namespace)")
    parser.add_argument("--pvc", help="Arg=(PersistenceVolumeClaim name)")
    parser.add_argument(
        "--sc", help="Arg=(StorageClassName)", default="ebs-gp3-ext4-eu-west-1b"
    )
    parser.add_argument(
        "--vs",
        action="store_true",
        default=False,
        # help="Arg=(Backup VolumeSnapshot)",
        help=argparse.SUPPRESS,
    )
    # argo
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
