from argparse import Namespace

from platform_cli.cli_tools.argo.factories.base import AbstractConfigArgoFactory
from platform_cli.cli_tools.argo.models.argo_settings import ArgoConfigs


class ArgparseConfigArgoFactory(AbstractConfigArgoFactory):

    def __init__(self, args:  Namespace):
        self.__args = args

    def create(self) -> ArgoConfigs:
        argo_config = ArgoConfigs()

        argo_config.context = self.__args.context
        argo_config.namespace = self.__args.namespace
        argo_config.sync = self.__args.sync
        argo_config.no_sync = self.__args.no_sync
        argo_config.sync_app = self.__args.sync_app
        argo_config.verbose = self.__args.verbose

        return argo_config
