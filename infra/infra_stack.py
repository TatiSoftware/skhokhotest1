from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_secretsmanager as sm,
)
from constructs import Construct

class DjangoStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # -------------------------------
        # VPC spanning 2 AZs with public and private subnets
        # Adds an S3 Gateway Endpoint for secure private access to S3
        # -------------------------------
        vpc = ec2.Vpc(self, "AppVpc",
            max_azs=2,
            gateway_endpoints={
                "S3": ec2.GatewayVpcEndpointOptions(
                    service=ec2.GatewayVpcEndpointAwsService.S3
                )
            }
        )

        # -------------------------------
        # Secrets Manager to securely generate and store DB credentials
        # -------------------------------
        db_secret = sm.Secret(self, "DBSecret",
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template='{"username":"postgres"}',
                generate_string_key="password",
                exclude_characters='/"@ '
            )
        )

        # -------------------------------
        # RDS PostgreSQL DB instance in private subnet with Secrets Manager integration
        # -------------------------------
        db = rds.DatabaseInstance(self, "DjangoDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_13
            ),
            credentials=rds.Credentials.from_secret(db_secret),
            vpc=vpc,
            vpc_subnets={"subnet_type": ec2.SubnetType.PRIVATE_WITH_EGRESS},
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO
            ),
            allocated_storage=20
        )

        # -------------------------------
        # ECS Fargate Service with Load Balancer
        # Pulls Docker image from local Dockerfile (./)
        # Injects DB host and secret-managed DB password into container environment
        # -------------------------------
        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "DjangoFargateService",
            vpc=vpc,
            cpu=256,
            memory_limit_mib=512,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("./"),
                container_port=8000,
                environment={
                    "DJANGO_SETTINGS_MODULE": "core.settings",
                    "DB_HOST": db.db_instance_endpoint_address,
                },
                secrets={
                    "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password")
                }
            ),
            public_load_balancer=True
        )

        # -------------------------------
        # Allow ECS tasks (Fargate) to connect to the DB on port 5432
        # -------------------------------
        db.connections.allow_from(service.service, ec2.Port.tcp(5432))
