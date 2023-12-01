from aws_cdk import (
    Aspects,
    Stack,
    aws_iam as iam,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_kms,
    aws_events_targets as event_target,
    aws_sns as sns,
    custom_resources as custom_resources,
)
from constructs import Construct

from cloudcomponents.cdk_pull_request_check import PullRequestCheck

from cloudcomponents.cdk_pull_request_approval_rule import (
    Approvers,
    ApprovalRuleTemplate,
    ApprovalRuleTemplateRepositoryAssociation,
    Template,
)
import cdk_nag

# Constant variables
REPOSITORY_NAME = "my_demo_repo"
MY_ASSUME_ROLE = "MY_ASSUME_ROLE"
APPROVALS_REQUIRED_MAIN = 1
TEMPLATES_FOLDER = "cdk.out"
TEMPLATES_FILE_SUFFIX = "*.template.json"


class CodecheckerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import the CodeCommit repository where the codechecker needs to check the pull requests.
        self.repository = codecommit.Repository.from_repository_name(
            self, "Repository", repository_name=REPOSITORY_NAME
        )

        # Create the pull request check
        pull_request_check = self.create_pull_request_check(self.repository)

        # Create SNS topic for monitoring purpose
        monitoring_topic = sns.Topic(
            self,
            "MonitoringTopic",
            master_key=aws_kms.Key(
                self,
                "MonitoringTopicKey",
                enable_key_rotation=True,
                alias="/sns/monitoring",
            ),
        )
        # Sent notification on failed build
        pull_request_check.on_check_failed(
            "Failed", target=event_target.SnsTopic(monitoring_topic)
        )

        # Dict for branches and amount of approvals needed via constant variables
        approvals_per_branch = {
            "main": APPROVALS_REQUIRED_MAIN,
        }

        # Starting for loop over dict and create approval templates
        for branch, required_approvals in approvals_per_branch.items():
            create_approval_template = self.create_approval_template(
                id=f"{branch}-{required_approvals}",
                branch=branch,
                required_approvals=required_approvals,
                repository_name=self.repository.repository_name,
                pr_check_approval_role=pull_request_check.code_build_result_function.role.role_name,
            )

            # Associate approval rule template with repositories from list
            approval_template_association = (
                self.associate_approval_rule_template_with_repositories(
                    id=f"associate-existing-repositories-{branch}-{required_approvals}",
                    branch=branch,
                    required_approvals=required_approvals,
                )
            )

            approval_template_association.node.add_dependency(create_approval_template)
        # Adding CDK Nag aspects
        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())
        # Suppress some known CDK findings
        cdk_nag.NagSuppressions.add_stack_suppressions(
            self,
            [
                {"id": "AwsSolutions-IAM4", "reason": "Managed policies are allowed"},
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard in generated policy by CDK is allowed",
                },
                {
                    "id": "AwsSolutions-CB4",
                    "reason": "Not supported by PullRequestCheck - The CodeBuild project does not use an AWS KMS key for encryption. TODO fix with aspect",
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Not supported by PullRequestCheck -  The non-container Lambda function is not configured to use the latest runtime version. TODO fix with aspect",
                },
            ],
        )

    def create_approval_template(
        self,
        id: str,
        branch: str,
        required_approvals: int,
        repository_name: str,
        pr_check_approval_role: str,
    ) -> ApprovalRuleTemplate:
        """Function to create the actual approval template"""
        return ApprovalRuleTemplate(
            self,
            f"{id}-ApprovalRuleTemplate",
            approval_rule_template_name=self.get_approval_rule_template_name(
                required_approvals, repository_name, branch
            ),
            approval_rule_template_description=f"Requires {required_approvals} approvals from the team to approve the pull request",
            template=Template(
                approvers=Approvers(
                    number_of_approvals_needed=required_approvals,
                    approval_pool_members=[
                        f"arn:aws:sts::{Stack.of(self).account}:assumed-role/{MY_ASSUME_ROLE}/*",
                        f"arn:aws:sts::{Stack.of(self).account}:assumed-role/{pr_check_approval_role}/*",
                    ],
                ),
                branches=[branch],
            ),
        )

    def associate_approval_rule_template_with_repositories(
        self,
        id: str,
        branch: str,
        required_approvals: int,
    ) -> ApprovalRuleTemplateRepositoryAssociation:
        """Function to associate the approval template with the repository"""

        return ApprovalRuleTemplateRepositoryAssociation(
            self,
            f"{id}-ApprovalRuleTemplateRepositoryAssociation",
            approval_rule_template_name=self.get_approval_rule_template_name(
                required_approvals, self.repository.repository_name, branch
            ),
            repository=self.repository,
        )

    @staticmethod
    def get_approval_rule_template_name(
        required_approvals: int, repository_name: str, branch: str
    ) -> str:
        return f"{str(required_approvals)}-approval-for-{repository_name}-{branch}"

    def create_pull_request_role(self, repository_name: str) -> iam.IRole:
        """First create a role to be used for CodeBuild, otherwise a dependency issue will occure with adding to VPC"""
        role = iam.Role(
            self,
            "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            inline_policies={
                "CloudWatchLoggingAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/codebuild/{repository_name}-pull-request:*",
                                f"arn:aws:logs:{Stack.of(self).region}:{Stack.of(self).account}:log-group:/aws/codebuild/{repository_name}-pull-request",
                            ],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "codebuild:BatchPutCodeCoverages",
                                "codebuild:BatchPutTestCases",
                                "codebuild:CreateReport",
                                "codebuild:CreateReportGroup",
                                "codebuild:UpdateReport",
                            ],
                            resources=[
                                f"arn:aws:codebuild:{Stack.of(self).region}:{Stack.of(self).account}:report-group/{repository_name}-pull-request-*"
                            ],
                        ),
                    ]
                ),
            },
        )

        return role

    def create_pull_request_check(
        self, repository: codecommit.Repository
    ) -> PullRequestCheck:
        """Function to create the pull request check, CodeBuild project"""

        # Create a CodeBuild project which will check the code on a pull request.
        pullrequest = PullRequestCheck(
            self,
            "PullRequestCheck",
            repository=repository,
            role=self.create_pull_request_role(
                repository_name=repository.repository_name
            ),
            build_image=codebuild.LinuxBuildImage.STANDARD_6_0,
            environment_variables={
                "TEMPLATES_FOLDER": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    value=TEMPLATES_FOLDER,
                ),
                "TEMPLATES_FILE_SUFFIX": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    value=TEMPLATES_FILE_SUFFIX,
                ),
            },
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "env": {"git-credential-helper": "yes"},
                    "phases": {
                        "install": {
                            "commands": [
                                "npm install -g aws-cdk",
                                "pip install -r requirements.txt",
                                "pip3 install cfn-lint",
                                "gem install cfn-nag",
                            ]
                        },
                        "build": {
                            "commands": [
                                "cdk synth",
                                "echo ### Scan templates with cfn-lint ###"
                                "for template in $(find ./$TEMPLATES_FOLDER -type f -maxdepth 3 -name $TEMPLATES_FILE_SUFFIX); do cfn-lint $template -i W2001 -i W3005 -i E3030; done",
                                "echo ### Scan templates with cfn-nag ###"
                                "for template in $(find ./$TEMPLATES_FOLDER -type f -maxdepth 3 -name $TEMPLATES_FILE_SUFFIX); do cfn_nag_scan -i $template; done",
                            ]
                        },
                        "post_build": {"commands": ["pytest -v"]},
                    },
                }
            ),
        )

        return pullrequest
