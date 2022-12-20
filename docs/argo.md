# argo

> Утилита для манипулирования состоянием Sync для argo в стиле Apps of Apps

```mermaid
graph TD
    A[__init__]
    A --> F[foo]
    A --> S[spam]

    F --> BAR[bar]
    F --> BAZ[baz]

    S --> EGGS[eggs]
    S --> BACON[bacon]
```

## Пример

```shell
pl-cli --tool argo --context ${ctx} --no-sync --sync-app 'bacon'
```

Последовательно выключит: `__init__`, `spam`, `bacon` и приложения за ним можно будет обслуживать. После работ следует вернуть все назад:

```shell
pl-cli --tool argo --context ${ctx} --sync --sync-app '__init__'
```

## [home](../README.md)
