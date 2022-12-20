# migrate_ebs

> Утилита для изменения StorageClass для PVC

1. Получаем на вход имя `pvc`, находим `bound` pod, если такого нет - выкидываем exception
2. Создаем pvc `<name>-backup`, если его еще нет.
3. C помощью pod-а находим его owner-а `(sts | deployment | crd)`
4. На owner-е pod-а будет аннотация `argo-instance`, через argo api выстраиваем цепочку зависимости от root application до нужного application, последовательно выключаем autosync.
5. Скейлим owner-а в 0 реплик
6. Создаем job, который будет выполнять миграцию данных (аналог [pv-migrate](https://github.com/utkuozdemir/pv-migrate))
7. После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
8. Пересоздаем `origin pvc`, но с правильным `StorageClass`.
9.  Выполняем пункты 8,9 `visa versa`
10. Делаем Sync (`cluster-init | target application`)
11. Удаляем pvc `<name>-backup` (SnapshotCRD)

## Пример

```shell
pl-cli --tool migration-ebs --context $ctx -n $ns --pvc $pvc --sc "gp3" -v INF
```

## [home](../README.md)
