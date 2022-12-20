from platform_cli.cli_tools.migration_ebs import MigrationEbs
from platform_cli.cli_tools.migration_ebs.factories.argo_crd import ArgoCRDFactory
from platform_cli.cli_tools.migration_ebs.factories.k8s import K8sFactory
from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs
from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s


class MigrationEbsFactory:

    def __init__(self, config: MigrationEbsConfigs):
        self.__config = config

    def __create_k8s(self) -> K8s:
        factory = K8sFactory(self.__config)
        return factory.create()

    def __create_argo_crd(self) -> ArgoCRD:
        factory = ArgoCRDFactory(self.__config)
        return factory.create()

    def create(self) -> MigrationEbs:
        k8s = self.__create_k8s()
        argo_crd = self.__create_argo_crd()

        return MigrationEbs(k8s, argo_crd, self.__config)
