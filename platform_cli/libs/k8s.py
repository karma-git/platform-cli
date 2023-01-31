import logging
from pathlib import Path
from uuid import uuid4
import typing as t
import ast

from platform_cli.libs.others import logging_prefix, k8s_owner_info, CRD_DICT, save_request_json

from kubernetes import client, config

# typing
from kubernetes.client.models import (
    V1PersistentVolumeClaim,
    V1ObjectMeta,
    V1OwnerReference,
    V1PodList,
    V1Pod,
    V1Deployment,
    V1StatefulSet,
    V1CustomResourceDefinition,
    V1Job,
    V1Node,
    V1Eviction
)
from kubernetes.client.exceptions import ApiException
import yaml

from dataclasses import dataclass, field


@dataclass
class PodAbstraction:
    name: str
    owner_ref: V1OwnerReference | None
    argo_inst: str | None
    is_workload_owner: field(init=True)
    # object_owner: field(init=True)
    version: field(init=True)
    group: field(init=True)
    plural: field(init=True)

    def __post_init__(self):
        if self.owner_ref is not None and self.argo_inst is not None:
            self.is_workload_owner = True
            api = self.owner_ref[0].api_version.split("/")
            self.group = api[0]
            self.version = api[1]
            self.plural = CRD_DICT.get(self.owner_ref[0].kind)
        else:
            self.is_workload_owner = False


class K8s:
    migrate_job_template = f"{Path(__file__).parent}/yaml/job-rsync.yml"
    vs_template = f"{Path(__file__).parent}/yaml/volume-snapshot.yml"

    def __init__(
        self,
        context,
        namespace=None,
        pvc=None,
        sc="ebs-gp3-ext4-eu-west-1b",
    ) -> None:
        self.ctx = context
        self.ns = namespace
        self.pvc = pvc
        self.sc = sc

        self.CoreV1Api = None
        self.AppsV1Api = None
        self.CustomObjectsApi = None
        self.BatchV1Api = None

        self._api_init()

    def _api_init(self) -> None:
        config.load_kube_config(context=self.ctx)
        self.CoreV1Api = client.CoreV1Api()
        self.AppsV1Api = client.AppsV1Api()
        self.CustomObjectsApi = client.CustomObjectsApi()
        self.BatchV1Api = client.BatchV1Api()

    # nodes

    def get_nodes(self, label_selector) -> t.List[V1Node]:
        (
            response,
            http_sc,
            _,
        ) = self.CoreV1Api.list_node_with_http_info(
            label_selector=label_selector,
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>nodes=<{len(response.items)}>")
        # return response
        nodes = [node for node in response.items]
        return nodes

    def cordon_node(self, name: str, unschedulable: bool = True) -> V1Node:
        body = {
        "spec": {
            "unschedulable": unschedulable,
        },
    }
        (
            response,
            http_sc,
            _,
        )  = self.CoreV1Api.patch_node_with_http_info(
            name=name,
            body=body
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,pvc_name=<{response.metadata.name}>")
        return response


    def get_pods(self, node_name) -> t.List[V1Pod]:
        all_pods = self.CoreV1Api.list_pod_for_all_namespaces(field_selector=f'spec.nodeName={node_name}')
        logging.info(f"{logging_prefix()} node=<{node_name}>,all_pods=<{len(all_pods.items)}>")
        pods_wo_ds = [p for p in all_pods.items
                  if k8s_owner_info(p.metadata).get("kind") != 'DaemonSet']

        logging.info(f"{logging_prefix()} node=<{node_name}>,pods_wo_ds=<{len(pods_wo_ds)}>")
        return pods_wo_ds

    def evict_pod(self, pod: V1Pod) -> t.Union[V1Eviction, V1Pod]:
        """
        'kind': 'Status',
        'metadata': {'annotations': None,
              'creation_timestamp': None,
              'deletion_grace_period_seconds': None,
              'deletion_timestamp': None,
              'finalizers': None,
              'generate_name': None,
              'generation': None,
              'labels': None,
              'managed_fields': None,
              'name': None,
              'namespace': None,
              'owner_references': None,
              'resource_version': None,
              'self_link': None,
              'uid': None}}
        """
        name = pod.metadata.name
        namespace = pod.metadata.namespace
        metadata = V1ObjectMeta(name=name, namespace=namespace)
        body = V1Eviction(metadata=metadata)
        try:
            response = self.CoreV1Api.create_namespaced_pod_eviction(name, namespace, body)
        except ApiException as e:
            body = ast.literal_eval(e.body) # body is a string, so it need to be converted into dict
            if body["message"] == "Cannot evict pod as it would violate the pod's disruption budget.":
                logging.warning(
                f"{logging_prefix()}   can't evict pod=<{name} due to pdp,details=<{body['details']['causes'][0]['message']}>"
                )
                return pod
            else:
                logging.error(
                f"{logging_prefix()}   <code>={e.status}\n\t details={e.body}"
            )
        # if we got response from eviction api
        else:
            return response

    # pv

    def get_pvc(self, pvc_name) -> V1PersistentVolumeClaim:
        (
            response,
            http_sc,
            _,
        ) = self.CoreV1Api.read_namespaced_persistent_volume_claim_with_http_info(
            name=pvc_name,
            namespace=self.ns,
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,pvc_name=<{pvc_name}>")
        if response.status.phase != "Bound":
            raise Exception(
                f"{logging_prefix()}   <pvc>={self.pvc} is not created, probably something wrong with provisioner"
            )
        return response

    def create_pvc(
        self, pvc_name: str, manifest: V1PersistentVolumeClaim
    ) -> V1PersistentVolumeClaim:
        metadata = V1ObjectMeta(name=pvc_name, namespace=self.ns)

        manifest.spec.volume_name = None
        manifest.metadata = metadata
        manifest.spec.storage_class_name = self.sc

        try:
            (
                response,
                http_sc,
                _,
            ) = self.CoreV1Api.create_namespaced_persistent_volume_claim_with_http_info(
                namespace=self.ns,
                body=manifest,
            )
            logging.info(f"{logging_prefix()} code=<{http_sc}>,pvc_name=<{pvc_name}>")
            return response
        except ApiException as e:
            logging.warning(
                f"{logging_prefix()}   <code>={e.status}\n\t details={e.body}"
            )

    def delete_pvc(self, pvc_name):
        (
            response,
            http_sc,
            _,
        ) = self.CoreV1Api.delete_namespaced_persistent_volume_claim_with_http_info(
            name=pvc_name, namespace=self.ns
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,pvc_name=<{pvc_name}>")
        return response

    # workloads

    def pod_pvc_relationship(self) -> V1ObjectMeta:
        pods: V1PodList = self.CoreV1Api.list_namespaced_pod(namespace=self.ns)

        try:
            for pod in pods.items:  # pods in ns
                try:
                    for v in pod.spec.volumes:  # volumes of the pod
                        if v.persistent_volume_claim:  # looking for pvc volumes
                            if v.persistent_volume_claim.claim_name == self.pvc:
                                logging.info(
                                    f"{logging_prefix()}   <pod>={pod.metadata.name}\n\t owner={k8s_owner_info(pod.metadata)}"
                                )
                                return pod.metadata
                except:
                    logging.error(
                        f"{logging_prefix()}   Strange situation :D"
                    )
        except ApiException as e:
            logging.warning(
                f"{logging_prefix()}   <code>={e.status}\n\t details={e.body}"
            )
            # raise Exception(
            #     f"{logging_prefix()}    <pvc>={self.pvc} is not bonded to any pod"
            # )

    def get_deploy(self, deploy_name) -> V1Deployment:
        response, http_sc, _ = self.AppsV1Api.read_namespaced_deployment_with_http_info(
            name=deploy_name, namespace=self.ns
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{deploy_name}>")
        return response

    def get_sts(self, sts_name) -> V1StatefulSet:
        (
            response,
            http_sc,
            _,
        ) = self.AppsV1Api.read_namespaced_stateful_set_with_http_info(
            name=sts_name, namespace=self.ns
        )
        self.AppsV1Api.delete_namespaced_stateful_set_with_http_info
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{sts_name}>")
        return response

    def get_crd(self, name, group, version, plural) -> V1CustomResourceDefinition:
        (
            response,
            http_sc,
            _,
        ) = self.CustomObjectsApi.get_namespaced_custom_object_with_http_info(
            group=group,
            version=version,
            namespace=self.ns,
            plural=plural,
            name=name,
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{name}>")
        return response

    def scale_deploy(self, deploy_name, replicas=0):
        (
            response,
            http_sc,
            _,
        ) = self.AppsV1Api.patch_namespaced_deployment_with_http_info(
            name=deploy_name, namespace=self.ns, body={"spec": {"replicas": replicas}}
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{deploy_name}>")
        return response

    def scale_sts(self, sts_name, replicas=0) -> V1StatefulSet:
        (
            response,
            http_sc,
            _,
        ) = self.AppsV1Api.patch_namespaced_stateful_set_with_http_info(
            name=sts_name, namespace=self.ns, body={"spec": {"replicas": replicas}}
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,sts_name=<{sts_name}>")
        return response

    def scale_crd(
        self, name, group, version, plural, replicas=0
    ) -> V1CustomResourceDefinition:
        (
            response,
            http_sc,
            _,
        ) = self.CustomObjectsApi.patch_namespaced_custom_object_with_http_info(
            group=group,
            version=version,
            namespace=self.ns,
            plural=plural,
            name=name,
            body={"spec": {"replicas": replicas}},
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{name}>")
        return response

    def delete_sts(self, sts_name) -> V1StatefulSet:
        (
            response,
            http_sc,
            _,
        ) = self.AppsV1Api.delete_namespaced_stateful_set_with_http_info(
            name=sts_name, namespace=self.ns, propagation_policy="Orphan"
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,sts_name=<{sts_name}>")
        return response

    # payload

    def create_snapshot(self, pvc_name, vsc):
        with open(self.vs_template) as y:
            vs = yaml.safe_load(y)

        vs["metadata"]["name"] = pvc_name
        vs["spec"]["source"]["persistentVolumeClaimName"] = pvc_name
        vs["spec"]["volumeSnapshotClassName"] = vsc
        vs["metadata"]["namespace"] = self.ns
        try:
            (
                response,
                http_sc,
                _,
            ) = self.CustomObjectsApi.create_namespaced_custom_object_with_http_info(
                group="snapshot.storage.k8s.io",
                version="v1",
                plural="volumesnapshots",
                namespace=self.ns,
                body=vs,
            )
            logging.info(
                f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{pvc_name}>"
            )
            return response
        except ApiException as e:
            logging.warning(
                f"{logging_prefix()}   <code>={e.status}\n\t details={e.body}"
            )

    def migrate_job(self, src_pvc, dest_pvc) -> V1Job:
        with open(self.migrate_job_template) as y:
            job = yaml.safe_load(y)

        # v = lambda job, i: job["spec"]["template"]["spec"]["volumes"][i]["persistentVolumeClaim"]["claimName"]
        job_name = f"pv-migrate-{uuid4().hex[0:6]}"

        job["metadata"]["name"] = job_name
        job["metadata"]["namespace"] = self.ns

        job["spec"]["template"]["spec"]["volumes"][0]["persistentVolumeClaim"][
            "claimName"
        ] = src_pvc
        job["spec"]["template"]["spec"]["volumes"][1]["persistentVolumeClaim"][
            "claimName"
        ] = dest_pvc
        response, http_sc, _ = self.BatchV1Api.create_namespaced_job_with_http_info(
            namespace=self.ns, body=job
        )
        logging.info(f"{logging_prefix()} code=<{http_sc}>,deploy_name=<{job_name}>")
        return response

    def watch_migrate_job(self, job_name):
        pass