terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "provision-demo-tfstate"
    key            = "provision-demo-platform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "provision-demo-tflock"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
