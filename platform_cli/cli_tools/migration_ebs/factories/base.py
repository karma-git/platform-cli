from abc import ABC, abstractmethod

from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs


class AbstractConfigMigrationEbsFactory(ABC):

    @abstractmethod
    def create(self) -> MigrationEbsConfigs:
        pass
