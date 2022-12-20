"""
pipeline:

1. передаем селектор - какие-ноды хотим сдрейнить
2. строится список нод
3. принимаем решение для дрейна: чанки или manual
4. печатается имя ноды и поды на ней
5. срабатывает drain
"""
import argparse
import logging
import json
from time import sleep
import typing as t

import emoji

from platform_cli.libs.others import (
    logging_prefix,
    k8s_owner_info,
    confirm,
    LOG_LEVEL,
)

from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s

from prettytable import PrettyTable

from kubernetes.client.models import V1Pod, V1Node

# TODO: avoid of usage global instance
k = K8s(
    context="ctx",
    namespace=None,
    pvc=None,
)

logging.getLogger("kubernetes").setLevel(logging.ERROR)


def cli():
    example_text = """
    pl-cli --tool rotator --context $ctx -l 'node.kubernetes.io/owner=project' -v INFO
    """

    parser = argparse.ArgumentParser(
        description="CLI for rotate kubernetes worker nodes",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--context", help="Arg=(kubernetes context)")
    parser.add_argument("-l", "--selector", help="Arg=(Selector (label query) for nodes)")
    parser.add_argument("-m", "--mode", help="Arg=()", choices=["chunks", "manual"], default="chunks")
    parser.add_argument("--sleep", help="Arg=(Pause between mode=<chunks> drains in seconds)", type=int, default=90)
    parser.add_argument("--ratio", help="Arg=(How much need to wait between chunks drains?)", type=float, default=0.1)
    # logs
    parser.add_argument(
        "-v",
        "--verbose",
        help="Arg=(Logging Level)",
        # default="ERROR",
        default="INFO",
        choices=list(LOG_LEVEL.keys()),
    )
    args = parser.parse_args()

    return args


def print_table(bucket: dict):
    table = PrettyTable()
    table.field_names = ["team", "user"]
    for team in bucket:

        for user in bucket[team]:
            table.add_row([team, user])
    return table


def pods_on_node_table(pods: t.List[V1Pod]) -> None:
    table = PrettyTable()
    table.field_names = ["PodName", "PodNamespace", "OwnerKind"]
    for pod in pods:
        table.add_row([pod.metadata.name, pod.metadata.namespace, k8s_owner_info(pod.metadata)["kind"]])
    table.sortby = "PodNamespace"
    print(table)


def drain_node_chunks_calc(node_count: int) -> int:
    chunk = int(node_count * 0.1)
    if chunk >= 1:
        return chunk
    else:
        return 1


def node_drain(node: V1Node, pods: t.List[V1Pod]) -> dict:
    """
    1. cordon node
    2. evict every pod
    """
    not_evicted = {}
    node_name = node.metadata.name
    logging.debug(f"{logging_prefix()} k.cordon_node=<{node_name}>")
    k.cordon_node(node_name)

    ev = []
    for pod in pods:
        r = k.evict_pod(pod)
        if isinstance(r, V1Pod):
            ev.append(pod.metadata.name)
        if ev:
            not_evicted.update({node_name: ev})
    return not_evicted


def pod_eviction_retry():
    pass


def drain_manual(nodes: list) -> dict:
    not_evicted_all_nodes = {}
    for node in nodes:
        node_name = node.metadata.name
        print(emoji.emojize(f":laptop: Node: <{node_name}>"))

        pods = k.get_pods(node_name)
        pods_on_node_table(pods)

        proceed = confirm(f"drain node: <{node_name}>", node_name)
        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Node=<{node_name}>")
            return not_evicted_all_nodes
        not_evicted = node_drain(node, pods)
        not_evicted_all_nodes.update(not_evicted)

    return not_evicted_all_nodes


def drain_node_chunks(nodes: list, wait: int = 110) -> dict:
    chunk_size = drain_node_chunks_calc(len(nodes))
    not_evicted_all_nodes = {}
    while nodes:
        step = nodes[:chunk_size]
        nodes = nodes[chunk_size:]
        for node in step:
            node_name = node.metadata.name
            print(emoji.emojize(f":laptop: Node: <{node_name}>"))
            pods = k.get_pods(node_name)
            pods_on_node_table(pods)

            not_evicted = node_drain(node, pods)
            not_evicted_all_nodes.update(not_evicted)
        else:
            print(emoji.emojize(f":sleeping_face: sleeping <{wait}> seconds"))
            sleep(wait)

    return not_evicted


def main():
    # *arg, **kwarg -> другой интерфейс
    # cli args, logging
    user_args = cli()

    logging.basicConfig(
        level=LOG_LEVEL[user_args.verbose],
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    logging.debug(f"{logging_prefix()}  <user_args>: {user_args}")

    # Kubernetes
    k = K8s(
        context=user_args.context,
        namespace=user_args.namespace,
        pvc=user_args.pvc,
        sc=user_args.sc,
    )
    nodes = k.get_nodes(user_args.selector)
    not_evicted = drain_manual(nodes)
    print(json.dumps(not_evicted, indent=4))


if __name__ == "__main__":
    main()
