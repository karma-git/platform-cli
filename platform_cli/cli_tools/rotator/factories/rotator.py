from platform_cli.cli_tools.rotator import Rotator
from platform_cli.cli_tools.rotator.factories.k8s import K8sFactory
from platform_cli.cli_tools.rotator.models.rotator_settings import RotatorConfigs
from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s


class RotatorFactory:
    def __init__(self, config: RotatorConfigs):
        self.__config = config

    def __create_k8s(self) -> K8s:
        factory = K8sFactory(self.__config)
        return factory.create()

    def create(self) -> Rotator:
        k8s = self.__create_k8s()

        return Rotator(k8s, self.__config)
