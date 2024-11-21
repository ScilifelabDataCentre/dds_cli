#!/bin/sh
# Copyright (C) 2024 SciLifeLab.  MIT licence (https://opensource.org/license/mit).
# Usage: ./set-up-kubernetes-load-testing.sh <cluster> <namespace>

cluster=$1
namespace=$2

if [ z$1 = z ]; then
  echo "Usage: $0 <cluster> <namespace>"
  exit -1
fi

yq .data.dds_cli_token=\"`base64 -i $HOME/.dds_cli_token`\" <dds-cli-token.yaml.in | \
  kubeseal --context $cluster -n $namespace | \
  kubectl --context $cluster -n $namespace apply -f -
