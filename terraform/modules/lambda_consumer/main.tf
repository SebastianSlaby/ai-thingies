variable "lambda_arn" {
  description = "The ARN of the lambda function"
  type        = string
}

output "module_lambda_arn" {
  value = var.lambda_arn
}
