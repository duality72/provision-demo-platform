variable "connector_name" {
  description = "Name of the connector"
  type        = string
}

variable "connector_type" {
  description = "Type of the connector"
  type        = string
}

variable "config" {
  description = "Connector configuration map"
  type        = map(string)
}
