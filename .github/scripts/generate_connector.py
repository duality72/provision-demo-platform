#!/usr/bin/env python3
"""Generate connector configuration files for onboarding."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

CONNECTOR_REGISTRY = {
    "s3": {
        "config_fields": ["bucket_name", "region"],
        "secret_fields": [],
    },
    "postgres": {
        "config_fields": ["host", "port", "database"],
        "secret_fields": ["username", "password"],
    },
    "rest-api": {
        "config_fields": ["base_url", "polling_schedule"],
        "secret_fields": ["api_key"],
    },
    "sftp": {
        "config_fields": ["host", "port"],
        "secret_fields": ["username", "ssh_private_key"],
    },
}


def validate_payload(connector_type, payload):
    """Validate that the payload contains all required fields."""
    registry = CONNECTOR_REGISTRY[connector_type]
    errors = []

    config = payload.get("config", {})
    for field in registry["config_fields"]:
        if field not in config or not config[field]:
            errors.append(f"Missing required config field: {field}")

    secrets = payload.get("secrets", {})
    for field in registry["secret_fields"]:
        if field not in secrets or not secrets[field]:
            errors.append(f"Missing required secret field: {field}")

    return errors


def sops_encrypt(input_path, output_path):
    """Encrypt a file using SOPS with KMS."""
    kms_arn = os.environ.get("SOPS_KMS_ARN")
    if not kms_arn:
        print("WARNING: SOPS_KMS_ARN not set, skipping encryption", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            ["sops", "--encrypt", "--kms", kms_arn, input_path],
            capture_output=True,
            text=True,
            check=True,
        )
        with open(output_path, "w") as f:
            f.write(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"SOPS encryption failed: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("ERROR: sops binary not found", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate connector configuration files")
    parser.add_argument(
        "--connector-type",
        required=True,
        choices=list(CONNECTOR_REGISTRY.keys()),
        help="Type of connector",
    )
    parser.add_argument(
        "--connector-name",
        required=True,
        help="Name of the connector",
    )
    parser.add_argument(
        "--payload-file",
        required=True,
        help="Path to the decrypted JSON payload file",
    )
    args = parser.parse_args()

    # Read payload
    try:
        with open(args.payload_file, "r") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to read payload file: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate
    errors = validate_payload(args.connector_type, payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    # Create connector directory
    connector_dir = os.path.join("connectors", args.connector_name)
    os.makedirs(connector_dir, exist_ok=True)

    # Coerce all config values to strings for Terraform compatibility
    config = {k: str(v) for k, v in payload["config"].items()}

    # Write config.json
    config_data = {
        "connector_name": args.connector_name,
        "connector_type": args.connector_type,
        "config": config,
        "created_by": payload.get("requested_by", payload.get("created_by", "system")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    config_path = os.path.join(connector_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
        f.write("\n")
    print(f"Created {config_path}")

    # Handle secrets
    registry = CONNECTOR_REGISTRY[args.connector_type]
    if registry["secret_fields"]:
        secrets_data = {field: payload["secrets"][field] for field in registry["secret_fields"]}
        secrets_path = os.path.join(connector_dir, "secrets.json")
        encrypted_path = os.path.join(connector_dir, "secrets.enc.json")

        with open(secrets_path, "w") as f:
            json.dump(secrets_data, f, indent=2)
            f.write("\n")

        if sops_encrypt(secrets_path, encrypted_path):
            os.remove(secrets_path)
            print(f"Created {encrypted_path} (SOPS encrypted)")
        else:
            os.remove(secrets_path)
            print("WARNING: Secrets file was not encrypted", file=sys.stderr)
    else:
        print("No secrets required for this connector type")

    print(f"\nConnector '{args.connector_name}' ({args.connector_type}) generated successfully")


if __name__ == "__main__":
    main()
