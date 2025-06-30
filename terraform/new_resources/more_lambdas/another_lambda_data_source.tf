data "aws_lambda_function" "another_lambda_data" {
  function_name = aws_lambda_function.another_lambda.function_name
}

output "another_lambda_data_arn" {
  value = data.aws_lambda_function.another_lambda_data.arn
}
