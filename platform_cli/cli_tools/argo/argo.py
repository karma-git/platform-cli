import logging
from functools import cached_property
from typing import Optional, Any, Tuple

from platform_cli.cli_tools.argo.models.argo_settings import ArgoConfigs
from platform_cli.libs.others import (
    logging_prefix,
    LOG_LEVEL,
)
from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s


class Argo:

    """
    ArgoAPI
    """

    def __init__(self, argo_crd: ArgoCRD, config: ArgoConfigs):
        self.__config = config
        self.__argo_crd = argo_crd

    def __init_logger(self) -> None:
        logging.basicConfig(
            level=LOG_LEVEL[self.__config.verbose],
            format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        )
        logging.debug(f"{logging_prefix()}  <user_args>: {self.__config.dict()}")

    def toggle_sync(self) -> None:
        self.__init_logger()
        if self.__config.sync:
            self.__argo_crd.enable_autosync(self.__config.sync_app)
        elif not self.__config.sync:
            argo_chain = self.__argo_crd.app_of_apps_chain(self.__config.sync_app)
            self.__argo_crd.disable_autosync_chain(argo_chain)
