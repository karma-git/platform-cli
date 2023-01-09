import inspect
import json
import logging
from typing import List, Union

import emoji
from kubernetes.client.models import V1ObjectMeta, V1OwnerReference

STORAGE_CLASS = "ebs-gp3-ext4-eu-west-1b"

LOG_LEVEL = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
}


CRD_DICT = {
    # spec.names.prural
    "Alertmanager": "alertmanagers",
    "Prometheus": "prometheuses",
}

ROOT_ARGO_APP = "cluster-init"


def logging_prefix() -> str:
    """
    2022-11-03 14:51:47,617 INFO root | [old_migration.py | logging_prefix]:  <user_args>: Namespace(context='sandbox', namespace=None, pvc=None, sync=True, verbose='INFO')
    """
    ctx = inspect.stack()[1]
    return f"[{ctx.filename.split('/')[-1]} | {ctx.function}]:"


def confirm(text: str, log: str) -> bool:
    """
    doc: https://click.palletsprojects.com/en/7.x/prompts/#confirmation-prompts
    src: https://github.com/pallets/click/blob/c65c6ad18471448c0fcc59ef53088787288c02cc/src/click/termui.py#L192
    """
    while True:
        try:
            value = input(emoji.emojize(f":thinking_face: {text}: y/n? "))
            if value in ("y", "yes"):
                rv = True
            elif value in ("n", "no"):
                rv = False
            else:
                logging.error(
                    f"{logging_prefix()}  Step=<{log}>Error: invalid input={value}"
                )
                continue
            break
        except (KeyboardInterrupt, EOFError):
            logging.info(
                    f"{logging_prefix()}  Interrupted Step=<{log}>"
                )
            print(emoji.emojize(f":waving_hand: bye"))
            exit()
            # raise Exception(f"Interrupted Step=<{log}>")
    return rv


def save_request_json(data: dict, file_name: str = "tmp") -> None:
    with open(f"{file_name}.json", "w") as outfile:
        json.dump(data, outfile)


def dict_to_metadata(data: Union[dict, V1ObjectMeta]) -> V1ObjectMeta:
    if isinstance(data, dict):
        return V1ObjectMeta(data)
    elif isinstance(data, V1ObjectMeta):
        return data
    else:
        logging.error(f"{logging_prefix()}  object=<{type(data)} is not supposed>")


def sc_to_vsc(sc: str) -> str:
    """
    get ebs-gp3-ext4-eu-west-1b
    return ebs-gp3-ext4
    """
    sc_list = sc.split("-")
    return "-".join(sc_list[:3])


def k8s_owner_info(data: V1ObjectMeta) -> dict:
    """
    return object owner info, or None if the object has no owner
    """
    data = dict_to_metadata(data)
    owner: List[V1OwnerReference] = data.owner_references
    nil = {
        "name": None,
        "kind": None,
        "group": None,
        "version": None,
        "plural": None,
    }
    if owner is None:
        return nil
    elif len(owner) == 0:
        return nil
    elif len(owner) != 1:
        logging.warning(
            f"{logging_prefix()}  object=<{data.name} has more then 1 owner>"
        )

    owner = data.owner_references[0]

    api = owner.api_version.split("/")

    result = {
        "name": owner.name,
        "kind": owner.kind,
        "group": api[0],
        "version": api[1],
        "plural": CRD_DICT.get(owner.kind),
    }
    return result


def argo_instance(data: V1ObjectMeta) -> Union[str, None]:
    """
    return name of the argo application which created the object, or None if the object is not created via argo
    """
    if isinstance(data, dict):
        return data["labels"].get("argocd.argoproj.io/instance")
    elif isinstance(data, V1ObjectMeta):
        return data.labels.get("argocd.argoproj.io/instance")


def pod_to_deployment_name(pod_name: str) -> str:
    """
    arg: argocd-redis-66d94b965-9rh5m
    return: argocd-redis
    """
    pod_name_list = pod_name.split("-")
    pod_name_list.pop(-1)  # rs-hash
    pod_name_list.pop(-1)  # pod-template-hash
    return "-".join(pod_name_list)
