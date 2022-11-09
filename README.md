[SERVER-3968](https://studionx.atlassian.net/browse/SERVER-3968)

# plan

> с соблюдением консистентности данных

1. [x] Получаем на вход имя `pvc`, находим `bound` pod, если такого нет - выкидываем exception
2. (опционально - создаем SnapshotCRD)
3. [x] Создаем pvc `<name>-backup`, если его еще нет.
4. [x] C помощью pod-а находим его owner-а `(sts | deployment | crd)`
5. [x] На owner-е pod-а будет аннотация `argo-instance`, через argo api выстраиваем цепочку зависимости от cluster-init до нужного application, последовательно выключаем autosync
6. [x] Скейлим owner-а в 0 реплик
7. [x] Создаем job, который будет выполнять миграцию данных (аналог `pv-migrate`)
8. После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
9. Пересоздаем `origin pvc`, но с правильным `StorageClass`.
10. Выполняем пункты 8,9 `visa versa`
11. Делаем Sync (`cluster-init | target application`)
12. Удаляем pvc `<name>-backup` (SnapshotCRD)

<details>
<summary>Old Plan</summary>

```
# STEP 1 - scale workload to 0

# STEP 2 - create clone pvc

# STEP 3 copy data from original pvc, to backup pvc

# STEP 4 delete original pvc

# STEP 5 crete new one with proper storage class

# STEP 6 copy data from backup pvc to orinal

# STEP 7 delete backup pvc

# STEP 8 return workloads replicas
```

</details>

> без
1. Получаем на вход имя `pvc`, находим `bound` pod, если такого нет - выкидываем exception
2. Создаем pvc `<name>-backup`, если его еще нет.
3. Создаем job, ассайним на node, где бежит pod нашего origin pvc, который будет выполнять миграцию данных (аналог `pv-migrate`)
4. После создания делаем watch за job-ом, в случае если выполниться успешно - `удаляем origin pvc`
5. Создаем job, ассайним на node, где бежит pod нашего origin pvc, который будет выполнять миграцию данных (аналог `pv-migrate`) `visa versa`

# examples
AM
```shell
python main.py --context sandbox -n prometheus-stack -v INFO --pvc alertmanager-prometheus-stack-kube-prom-alertmanager-db-alertmanager-prometheus-stack-kube-prom-alertmanager-0
```

PROM
```
python main.py --context sandbox -n prometheus-stack -v INFO --pvc  prometheus-prometheus-stack-kube-prom-prometheus-db-prometheus-prometheus-stack-kube-prom-prometheus-0
```

LOKI
```
python main.py --context sandbox -n loki -v INFO  --pvc storage-loki-0
```

WORDPRESS
```
python main.py --context sandbox -n env-ahorbach -v INFO --pvc word-press-wordpress
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pv-migrate-aacea-rsync
  namespace: env-ahorbach
  uid: 0848da74-0d25-4c7b-9506-2b3f9d761578
  resourceVersion: '266432170'
  generation: 1
  creationTimestamp: '2022-11-06T10:00:58Z'
  labels:
    controller-uid: 0848da74-0d25-4c7b-9506-2b3f9d761578
    job-name: pv-migrate-aacea-rsync
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: >
      {"apiVersion":"batch/v1","kind":"Job","metadata":{"annotations":{},"name":"pv-migrate-aacea-rsync","namespace":"env-ahorbach"},"spec":{"backoffLimit":0,"completions":1,"parallelism":1,"suspend":false,"template":{"spec":{"containers":[{"command":["sh","-c","n=0\nrc=1\nretries=10\nuntil
      [ \"$n\" -ge \"$retries\" ]\ndo\n  rsync -azv
      --info=progress2,misc0,flist0 --no-inc-recursive -e \"ssh -o
      StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o
      ConnectTimeout=5\" /source// /dest// \u0026\u0026 rc=0 \u0026\u0026
      break\n  n=$((n+1))\n  echo \"rsync attempt $n/10 failed, waiting 5
      seconds before trying again\"\n  sleep 5\ndone\n\nif [ $rc -ne 0 ];
      then\n  echo \"rsync job failed after $retries retries\"\nfi\nexit
      $rc\n"],"image":"docker.io/utkuozdemir/pv-migrate-rsync:1.0.0","imagePullPolicy":"IfNotPresent","name":"rsync","resources":{},"securityContext":{},"volumeMounts":[{"mountPath":"/source","name":"vol-0","readOnly":true},{"mountPath":"/dest","name":"vol-1"}]}],"restartPolicy":"Never","volumes":[{"name":"vol-0","persistentVolumeClaim":{"claimName":"word-press-wordpress","readOnly":true}},{"name":"vol-1","persistentVolumeClaim":{"claimName":"word-press-wordpress-backup"}}]}}}}
  managedFields:
    - manager: kubectl-client-side-apply
      operation: Update
      apiVersion: batch/v1
      time: '2022-11-06T10:00:58Z'
      fieldsType: FieldsV1
      fieldsV1:
        f:metadata:
          f:annotations:
            .: {}
            f:kubectl.kubernetes.io/last-applied-configuration: {}
        f:spec:
          f:backoffLimit: {}
          f:completionMode: {}
          f:completions: {}
          f:parallelism: {}
          f:suspend: {}
          f:template:
            f:spec:
              f:containers:
                k:{"name":"rsync"}:
                  .: {}
                  f:command: {}
                  f:image: {}
                  f:imagePullPolicy: {}
                  f:name: {}
                  f:resources: {}
                  f:securityContext: {}
                  f:terminationMessagePath: {}
                  f:terminationMessagePolicy: {}
                  f:volumeMounts:
                    .: {}
                    k:{"mountPath":"/dest"}:
                      .: {}
                      f:mountPath: {}
                      f:name: {}
                    k:{"mountPath":"/source"}:
                      .: {}
                      f:mountPath: {}
                      f:name: {}
                      f:readOnly: {}
              f:dnsPolicy: {}
              f:restartPolicy: {}
              f:schedulerName: {}
              f:securityContext: {}
              f:terminationGracePeriodSeconds: {}
              f:volumes:
                .: {}
                k:{"name":"vol-0"}:
                  .: {}
                  f:name: {}
                  f:persistentVolumeClaim:
                    .: {}
                    f:claimName: {}
                    f:readOnly: {}
                k:{"name":"vol-1"}:
                  .: {}
                  f:name: {}
                  f:persistentVolumeClaim:
                    .: {}
                    f:claimName: {}
    - manager: kube-controller-manager
      operation: Update
      apiVersion: batch/v1
      time: '2022-11-06T10:01:14Z'
      fieldsType: FieldsV1
      fieldsV1:
        f:status:
          f:completionTime: {}
          f:conditions: {}
          f:startTime: {}
          f:succeeded: {}
      subresource: status
  selfLink: /apis/batch/v1/namespaces/env-ahorbach/jobs/pv-migrate-aacea-rsync
status:
  conditions:
    - type: Complete
      status: 'True'
      lastProbeTime: '2022-11-06T10:01:14Z'
      lastTransitionTime: '2022-11-06T10:01:14Z'
  startTime: '2022-11-06T10:00:58Z'
  completionTime: '2022-11-06T10:01:14Z'
  succeeded: 1
spec:
  parallelism: 1
  completions: 1
  backoffLimit: 0
  selector:
    matchLabels:
      controller-uid: 0848da74-0d25-4c7b-9506-2b3f9d761578
  template:
    metadata:
      creationTimestamp: null
      labels:
        controller-uid: 0848da74-0d25-4c7b-9506-2b3f9d761578
        job-name: pv-migrate-aacea-rsync
    spec:
      volumes:
        - name: vol-0
          persistentVolumeClaim:
            claimName: word-press-wordpress
            readOnly: true
        - name: vol-1
          persistentVolumeClaim:
            claimName: word-press-wordpress-backup
      containers:
        - name: rsync
          image: docker.io/utkuozdemir/pv-migrate-rsync:1.0.0
          command:
            - sh
            - '-c'
            - |
              n=0
              rc=1
              retries=10
              until [ "$n" -ge "$retries" ]
              do
                rsync -azv --info=progress2,misc0,flist0 --no-inc-recursive -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5" /source// /dest// && rc=0 && break
                n=$((n+1))
                echo "rsync attempt $n/10 failed, waiting 5 seconds before trying again"
                sleep 5
              done

              if [ $rc -ne 0 ]; then
                echo "rsync job failed after $retries retries"
              fi
              exit $rc
          resources: {}
          volumeMounts:
            - name: vol-0
              readOnly: true
              mountPath: /source
            - name: vol-1
              mountPath: /dest
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
          imagePullPolicy: IfNotPresent
          securityContext: {}
      restartPolicy: Never
      terminationGracePeriodSeconds: 30
      dnsPolicy: ClusterFirst
      securityContext: {}
      schedulerName: default-scheduler
  completionMode: NonIndexed
  suspend: false
```

> IDEA
> 1. Snapshot CRD: смотреть глазами, а дальнейший поток блочить через input()
> 2. Аналогично для migrate Job и удаления
