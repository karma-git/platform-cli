from abc import ABC, abstractmethod

from platform_cli.cli_tools.rotator.models.rotator_settings import RotatorConfigs


class AbstractConfigRotatorFactory(ABC):
    @abstractmethod
    def create(self) -> RotatorConfigs:
        pass
