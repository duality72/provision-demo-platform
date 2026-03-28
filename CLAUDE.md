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

## Testing

After any workflow change, test by submitting a connector through the live Provision Demo app and verifying:
- The workflow runs successfully
- Config files are generated correctly
- The PR is created with the right branch name, title, and body
- The provision-demo app's `/run-status` endpoint picks up the completed run and PR

For removal workflow changes, test by clicking "Remove" on an active connector in the app and verifying the PR deletes the correct directory.

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
