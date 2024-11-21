#!/bin/sh
# Copyright (C) SciLifeLab 2024.  MIT licence (https://opensource.org/license/mit).
# Usage: ./upload.sh

dirname=`uname -n`.`date '+%s'`
echo Dir name: $dirname
# DDS_CLI_ENV and DDS_CLI_PROJECT are set in the Kubernetes environment
$HOME/.dds/bin/dds data put -nt 32 -p $DDS_CLI_PROJECT -s $HOME/upload -d $dirname
