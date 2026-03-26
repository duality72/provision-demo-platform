output "connectors" {
  description = "Map of registered connectors and their status"
  value = {
    for name, mod in module.connector :
    name => {
      connector_name = mod.connector_name
      connector_type = mod.connector_type
      status         = mod.status
    }
  }
}
