#!/bin/bash

KUBERNETES_CONTEXT=$1;
KUBERNETES_NAMESPACE=$2;
PVC_NAME=$3; shift
APPS_OF_APPS_GRAPH=("$@")

echo "TRACE(STEP 2):    <KUBERNETES_CONTEXT=${KUBERNETES_CONTEXT}>,KUBERNETES_NAMESPACE=${KUBERNETES_NAMESPACE},PVC_NAME=${PVC_NAME}"

# last_idx=$(( ${#APPS_OF_APPS_GRAPH[@]} - 1 ))
# arg2=${APPS_OF_APPS_GRAPH[$last_idx]}
# unset APPS_OF_APPS_GRAPH[$last_idx]

# KUBERNETES_CONTEXT=$1
# APPS_OF_APPS_GRAPH=("${!2}")

echo "STEP 1: Disabling ArgoCD AutoSync"

# for argo_app in ${APPS_OF_APPS_GRAPH[@]}; do
#   echo "TRACE:    Disabling AutoSync for <application=${argo_app}>"
#   kubectl --context ${KUBERNETES_CONTEXT} -n argocd \
#     patch application ${argo_app} \
#      --patch '{"spec": {"syncPolicy": {}}}' \
#      --type=merge
# done

echo "STEP 2: scale Statefull App in 0 replicas"

pods_list=$(kubectl --context ${KUBERNETES_CONTEXT} -n ${KUBERNETES_NAMESPACE} get po -o json | tee tmp.json > /dev/null 2>&1 )

pvc_pod_name=$(
  jq -r --arg PVC_NAME $PVC_NAME '
    .items[]
    | select(.spec.volumes[].persistentVolumeClaim.claimName==$PVC_NAME)
    | .metadata.name' tmp.json
)

# pvc_pod_name=$(kubectl --context ${KUBERNETES_CONTEXT} -n ${KUBERNETES_NAMESPACE} get po -o json | jq -r --arg PVC_NAME $PVC_NAME '.items[] | select(.spec.volumes[].persistentVolumeClaim.claimName==$PVC_NAME) | .metadata.name')

echo "TRACE(STEP 2):    <pod_name=${pvc_pod_name}>"

pvc_pod_abstraction=$(
  kubectl --context ${KUBERNETES_CONTEXT} -n ${KUBERNETES_NAMESPACE} \
  get po ${pvc_pod_name} -o json \
    | jq -r ".metadata.ownerReferences[0].kind" )

echo "TRACE(STEP 2):    <pvc_pod_abstraction=${pvc_pod_abstraction}>"
