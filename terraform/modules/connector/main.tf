locals {
  connector_id = "${var.connector_type}/${var.connector_name}"
}

resource "local_file" "registration" {
  content  = "registered: ${local.connector_id}\n"
  filename = "${path.module}/../../../connectors/${var.connector_name}/.registered"
}

resource "null_resource" "register" {
  triggers = {
    connector_name = var.connector_name
    connector_type = var.connector_type
  }

  provisioner "local-exec" {
    command = "echo 'Connector ${var.connector_name} of type ${var.connector_type} registered'"
  }
}
