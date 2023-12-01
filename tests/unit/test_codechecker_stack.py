from aws_cdk import App
from aws_cdk.assertions import Template

from codechecker.codechecker_stack import CodecheckerStack


class TestCodeCheckerStack:
    @staticmethod
    def test_synthesizes_properly() -> None:
        """Testing if template synthesizes properly"""
        app = App()
        stack = CodecheckerStack(app, "CodeCheckerStack")
        Template.from_stack(stack)

    #! We cannot do snapshot tests as we are using aspects to later change the cloudformation template.
    # def test_matches_snapshot(snapshot):
    #     """
    #     Validate that the synthesized stack is equal to the stored snapshot. This will detect impactful changes within the CDK framework.
    #     Run: "pytest --snapshot-update" to create the initial snapshot or update the existing one.
    #     """
    #     app = App()
    #     stack = CodecheckerStack(app, "CodeCheckerStack")

    #     # Prepare the stack for assertions.
    #     template = Template.from_stack(stack)

    #     assert template.to_json() == snapshot

    @staticmethod
    def test_count_resources() -> None:
        """Testing if amount of resources are correct"""
        app = App()
        stack = CodecheckerStack(app, "CodeCheckerStack")
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::CodeBuild::Project", 1)
        template.resource_count_is("Custom::ApprovalRuleTemplate", 1)
        template.resource_count_is(
            "Custom::ApprovalRuleTemplateRepositoryAssociation", 1
        )
        template.resource_count_is("AWS::Lambda::Function", 3)
        template.resource_count_is("AWS::IAM::Role", 5)
        template.resource_count_is("AWS::KMS::Key", 1)
        template.resource_count_is("AWS::KMS::Alias", 1)

    # @staticmethod
    # def test_lambda_functions_in_vpc() -> None:
    #     """Testing if Lambda functions do have a VPC config"""
    #     app = App()
    #     stack = CodecheckerStack(app, "CodeCheckerStack")
    #     template = Template.from_stack(stack)
    #     template.has_resource_properties("AWS::Lambda::Function", {"VpcConfig": {}})

    # @staticmethod
    # def test_codebuild_projects_in_vpc() -> None:
    #     """Testing if repository codebuild projects are inside VPC"""
    #     app = App()
    #     stack = CodecheckerStack(app, "CodeCheckerStack")
    #     template = Template.from_stack(stack)
    #     template.has_resource_properties("AWS::CodeBuild::Project", {"VpcConfig": {}})

    # @staticmethod
    # def test_repository_stack_to_return_repository_name() -> None:
    #     """Testing if repository uses given and return proper name"""
    #     app = App()
    #     stack = CodecheckerStack(app, "CodeCheckerStack")
    #     template = Template.from_stack(stack)
    #     template.has_resource_properties(
    #         "AWS::CodeCommit::Repository", {"RepositoryName": "test"}
    #     )
    #     stack.repository.repository_name == "test"
