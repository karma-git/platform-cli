from abc import ABC, abstractmethod

from platform_cli.cli_tools.argo.models.argo_settings import ArgoConfigs


class AbstractConfigArgoFactory(ABC):

    @abstractmethod
    def create(self) -> ArgoConfigs:
        pass
