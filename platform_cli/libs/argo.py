"""
TODO: DRY common parts in classes
ref: https://argo-cd.readthedocs.io/en/stable/developer-guide/api-docs/
http://localhost:8080/swagger-ui
"""
import logging
from typing import List
import json

from kubernetes import client, config
import requests

from platform_cli.libs.others import logging_prefix


class ArgoApi:
    def __init__(self, server, token=None):
        self.server = server
        self._bearer_header = {"Authorization": f"Bearer {token}"}

    @staticmethod
    def generate_bearer_token(server: str, username: str, password: str) -> str:
        data = json.dumps({"username": username, "password": password}).encode("utf-8")
        response = requests.post(
            f"https://{server}/api/v1/session",
            data=data,
        )
        logging.info(f"{logging_prefix()}  <response>: {response, response.json()}")
        token = response.json()["token"]

        return token

    def list_argo_applications(self) -> dict:
        """
        result:
        {
            "cluster-init": null,
            "platform-environment": "cluster-init",
            "platform-core": "platform-environment",
            "karpenter": "platform-core"
        }
        """
        response = requests.get(
            f"https://{self.server}/api/v1/applications",
            headers=self._bearer_header,
        )
        apps = response.json()["items"]
        logging.info(f"{logging_prefix()}  <apps_count>: {len(apps)}")
        apps_dict = {}

        for app in apps:
            name = app["metadata"]["name"]
            owner = app["metadata"]["labels"].get("argocd.argoproj.io/instance")
            apps_dict.update({name: owner})

        logging.debug(f"{logging_prefix()}  <apps_dict>: {apps_dict}")
        return apps_dict

    def app_of_apps_chain(self, app_name) -> List[str]:
        """
        return ['cluster-init', 'platform-environment', 'platform-core', 'karpenter']
        """
        apps_dict = (
            self.list_argo_applications()
        )  # NOTE: see <list_argo_applications> for example payload
        chain = [app_name]  # [..., karpenter]
        owner = apps_dict[app_name]  # platform-core

        while owner is not None:
            chain.insert(0, owner)  # [..., platform-core, loki]
            owner = apps_dict[owner]  # platform-environment
        else:
            logging.info(f"{logging_prefix()}  <chain>: {' -> '.join(chain)}")
        return chain

    def disable_autosync(self, app_name):
        body = {"spec": {"syncPolicy": None}}  # it's ok
        # body = {"spec": {"syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}}  # for some reason this request will delete applicaition
        response = requests.post(
            f"https://{self.server}/api/v1/applications/{app_name}",
            headers=self._bearer_header,
            data=body,
        )
        logging.debug(f"{logging_prefix()}    {app_name}->{response.status_code}")
        return response

    def disable_autosync_chain(self, apps_chain):
        body = {"spec": {"syncPolicy": None}}
        for app in apps_chain:
            response = requests.post(
                f"https://{self.server}/api/v1/applications/{app}",
                headers=self._bearer_header,
                data=body,
            )
            logging.debug(f"{logging_prefix()}    {app}->{response.status_code}")

    def enable_autosync(self, app_name):
        response = requests.get(
            f"https://{self.server}/api/v1/applications/{app_name}",
            headers=self._bearer_header,
        )
        logging.debug(f"{logging_prefix()}    GET:{app_name}->{response.status_code}")
        body = response.json()

        # PATCH

        body["spec"].update(
            {"syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}
        )
        response = requests.post(
            f"https://{self.server}/api/v1/applications/{app_name}",
            headers=self._bearer_header,
            data=body,
        )
        logging.debug(f"{logging_prefix()}    PATCH:{app_name}->{response.status_code}")
        return response

    def apps_of_apps_chain(self):
        pass

    def apps_of_apps_graph(self):
        """
        ref: https://github.com/thebjorn/pydeps
        """
        pass


class ArgoCRD:
    ARGO_CRD = {
        "group": "argoproj.io",
        "version": "v1alpha1",
        "plural": "applications",
    }

    def __init__(self, context, namespace="argocd"):
        self.ctx = context
        self.ns = namespace

        self.CustomObjectsApi = None
        self._api_init()

    def _api_init(self) -> None:
        config.load_kube_config(context=self.ctx)
        self.CustomObjectsApi = client.CustomObjectsApi()

    def list_argo_applications(self) -> dict:
        """
        result:
        {
            "cluster-init": null,
            "platform-environment": "cluster-init",
            "platform-core": "platform-environment",
            "karpenter": "platform-core"
        }
        """
        (
            response,
            http_sc,
            _,
        ) = self.CustomObjectsApi.list_namespaced_custom_object_with_http_info(
            **self.ARGO_CRD,
            namespace=self.ns,
        )
        apps = response["items"]
        logging.info(f"{logging_prefix()}  code=<{http_sc}>,<apps_count>: {len(apps)}")
        apps_dict = {}

        for app in apps:
            name = app["metadata"]["name"]
            owner = app["metadata"]["labels"].get("argocd.argoproj.io/instance")
            apps_dict.update({name: owner})

        logging.debug(f"{logging_prefix()}  <apps_dict>: {apps_dict}")
        return apps_dict

    def app_of_apps_chain(self, app_name) -> List[str]:
        """
        return ['cluster-init', 'platform-environment', 'platform-core', 'karpenter']
        """
        apps_dict = (
            self.list_argo_applications()
        )  # NOTE: see <list_argo_applications> for example payload
        chain = [app_name]  # [..., karpenter]
        owner = apps_dict[app_name]  # platform-core

        while owner is not None:
            chain.insert(0, owner)  # [..., platform-core, loki]
            owner = apps_dict[owner]  # platform-environment
        else:
            logging.info(f"{logging_prefix()}  <chain>: {' -> '.join(chain)}")
        return chain

    def disable_autosync(self, app_name):
        body = {"spec": {"syncPolicy": None}}  # it's ok
        (
            response,
            http_sc,
            _,
        ) = self.CustomObjectsApi.patch_namespaced_custom_object_with_http_info(
            **self.ARGO_CRD,
            namespace=self.ns,
            name=app_name,
            body=body,
        )
        logging.info(f"{logging_prefix()}    code=<{http_sc}>,app_name=<{app_name}>")
        return response

    def disable_autosync_chain(self, apps_chain):
        body = {"spec": {"syncPolicy": None}}
        for app in apps_chain:
            (
                response,
                http_sc,
                _,
            ) = self.CustomObjectsApi.patch_namespaced_custom_object_with_http_info(
                **self.ARGO_CRD,
                namespace=self.ns,
                name=app,
                body=body,
            )
            logging.info(f"{logging_prefix()}    code=<{http_sc}>,app_name=<{app}>")

    def enable_autosync(self, app_name):
        body = {
            "spec": {"syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}
        }
        (
            response,
            http_sc,
            _,
        ) = self.CustomObjectsApi.patch_namespaced_custom_object_with_http_info(
            **self.ARGO_CRD,
            namespace=self.ns,
            name=app_name,
            body=body,
        )
        logging.info(f"{logging_prefix()}    code=<{http_sc}>,app_name=<{app_name}>")
        return response

    def apps_of_apps_chain(self):
        pass

    def apps_of_apps_graph(self):
        """
        ref: https://github.com/thebjorn/pydeps
        """
        pass
