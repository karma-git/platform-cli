from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs
from platform_cli.libs.argo import ArgoCRD


class ArgoCRDFactory:

    def __init__(self, config: MigrationEbsConfigs):
        self.__config = config

    def create(self) -> ArgoCRD:
        return ArgoCRD(context=self.__config.context)
