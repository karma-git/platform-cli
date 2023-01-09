import logging
import datetime as dt
import typing as t

from kubernetes.client.models import (
    V1Pod,
)

from prettytable import PrettyTable
import humanize
import emoji

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

def node_message(context: str, node_name: str, node_age: dt.datetime, print_time: bool = True) -> str:
    message = f":ship: Context <{context}>, :laptop: Node: <{node_name}>"
    if print_time:
        delta: dt.timedelta = node_age - dt.datetime.now(dt.timezone.utc)
        h_node_age = humanize.precisedelta(delta, minimum_unit='minutes', format='%0.0f')
        message += f", :alarm_clock: Age: <{h_node_age}>"
    return emoji.emojize(message)
