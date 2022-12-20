import argparse
import logging
from typing import Callable

from platform_cli.cli_controllers.migration_ebs import migration_ebs
from platform_cli.cli_controllers.argo import argo
from platform_cli.cli_controllers.rotator import rotator

__tools_runners = {
    "argo": argo,
    "migration-ebs": migration_ebs,
    "rotator": rotator,
}


def __get_tool_name() -> str:
    example_text = """
        platform_cli --tool migration-ebs --context sandbox -n loki --pvc storage-loki-0
    """

    parser = argparse.ArgumentParser(
        description="CLI utility for working with the k8s-cluster",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--tool", help="Arg=(Name of the tool from the platform_cli library)", required=True,
    choices=["argo", "migration-ebs", "rotator"])
    args, _ = parser.parse_known_args()

    return args.tool


def __get_tool_runner(tool_name: str) -> Callable:
    return __tools_runners.get(tool_name)


def run_utils():
    tool_name = __get_tool_name()
    tool_runner = __get_tool_runner(tool_name)
    tool_runner()


if __name__ == "__main__":
    logging.getLogger('kubernetes').setLevel(logging.ERROR)
    run_utils()
