#!/bin/bash

# Abort the script if any command fails
set -e


# See README.md for how to get these values

TAG="0.0.$GITHUB_RUN_NUMBER" # Initially set this to "0.0.1", and then update to come from Github Actions
MACHINE_ID=$MACHINE_ID  # Initially hard code this to your machine ID for the first deploy, e.g. "e2865c22a34548", and then update to use whatever env var is in Github Actions
APP_NAME="wheretolive-a32cd"

fly deploy

# docker build -t registry.fly.io/$APP_NAME:deployment-$TAG . --platform linux/amd64
# docker push registry.fly.io/$APP_NAME:deployment-$TAG
# fly machine update $MACHINE_ID --yes --image registry.fly.io/$APP_NAME:deployment-$TAG --schedule=daily --metadata fly_process_group=worker

MACHINE_ID=$(fly machine list --json | jq -r -c '.[] | select(.config | .metadata | .fly_process_group | contains("worker")) | .id')
ly machine update $MACHINE_ID --yes --schedule=daily --metadata fly_process_group=worker