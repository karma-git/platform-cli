import logging
from functools import cached_property
from typing import Optional

from kubernetes.client import V1ObjectMeta, V1Deployment

from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s
from platform_cli.libs.others import k8s_owner_info, argo_instance, logging_prefix, pod_to_deployment_name


class RsScalerService:

    def __init__(self, k8s: K8s, argo_crd: ArgoCRD, pod_metadata: V1ObjectMeta):
        self.__k8s = k8s
        self.__argo_crd = argo_crd
        self.__pod_metadata = pod_metadata

    @cached_property
    def deploy_name(self) -> str:
        deploy_name = pod_to_deployment_name(self.__pod_metadata.name)
        return deploy_name

    @cached_property
    def deploy(self) -> V1Deployment:
        deploy = self.__k8s.get_deploy(self.deploy_name)
        return deploy

    @cached_property
    def rs_owner(self) -> Optional[dict]:
        owner = k8s_owner_info(self.deploy.metadata)
        logging.debug(f"{logging_prefix()}:  Step3(D): owner=<{owner}>")

        return owner

    @cached_property
    def rs_argo_app(self) -> Optional[str]:
        argo_app = argo_instance(self.deploy.metadata)
        logging.debug(f"{logging_prefix()}:  Step3(D): argo_app=<{argo_app}>")

        return argo_app

    def scale_rs_if_owner(self) -> None:
        if self.rs_owner is None and self.rs_argo_app is not None:
            # выключаем autosync
            argo_chain = self.__argo_crd.app_of_apps_chain(self.rs_argo_app)
            self.__argo_crd.disable_autosync_chain(argo_chain)
            # скейлим нагрузку
            self.__k8s.scale_deploy(self.deploy.metadata.name)

    def scale_rs_if_not_owner(self) -> None:
        if self.rs_owner is None and self.rs_argo_app is not None:
            # выключаем autosync
            argo_chain = self.__argo_crd.app_of_apps_chain(self.rs_argo_app)
            self.__argo_crd.disable_autosync_chain(argo_chain)
            # скейлим нагрузку
            self.__k8s.scale_deploy(self.deploy.metadata.name)

    def scale_rs(self) -> None:
        self.scale_rs_if_owner()
        self.scale_rs_if_not_owner()
