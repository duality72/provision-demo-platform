# Project Instructions

## Overview

This is the Provision Demo Platform repo — the target repo that receives automated PRs from the [Provision Demo](https://github.com/duality72/provision-demo) web application. It contains connector configurations and the GitHub Actions workflows that generate them.

## Relationship to provision-demo

The provision-demo Lambda dispatches `workflow_dispatch` events to this repo's workflows. Changes here must be coordinated with the Lambda:

- **Deploy this repo first** when changing workflow inputs, since the Lambda dispatches to these workflows
- **Workflow inputs** are defined by what the Lambda sends — adding/removing inputs requires changes in both repos
- **Branch naming** is controlled by the Lambda (timestamped `feat/onboard-{name}-YYYYMMDD-HHMMSS` / `feat/remove-{name}-YYYYMMDD-HHMMSS`)

## Workflows

### onboard-connector.yml

Triggered by the Lambda when a user submits a new connector. Receives encrypted payload, decrypts it, generates config files, and opens a PR.

Key inputs: `connector_name`, `connector_type`, `encrypted_payload`, `requested_by`, `branch_name`

### remove-connector.yml

Triggered by the Lambda when a user clicks "Remove" on an active connector. Deletes the connector directory and opens a PR.

Key inputs: `connector_name`, `requested_by`, `branch_name`

## Adding a New Connector Type

Changes needed in three places across both repos:

1. **This repo**: Add the type to `CONNECTOR_REGISTRY` in `.github/scripts/generate_connector.py`
2. **provision-demo (frontend)**: Add to `CONNECTOR_REGISTRY`, `FIELD_VALIDATORS`, and `SECRET_TOOLTIPS` in `index.html`
3. **provision-demo (backend)**: Add to `CONNECTOR_TYPES` in `dispatch.py`

## Connector Directory Structure

Each connector lives in `connectors/{connector-name}/`:
- `config.json` — connector configuration (type, non-secret fields)
- `secrets.enc.json` — SOPS-encrypted secrets (if the connector type has secret fields)

Terraform discovers connectors via `fileset()` on `connectors/*/config.json`.

## Monitor PRs for status checks and Copilot

When creating PRs, always:
1. Wait for CI status checks to pass: `gh pr checks <number> --watch`
2. Check for Copilot code review comments: `gh api repos/duality72/provision-demo-platform/pulls/<number>/comments --jq '.[] | "[\(.user.login)] \(.path):\(.line) — \(.body[0:200])"'`
3. Address any Copilot findings before merging
4. Copilot is configured as an automatic reviewer on PRs to main

## Testing

This repo should be testable independently of the provision-demo web app. Use `gh workflow run` to trigger workflows directly from the command line.

### Testing the onboard workflow

The onboard workflow requires a real age-encrypted payload. To create one:

```
# Get the age public key from SSM
AGE_PUB_KEY=$(aws ssm get-parameter --name /provision-demo/age-public-key --query 'Parameter.Value' --output text --region us-east-1)

# Create and encrypt a test payload
PAYLOAD=$(echo '{"connector_name":"test-direct","connector_type":"s3","config":{"bucket_name":"my-test-bucket","region":"us-east-1"},"secrets":{}}' \
  | age -r "$AGE_PUB_KEY" | base64)

# Trigger the workflow
gh workflow run onboard-connector.yml \
  --repo duality72/provision-demo-platform \
  -f connector_name=test-direct \
  -f connector_type=s3 \
  -f encrypted_payload="$PAYLOAD" \
  -f requested_by="test@example.com" \
  -f branch_name="feat/onboard-test-direct-20260328-120000"
```

Prerequisites: `age` CLI installed locally and AWS credentials to read the SSM parameter.

After the workflow completes, verify:
- The PR was created with the correct branch name, title, and body
- `connectors/test-direct/config.json` contains the expected configuration
- `connectors/test-direct/secrets.enc.json` is SOPS-encrypted (if the type has secrets)

Clean up: close the PR and delete the branch when done.

### Testing the remove workflow

The remove workflow is simpler — no encryption needed, but the connector must exist on main:

```
gh workflow run remove-connector.yml \
  --repo duality72/provision-demo-platform \
  -f connector_name=test-direct \
  -f requested_by="test@example.com" \
  -f branch_name="feat/remove-test-direct-20260328-120100"
```

If the connector directory doesn't exist on main, the workflow fails with "Connector directory does not exist" — this is expected and correct behavior.

### Testing generate_connector.py locally

```
echo '{"connector_name":"test","connector_type":"s3","config":{"bucket_name":"b","region":"us-east-1"},"secrets":{}}' > /tmp/test-payload.json
python .github/scripts/generate_connector.py --connector-type s3 --connector-name test --payload-file /tmp/test-payload.json
ls connectors/test/
```

This requires `SOPS_KMS_ARN` env var and AWS credentials for SOPS encryption if the connector type has secrets.

### Contract with provision-demo

The provision-demo Lambda depends on this repo's outputs. If you change any of these, coordinate with the other repo:

- **Workflow inputs**: The Lambda constructs these — adding/removing inputs requires changes in both repos
- **PR body format**: The Lambda parses `**Type:**` and `**Requested by:**` lines from PR bodies. If you change the PR body template in the workflow, update `handle_connectors()` in dispatch.py
- **Connector directory structure**: The Lambda's `/connectors` endpoint reads `connectors/{name}/config.json` from main. Changes to the directory layout require updating the Lambda
- **Branch naming**: The Lambda generates timestamped branch names and the `/connectors` endpoint parses them to extract connector names

## GitHub Actions

All actions should use Node.js 24 compatible versions:
- `actions/checkout@v6`
- `actions/setup-python@v6`
- `aws-actions/configure-aws-credentials@v6`

## Common Gotchas

- **Branch already exists**: If the Lambda generates a branch name that already exists (shouldn't happen with timestamps, but could in theory with sub-second concurrent requests), the `git push` will fail. The Lambda checks for existing branches/PRs before dispatching.
- **Connector directory not found**: The remove workflow checks that `connectors/{name}` exists before attempting `git rm`. If it doesn't exist, the workflow fails with a clear error.
- **SOPS encryption**: Requires the KMS key ARN and AWS credentials. The OIDC role must have `kms:Encrypt` and `kms:Decrypt` permissions.
- **PR body parsing**: The provision-demo Lambda parses PR bodies for `**Type:**` and `**Requested by:**` lines to extract metadata for the Connectors tab. If you change the PR body format, update the parsing in `handle_connectors()` in dispatch.py.
