locals {
  another_lambda_id = aws_lambda_function.another_lambda.id
}

output "local_lambda_id" {
  value = local.another_lambda_id
}
