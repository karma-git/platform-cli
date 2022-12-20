import logging
import typing as t

from kubernetes.client.models import (
    V1Pod,
)

from prettytable import PrettyTable

from platform_cli.libs.others import k8s_owner_info, argo_instance, logging_prefix, pod_to_deployment_name


def drain_node_chunks_calc(node_count: int, ratio: float) -> int:
    chunk = int(node_count * ratio)
    if chunk >= 1:
        return chunk
    else:
        return 1


def pods_on_node_table(pods: t.List[V1Pod]) -> None:
    table = PrettyTable()
    table.field_names = ["PodName", "PodNamespace", "OwnerKind"]
    for pod in pods:
        table.add_row([pod.metadata.name, pod.metadata.namespace, k8s_owner_info(pod.metadata)["kind"]])
    table.sortby = "PodNamespace"
    print(table)
