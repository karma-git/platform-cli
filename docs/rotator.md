# migrate_ebs

> Утилита для ротации нод в кластере

1. Получаем на вход имя `selector`, по нему находим ноды, которые нужно сротировать
2. Ставим на ноду `cordon`
3. Для pod-ов, не созданных `DaemonSet`-ом делаем eviction
<!-- TODO: should we increase Provisioner resource before rotation? -->
<!-- TODO: retry to evict not_evicted pods -->
## details


### mode chunks

В этом моде `drain` каждой последующей ноды выполняется автоматически, имеется 2 параметра влияющие на скорость:

- `ratio` (float) в диапазоне от 0 до 1, определяет % нод, которые попадут в один чанк и будут сдрейнены последовательно без задержки на `sleep`
- `sleep` - сколько секунд ждать между чанками

### mode manual

В этом моде `drain` каждой новой ноды нужно апрувить вручную

## Пример

```shell
pl-cli --tool rotator --context $ctx -l 'node.kubernetes.io/owner=project' -v INFO
```

## [home](../README.md)
