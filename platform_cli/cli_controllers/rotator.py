from platform_cli.cli_tools.rotator.factories.argparse_configuration import ArgparseConfigRotatorFactory
from platform_cli.cli_tools.rotator.factories.rotator import RotatorFactory
from platform_cli.cli_tools.rotator.services.argparser import get_args


def rotator() -> None:
    args = get_args()
    configuration = ArgparseConfigRotatorFactory(args).create()

    rotation = RotatorFactory(configuration).create()
    rotation.rotate()


if __name__ == "__main__":
    rotator()
