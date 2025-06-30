resource "aws_lambda_function" "a_third_lambda" {
  function_name = "a-third-example-lambda"
  handler       = "index.handler"
  runtime       = "go1.x"
  filename      = "a_third_lambda_payload.zip"
}
