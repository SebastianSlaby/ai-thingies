resource "aws_lambda_function" "another_lambda" {
  function_name = "another-example-lambda"
  handler       = "index.handler"
  runtime       = "python3.9"
  filename      = "another_lambda_payload.zip"
}
