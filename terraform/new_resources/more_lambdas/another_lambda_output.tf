output "another_lambda_arn_output" {
  value = aws_lambda_function.another_lambda.arn
  description = "The ARN of the another_lambda function"
}
