locals {
  connector_files = fileset("${path.module}/../connectors", "*/config.json")

  connectors = {
    for f in local.connector_files :
    dirname(f) => jsondecode(file("${path.module}/../connectors/${f}"))
  }
}

module "connector" {
  source   = "./modules/connector"
  for_each = local.connectors

  connector_name = each.value.connector_name
  connector_type = each.value.connector_type
  config         = each.value.config
}
