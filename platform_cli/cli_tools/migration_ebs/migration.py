import logging
from functools import cached_property
from typing import Optional, Any, Tuple

from kubernetes.client import V1PersistentVolumeClaim, V1ObjectMeta, V1Job

from platform_cli.cli_tools.migration_ebs.models.migration_ebs_settings import MigrationEbsConfigs
from platform_cli.cli_tools.migration_ebs.services.rs_scaler import RsScalerService
from platform_cli.cli_tools.migration_ebs.services.sts_scaler import StsScalerService
from platform_cli.libs.others import (
    logging_prefix,
    k8s_owner_info,
    sc_to_vsc,
    LOG_LEVEL,
    ROOT_ARGO_APP, CRD_DICT, confirm,
)
from platform_cli.libs.argo import ArgoCRD
from platform_cli.libs.k8s import K8s


class MigrationEbs:

    def __init__(self, k8s: K8s, argo_crd: ArgoCRD, config: MigrationEbsConfigs):
        self.__k8s = k8s
        self.__config = config
        self.__argo_crd = argo_crd

    def __init_logger(self) -> None:
        logging.basicConfig(
            level=LOG_LEVEL[self.__config.verbose],
            format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        )
        logging.debug(f"{logging_prefix()}  <user_args>: {self.__config.dict()}")

    def toggle_sync(self) -> None:
        if self.__config.sync_app:  # включаем/выключаем sync
            logging.info(
                f"{logging_prefix()}:  Argo-sync=<{self.__config.sync},sync_app=<{self.__config.sync_app}>>"
            )
            if self.__config.sync:
                self.__argo_crd.enable_autosync(self.__config.sync_app)
                exit()
            elif not self.__config.sync:
                argo_chain = a.app_of_apps_chain(self.__config.sync_app)
                self.__argo_crd.disable_autosync_chain(argo_chain)
                exit()
        if not self.__config.sync_app:
            self.__config.sync_app = ROOT_ARGO_APP

    @cached_property
    def origin_pvc(self) -> V1PersistentVolumeClaim:
        # Step 1: Получаем на вход имя `pvc`
        origin_pvc = self.__k8s.get_pvc(self.__config.pvc)
        return origin_pvc

    @cached_property
    def vsc_from_sc(self) -> str:
        vsc = sc_to_vsc(self.__config.sc)
        return vsc

    def create_backup_pvc(self) -> V1PersistentVolumeClaim:
        # Step 3: Создаем pvc `<name>-backup`, если его еще нет.
        backup_pvc = self.__k8s.create_pvc(
            f"{self.__config.pvc}-backup", self.origin_pvc
        )

        return backup_pvc

    @cached_property
    def pod_metadata(self) -> V1ObjectMeta:
        # Step 2
        logging.warning(f"{logging_prefix()}:  Step2(PVC-POD)")
        pod_metadata = self.__k8s.pod_pvc_relationship()  # FIXME

        return pod_metadata

    @cached_property
    def pod_owner(self) -> Optional[dict]:
        # Step 4: C помощью pod-а находим его owner-а `(sts | deployment | crd)`
        owner = k8s_owner_info(self.pod_metadata)
        return owner

    @cached_property
    def pod_owner_kind(self) -> str:
        kind = self.pod_owner["kind"]
        return kind

    def scale_if_sts(self) -> None:
        if self.pod_owner_kind == "StatefulSet":
            sts_scaler = StsScalerService(self.__k8s, self.__argo_crd, self.pod_owner["name"])
            sts_scaler.scale_sts()

    def scale_if_rs(self) -> None:
        if self.pod_owner_kind == "ReplicaSet":
            rs_scaler = RsScalerService(self.__k8s, self.__argo_crd, self.pod_metadata)
            rs_scaler.scale_rs()

    def __if_is_incorrect_owner_type(self) -> None:
        if self.pod_owner_kind in list(CRD_DICT.keys()):
            logging.error(f"{logging_prefix()}:  Step3(CRDD)=<PLACEHOLDER>")
        else:
            logging.error(
                f"{logging_prefix()}:  pod=<{self.pod_metadata.name} not match owners>"
            )

    def create_snapshot(self) -> None:
        if self.__config.vs:

            log_message = f"{logging_prefix()}: Snapshot is working only with CSI StorageClasses"
            logging.error(log_message)

            self.__k8s.create_snapshot(pvc_name=self.__config.pvc, vsc=self.vsc_from_sc)
            proceed = confirm("Step 6, Snapshot is ready?", "6")

            if not proceed:
                logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 8")
                exit()

    def scale_owner(self) -> None:
        # Step 4: C помощью pod-а находим его owner-а `(sts | deployment | crd)`
        # Step 5: На owner-е pod-а будет аннотация `argo-instance`, через argo api выстраиваем цепочку зависимости
        # от cluster-init до нужного application, последовательно выключаем autosync Step 6: Скейлим owner-а в 0 реплик
        if self.pod_metadata is not None:
            self.scale_if_sts()
            self.scale_if_rs()
            self.__if_is_incorrect_owner_type()
        else:
            logging.warning(f"{logging_prefix()}:  SKIP: Step2(PVC-POD)")
        # создаем снэпшот
        self.create_snapshot()

    def create_migration_job(self) -> None:
        # Step 7: Создаем job, который будет выполнять миграцию данных (аналог pv-migrate)
        logging.warning(f"{logging_prefix()}:  Step7(MIGRATE)")
        self.__k8s.migrate_job(
            src_pvc=self.__config.pvc, dest_pvc=f"{self.__config.pvc}-backup"
        )

    def watch_job(self) -> Tuple[Any, bool]:
        # Step 8: После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
        logging.warning(f"{logging_prefix()}:  Step8(Delete Origin PVC)")
        proceed = confirm("Step 8, Delete Origin PVC", "8")

        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 8")
            exit()

        origin_pvc = self.__k8s.delete_pvc(pvc_name=self.__config.pvc)
        return origin_pvc, proceed

    def recreate_pvc(self, origin_pvc: any, proceed: bool) -> None:
        # Step 9: Пересоздаем `origin pvc`, но с правильным `StorageClass`.
        logging.warning(f"{logging_prefix()}:  Step9(Recreate Origin PVC)")

        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 9")
            exit()

        self.__k8s.create_pvc(pvc_name=self.__config.pvc, manifest=origin_pvc)

    def migrate_backup(self) -> V1Job:
        # Step 10: Выполняем пункты 8,9 `visa versa`
        logging.warning(f"{logging_prefix()}:  Step10(MIGRATE BACKUP->Origin)")
        migrate = self.__k8s.migrate_job(src_pvc=f"{self.__config.pvc}-backup", dest_pvc=self.__config.pvc)
        return migrate

    def create_sync(self) -> None:
        # Step 11: Делаем Sync (`cluster-init | target application`)
        proceed = confirm("Step 11,Enable AutoSync", "11")

        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 11")
            exit()

        logging.warning(f"{logging_prefix()}:  Step11(Enable AutoSync)")
        self.__argo_crd.enable_autosync(self.__config.sync_app)

    def delete_pvc_backup(self) -> Any:
        # Step 12: Удаляем pvc `<name>-backup` (SnapshotCRD)
        proceed = confirm("Step 12,Delete Backup PVC", "12")

        if not proceed:
            logging.warning(f"{logging_prefix()}:  Won't Proceed on Step 12")
            exit()

        logging.warning(f"{logging_prefix()}:  Step12(Delete Backup PVC)")
        backup_pvc = self.__k8s.delete_pvc(pvc_name=f"{self.__config.pvc}-backup")

        return backup_pvc

    def migrate(self):
        self.__init_logger()
        self.create_backup_pvc()
        # Step 4: C помощью pod-а находим его owner-а `(sts | deployment | crd)`
        # Step 5: На owner-е pod-а будет аннотация `argo-instance`, через argo api выстраиваем цепочку зависимости
        # от cluster-init до нужного application, последовательно выключаем autosync
        # Step 6: Скейлим owner-а в 0 реплик
        self.scale_owner()
        # Step 7: Создаем job, который будет выполнять миграцию данных (аналог pv-migrate)
        self.create_migration_job()
        # Step 8: После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
        origin_pvc, proceed = self.watch_job()
        # Step 9: Пересоздаем `origin pvc`, но с правильным `StorageClass`.
        self.recreate_pvc(origin_pvc, proceed)
        # Step 10: Выполняем пункты 8,9 `visa versa`
        self.migrate_backup()
        # Step 11: Делаем Sync (`cluster-init | target application`)
        self.create_sync()
        # Step 12: Удаляем pvc `<name>-backup` (SnapshotCRD)
        self.delete_pvc_backup()
