resource "aws_lambda_function" "a_fourth_lambda" {
  function_name = "a-fourth-example-lambda"
  handler       = "index.handler"
  runtime       = "ruby2.7"
  filename      = "a_fourth_lambda_payload.zip"
}
