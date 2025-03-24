#!/bin/bash

export PYTHONPATH="/fastapi_app/src:$PYTHONPATH"

if [[ "${1}" == "celery" ]]; then
  celery --app=src.tasks.tasks:celery worker -l INFO
elif [[ "${1}" == "flower" ]]; then
  celery --app=src.tasks.tasks:celery flower
fi
