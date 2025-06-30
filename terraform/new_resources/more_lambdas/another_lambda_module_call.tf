module "another_lambda_consumer" {
  source = "../modules/lambda_consumer"
  lambda_arn = aws_lambda_function.another_lambda.arn
}
