from platform_cli.cli_tools.argo.factories.argparse_configuration import ArgparseConfigArgoFactory
from platform_cli.cli_tools.argo.factories.argo import ArgoFactory
from platform_cli.cli_tools.argo.services.argparser import get_args


def argo() -> None:
    args = get_args()
    configuration = ArgparseConfigArgoFactory(args).create()

    argo = ArgoFactory(configuration).create()
    argo.toggle_sync()

if __name__ == "__main__":
    argo()
