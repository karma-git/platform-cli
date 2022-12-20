from argparse import Namespace

from platform_cli.cli_tools.rotator.factories.base import AbstractConfigRotatorFactory
from platform_cli.cli_tools.rotator.models.rotator_settings import RotatorConfigs


class ArgparseConfigRotatorFactory(AbstractConfigRotatorFactory):
    def __init__(self, args: Namespace):
        self.__args = args

    def create(self) -> RotatorConfigs:
        rotator_config = RotatorConfigs()

        rotator_config.context = self.__args.context
        rotator_config.selector = self.__args.selector
        rotator_config.mode = self.__args.mode
        rotator_config.sleep = self.__args.sleep
        rotator_config.ratio = self.__args.ratio
        rotator_config.verbose = self.__args.verbose

        return rotator_config
