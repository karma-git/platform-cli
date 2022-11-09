import argparse
import logging
import json
from time import sleep

from libs.others import (
    logging_prefix,
    k8s_owner_info,
    argo_instance,
    pod_to_deployment_name,
    confirm,
    sc_to_vsc,
    LOG_LEVEL,
    CRD_DICT,
    ROOT_ARGO_APP,
)
from libs.argo import ArgoApi, ArgoCRD
from libs.k8s import NxK8s


def cli():
    example_text = """
    python main.py --context sandbox -n loki --pvc storage-loki-0
    python main.py --context sandbox --sync
    """

    parser = argparse.ArgumentParser(
        description="CLI for migrate kubernetes stateful application data",
        epilog=example_text,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--context", help="Arg=(kubernetes context)", required=True)
    parser.add_argument("-n", "--namespace", help="Arg=(kubernetes namespace)")
    parser.add_argument("--pvc", help="Arg=(PersistenceVolumeClaim name)")
    parser.add_argument(
        "--sc", help="Arg=(StorageClassName)", default="ebs-gp3-ext4-eu-west-1b"
    )
    parser.add_argument(
        "--vs",
        help="Arg=(Backup VolumeSnapshot)",
        action="store_true",
        default=False,
    )
    # argo
    parser.add_argument(
        "--sync",
        help="Arg=(Enable AutoSync for sync-app)",
        action="store_true",
    )
    parser.add_argument(
        "--no-sync",
        help="Arg=(Disable AutoSync for sync-app)",
        action="store_false",
    )
    parser.add_argument(
        "--sync-app",
        help="Arg=(Enable AutoSync for app)",
        default="",
    )
    parser.add_argument(
        "--server",
        help="Arg=(argocd-server, eg platform.sandbox, rsd.prod)",
    )
    parser.add_argument(
        "--token",
        # help="Arg=(argocd_token)",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--generate-token",
        # help="Arg=(need login and password)"
        help=argparse.SUPPRESS,
        type=json.loads,
    )
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
    k = NxK8s(
        context=user_args.context,
        namespace=user_args.namespace,
        pvc=user_args.pvc,
        sc=user_args.sc,
    )

    # ArgoAPI
    """
    argo_server = f"argocd.{user_args.server}.nexters.team"

    if user_args.generate_token is not None:
        creds = user_args.generate_token
        token = ArgoApi.generate_bearer_token(
            server=argo_server, username=creds["username"], password=creds["password"]
        )
        print(f"<token={token}>")
        exit()

    a = ArgoApi(server=argo_server, token=user_args.token)
    """
    # ArgoCRD
    a = ArgoCRD(context=user_args.context)

    if user_args.sync_app:  # включаем/выключаем sync
        logging.info(
            f"{logging_prefix()}:  Argo-sync=<{user_args.sync},sync_app=<{user_args.sync_app}>>"
        )
        if user_args.sync:
            a.enable_autosync(user_args.sync_app)
            exit()
        elif not user_args.sync:
            argo_chain = a.app_of_apps_chain(user_args.sync_app)
            a.disable_autosync_chain(argo_chain)
            exit()
    if not user_args.sync_app:
        user_args.sync_app = ROOT_ARGO_APP

    # TODO: если есть комменты -> это отдельная функция, функция (10 стр); логически разные куски разносим на классы
    # TODO: расшарить общую функциональность
    # TODO: разделить кейсы

    # Step 1: Получаем на вход имя `pvc`, находим `bound` pod, если такого нет - выкидываем exception
    origin_pvc = k.get_pvc(user_args.pvc)
    vsc = sc_to_vsc(user_args.sc)
    # Step 3: Создаем pvc `<name>-backup`, если его еще нет.
    backup_pvc = k.create_pvc(f"{user_args.pvc}-backup", origin_pvc)

    # Step 4: C помощью pod-а находим его owner-а `(sts | deployment | crd)`
    # Step 5: На owner-е pod-а будет аннотация `argo-instance`, через argo api выстраиваем цепочку зависимости от cluster-init до нужного application, последовательно выключаем autosync
    # Step 6: Скейлим owner-а в 0 реплик
    logging.warning(f"{logging_prefix()}:  Step2(PVC-POD)")
    pod_metadata = k.pod_pvc_relationship()  # FIXME
    if pod_metadata is not None:
        owner = k8s_owner_info(pod_metadata)

        # NOTE: k8s объект является создателем пода, если:
        #  1) над ним нету более высокоуровневой абстракции
        #  2) он создан приложением argo
        obj = owner["kind"]

        if obj == "StatefulSet":
            sts = k.get_sts(owner["name"])
            owner, argo_app = k8s_owner_info(sts.metadata), argo_instance(sts.metadata)
            logging.warning(
                f"{logging_prefix()}:  Step3(STS): owner=<{owner}>,argo_app=<{argo_app}>"
            )
            # STS владелец пода
            if owner is None and argo_app is not None:
                # выключаем autosync
                argo_chain = a.app_of_apps_chain(argo_app)
                a.disable_autosync_chain(argo_chain)
                # скейлим нагрузку
                k.scale_sts(sts.metadata.name)
                # NOTE: need to recreate sts due to update sc in pvcTemplate
                sleep_time = 30  # sec
                logging.warning(
                    f"{logging_prefix()}:  Step3(STS): sleep {sleep_time} sec>"
                )
                sleep(sleep_time)
                k.delete_sts(sts.metadata.name)

            # над STS есть более высокоуровневая абcтракция
            elif owner is not None and argo_app is not None:
                # ищем более высокуровневого овнера
                crd_owner = k8s_owner_info(sts.metadata)
                crd_owner.pop("kind")
                crd = k.get_crd(**crd_owner)
                argo_app = argo_instance(crd["metadata"])

                # скейлим нагрузку
                argo_chain = a.app_of_apps_chain(argo_app)
                a.disable_autosync_chain(argo_chain)

                k.scale_crd(**crd_owner)

        elif obj == "ReplicaSet":
            deploy_name = pod_to_deployment_name(pod_metadata.name)
            deploy = k.get_deploy(deploy_name)
            owner, argo_app = k8s_owner_info(deploy.metadata), argo_instance(
                deploy.metadata
            )
            logging.debug(
                f"{logging_prefix()}:  Step3(D): owner=<{owner}>,argo_app=<{argo_app}>"
            )
            if owner is None and argo_app is not None:
                # выключаем autosync
                argo_chain = a.app_of_apps_chain(argo_app)
                a.disable_autosync_chain(argo_chain)
                # скейлим нагрузку
                k.scale_deploy(deploy.metadata.name)
            elif owner is not None and argo_app is not None:
                # ищем более высокуровневого овнера
                crd_owner = k8s_owner_info(deploy.metadata)
                crd_owner.pop("kind")
                crd = k.get_crd(**crd_owner)
                argo_app = argo_instance(crd["metadata"])

                # скейлим нагрузку
                argo_chain = a.app_of_apps_chain(argo_app)
                a.disable_autosync_chain(argo_chain)

                k.scale_crd(**crd_owner)

        elif obj in list(CRD_DICT.keys()):
            logging.error(f"{logging_prefix()}:  Step3(CRDD)=<PLACEHOLDER>")
        else:
            logging.error(
                f"{logging_prefix()}:  pod=<{pod_metadata.name} not match owners>"
            )
    else:
        logging.warning(f"{logging_prefix()}:  SKIP: Step2(PVC-POD)")

    # создаем снэпшот
    if user_args.vs:
        logging.error(
            f"{logging_prefix()}: Snapshot is working only with CSI StorageClasses"
        )
        k.create_snapshot(pvc_name=user_args.pvc, vsc=vsc)
        proceed = confirm("Step 6, Snapshot is ready?", 6)
        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 8")
            exit()

    # Step 7: Создаем job, который будет выполнять миграцию данных (аналог pv-migrate)
    logging.warning(f"{logging_prefix()}:  Step7(MIGRATE)")
    migrate = k.migrate_job(src_pvc=user_args.pvc, dest_pvc=f"{user_args.pvc}-backup")

    # Step 8: После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
    logging.warning(f"{logging_prefix()}:  Step8(Delete Origin PVC)")
    proceed = confirm("Step 8, Delete Origin PVC", 8)
    if not proceed:
        logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 8")
        exit()

    origin_pvc = k.delete_pvc(pvc_name=user_args.pvc)

    # Step 9: Пересоздаем `origin pvc`, но с правильным `StorageClass`.
    logging.warning(f"{logging_prefix()}:  Step9(Recreate Origin PVC)")
    if not proceed:
        logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 9")
        exit()
    origin_pvc = k.create_pvc(pvc_name=user_args.pvc, manifest=origin_pvc)

    # Step 10: Выполняем пункты 8,9 `visa versa`
    logging.warning(f"{logging_prefix()}:  Step10(MIGRATE BACKUP->Origin)")
    migrate = k.migrate_job(src_pvc=f"{user_args.pvc}-backup", dest_pvc=user_args.pvc)

    # Step 11: Делаем Sync (`cluster-init | target application`)
    proceed = confirm("Step 11,Enable AutoSync", 11)
    if not proceed:
        logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 11")
        exit()
    logging.warning(f"{logging_prefix()}:  Step11(Enable AutoSync)")
    a.enable_autosync(user_args.sync_app)

    # Step 12: Удаляем pvc `<name>-backup` (SnapshotCRD)
    proceed = confirm("Step 12,Delete Backup PVC", 12)
    if not proceed:
        logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 12")
        exit()
    logging.warning(f"{logging_prefix()}:  Step12(Delete Backup PVC)")
    backup_pvc = k.delete_pvc(pvc_name=f"{user_args.pvc}-backup")


def test():
    # cli args, logging
    user_args = cli()

    logging.basicConfig(
        level=LOG_LEVEL[user_args.verbose],
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    logging.info(f"{logging_prefix()}  <user_args>: {user_args}")

    # Kubernetes
    k = NxK8s(
        context=user_args.context,
        namespace=user_args.namespace,
        pvc=user_args.pvc,
        sc=user_args.sc,
    )
    k.create_snapshot(user_args.pvc, "ebs-gp3-ext4")
    # origin_pvc = k.get_pvc(user_args.pvc)


if __name__ == "__main__":
    main()
    # test()
