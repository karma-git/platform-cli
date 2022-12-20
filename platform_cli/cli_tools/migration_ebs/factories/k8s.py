from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs
from platform_cli.libs.k8s import K8s


class K8sFactory:

    def __init__(self, config: MigrationEbsConfigs):
        self.__config = config

    def create(self) -> K8s:
        return K8s(
            context=self.__config.context,
            namespace=self.__config.namespace,
            pvc=self.__config.pvc,
            sc=self.__config.sc,
        )
