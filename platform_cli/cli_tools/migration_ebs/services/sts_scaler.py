from functools import cached_property
from time import sleep
from typing import Optional
import logging

from kubernetes.client import V1StatefulSet

from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s
from platform_cli.libs.others import k8s_owner_info, argo_instance, logging_prefix


class StsScalerService:

    def __init__(self, k8s: K8s, argo_crd: ArgoCRD, pod_owner: str):
        self.__k8s = k8s
        self.__argo_crd = argo_crd
        self.__pod_owner = pod_owner

    @cached_property
    def stateful_set(self) -> V1StatefulSet:
        stateful_set = self.__k8s.get_sts(self.__pod_owner)
        return stateful_set

    @cached_property
    def owner_info(self):
        owner = k8s_owner_info(self.stateful_set.metadata)
        logging.warning(f"{logging_prefix()}:  Step3(STS): owner=<{owner}>")

        return owner

    @cached_property
    def argo_instance(self) -> Optional[str]:
        argo_app = argo_instance(self.stateful_set.metadata)
        logging.warning(f"{logging_prefix()}:  Step3(STS): argo_app=<{argo_app}>")

        return argo_app

    def scale_sts_if_owner(self) -> None:
        if self.owner_info is None and self.argo_instance is not None:
            # выключаем autosync
            argo_chain = self.__argo_crd.app_of_apps_chain(self.argo_instance)
            self.__argo_crd.disable_autosync_chain(argo_chain)
            # скейлим нагрузку
            self.__k8s.scale_sts(self.stateful_set.metadata.name)
            # NOTE: need to recreate sts due to update sc in pvcTemplate
            sleep_time = 30  # sec
            logging.warning(
                f"{logging_prefix()}:  Step3(STS): sleep {sleep_time} sec>"
            )
            sleep(sleep_time)
            self.__k8s.delete_sts(self.stateful_set.metadata.name)

    def scale_sts_if_not_owner(self) -> None:
        if self.owner_info is not None and self.argo_instance is not None:
            # ищем более высокуровневого овнера
            crd_owner = k8s_owner_info(self.stateful_set.metadata)
            crd_owner.pop("kind")
            crd = self.__k8s.get_crd(**crd_owner)
            argo_app = argo_instance(crd["metadata"])

            # скейлим нагрузку
            argo_chain = self.__argo_crd.app_of_apps_chain(argo_app)
            self.__argo_crd.disable_autosync_chain(argo_chain)

            self.__k8s.scale_crd(**crd_owner)

    def scale_sts(self) -> None:
        self.scale_sts_if_owner()
        self.scale_sts_if_not_owner()
