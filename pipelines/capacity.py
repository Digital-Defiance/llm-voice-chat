import os
import asyncio
import subprocess
from pathlib import Path

import asyncio
from contextlib import contextmanager
from typing import Literal
from prefect import flow, serve, get_run_logger, task, variables
from prefect.runner.storage import GitRepository
import boto3
from prefect_aws import AwsCredentials
import os

aws_credentials_block = AwsCredentials.load("spot")

os.environ["REGION_NAME"] = aws_credentials_block.region_name
os.environ["AWS_ACCESS_KEY_ID"] = aws_credentials_block.aws_access_key_id
os.environ["AWS_SECRET_ACCESS_KEY"] = aws_credentials_block.aws_secret_access_key.get_secret_value()


@task
def get_client():
    return boto3.client('autoscaling')
    

def set_capacity(client, capacity: int) -> None:
    logger = get_run_logger()
    response = client.update_auto_scaling_group(
        AutoScalingGroupName='Infra-ECS-Cluster-spot-gpu-2-d30de970-ECSAutoScalingGroup-Vif1pCjC51Hq',
        DesiredCapacity = capacity,
        MaxSize=1,
        MinSize=0,
    )

    print(response)


@flow
def main(capacity: int):
    logger = get_run_logger()
    client = get_client()
    set_capacity(client, capacity)


if __name__ == "__main__":

    git_repo = GitRepository(
        url="https://github.com/Digital-Defiance/llm-voice-chat.git",
        branch = "main",
    )

    main_flow = main.from_source(
        entrypoint="pipelines/capacity.py:main",
        source=git_repo,
    )

    main_flow.deploy(
        name="change-scaling-capacity",
        work_pool_name = "workpool-prefect",
    )