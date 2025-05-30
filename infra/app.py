#!/usr/bin/env python3
import os
import aws_cdk as cdk
from .infra_stack import DjangoStack

app = cdk.App()

DjangoStack(app, "DjangoStack",
    env=cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    )
)

app.synth()
