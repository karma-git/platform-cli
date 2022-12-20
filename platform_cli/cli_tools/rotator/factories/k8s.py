from platform_cli.cli_tools.rotator.models.rotator_settings import RotatorConfigs
from platform_cli.libs.k8s import K8s


class K8sFactory:
    def __init__(self, config: RotatorConfigs):
        self.__config = config

    def create(self) -> K8s:
        return K8s(
            context=self.__config.context,
        )
