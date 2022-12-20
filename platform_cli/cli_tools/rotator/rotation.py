import logging
import json
from functools import cached_property
from typing import Optional, Any, Tuple
import typing as t
from time import sleep

import emoji

from kubernetes.client.models import V1Pod, V1Node

from platform_cli.cli_tools.rotator.models.rotator_settings import RotatorConfigs


from platform_cli.libs.others import (
    logging_prefix,
    confirm,
    LOG_LEVEL,
)
from platform_cli.libs.k8s import K8s
from platform_cli.cli_tools.rotator.services.helpers import drain_node_chunks_calc, pods_on_node_table


class Rotator:
    def __init__(self, k8s: K8s, config: RotatorConfigs):
        self.__k8s = k8s
        self.__config = config

    def __init_logger(self) -> None:
        logging.basicConfig(
            level=LOG_LEVEL[self.__config.verbose],
            format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        )
        logging.debug(f"{logging_prefix()}  <user_args>: {self.__config.dict()}")

    @cached_property
    def nodes(self) -> t.List[V1Node]:
        nodes = self.__k8s.get_nodes(label_selector=self.__config.selector)
        return nodes

    def _node_drain(self, node: V1Node, pods: t.List[V1Pod]) -> dict:
        """
        1. cordon node
        2. evict every pod
        """
        not_evicted = {}
        node_name = node.metadata.name
        logging.debug(f"{logging_prefix()} k.cordon_node=<{node_name}>")
        self.__k8s.cordon_node(node_name)

        ev = []
        for pod in pods:
            r = self.__k8s.evict_pod(pod)
            if isinstance(r, V1Pod):
                ev.append(pod.metadata.name)
            if ev:
                not_evicted.update({node_name: ev})
        return not_evicted

    def drain_manual(self) -> dict:
        not_evicted_all_nodes = {}
        for node in self.nodes:
            node_name = node.metadata.name
            print(emoji.emojize(f":laptop: Node: <{node_name}>"))

            pods = self.__k8s.get_pods(node_name)
            pods_on_node_table(pods)

            proceed = confirm(f"drain node: <{node_name}>", node_name)
            if not proceed:
                logging.warning(f"{logging_prefix()}:  Won't Proceed on Node=<{node_name}>")
                return not_evicted_all_nodes
            not_evicted = self._node_drain(node, pods)
            not_evicted_all_nodes.update(not_evicted)

        return not_evicted_all_nodes

    def drain_node_chunks(self) -> dict:
        nodes = self.nodes.copy()
        chunk_size = drain_node_chunks_calc(len(nodes), self.__config.ratio)
        not_evicted_all_nodes = {}
        while nodes:
            step = nodes[:chunk_size]
            nodes = nodes[chunk_size:]
            for node in step:
                node_name = node.metadata.name
                print(emoji.emojize(f":laptop: Node: <{node_name}>"))
                pods = self.__k8s.get_pods(node_name)
                pods_on_node_table(pods)

                not_evicted = self._node_drain(node, pods)
                not_evicted_all_nodes.update(not_evicted)
            else:
                print(emoji.emojize(f":sleeping_face: sleeping <{self.__config.sleep}> seconds"))
                sleep(self.__config.sleep)

        return not_evicted

    def rotate(self):
        self.__init_logger()

        if self.__config.mode == "chunks":
            r = self.drain_node_chunks()

        elif self.__config.mode == "manual":
            r = self.drain_manual()

        print(json.dumps(r, indent=4))
