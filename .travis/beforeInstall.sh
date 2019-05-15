#!/usr/bin/env bash

if [[ ${WR_TEST} = "yes" || ${WOMBAT_TEST} == "yes" ]]; then
    sudo sysctl kernel.unprivileged_userns_clone=1
fi
