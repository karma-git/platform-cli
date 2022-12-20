from platform_cli.cli_tools.argo import Argo
from platform_cli.cli_tools.migration_ebs.factories.argo_crd import ArgoCRDFactory
from platform_cli.cli_tools.argo.models.argo_settings import ArgoConfigs
from platform_cli.libs.argo import ArgoCRD


class ArgoFactory:

    def __init__(self, config: ArgoConfigs):
        self.__config = config

    def __create_argo_crd(self) -> ArgoCRD:
        factory = ArgoCRDFactory(self.__config)
        return factory.create()

    def create(self) -> Argo:
        argo_crd = self.__create_argo_crd()

        return Argo(argo_crd, self.__config)
