#!/usr/bin/env python3
import aws_cdk as cdk
from .infra_stack import DjangoStack


app = cdk.App()
DjangoStack(app, "DjangoStack")
app.synth()
