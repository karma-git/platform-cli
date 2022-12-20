from argparse import Namespace

from platform_cli.cli_tools.migration_ebs.factories.base import AbstractConfigMigrationEbsFactory
from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs


class ArgparseConfigMigrationEbsFactory(AbstractConfigMigrationEbsFactory):

    def __init__(self, args:  Namespace):
        self.__args = args

    def create(self) -> MigrationEbsConfigs:
        migration_config = MigrationEbsConfigs()

        migration_config.context = self.__args.context
        migration_config.namespace = self.__args.namespace
        migration_config.pvc = self.__args.pvc
        migration_config.sc = self.__args.sc
        migration_config.vs = self.__args.vs
        migration_config.sync_app = self.__args.sync_app
        migration_config.verbose = self.__args.verbose

        return migration_config
