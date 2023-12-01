# CodeChecker

This CDK app creates a CodeChecker on your repository.
What is needed is to fill in the following variables:

# Constant variables
REPOSITORY_NAME = "my_demo_repo"
MY_ASSUME_ROLE = "vanzee.cloud/yvo-dev"
APPROVALS_REQUIRED_MAIN = 1
TEMPLATES_FOLDER = "cdk.out"
TEMPLATES_FILE_SUFFIX = "*.template.json"

The repository name where the codechecker is running on.
Your Assume role which is used to accept approvals from.
Approvals required for the MAIN branch.
Where your CloudFormation templates are stored, in this case CDK.out
And what the suffix is of the template, in this case ending with template.json.
