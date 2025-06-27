resource "aws_lambda_function" "my_lambda" {
  function_name = "my-example-lambda"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  filename      = "lambda_function_payload.zip"
  source_code_hash = filebase64sha256("lambda_function_payload.zip") # Placeholder

  role = aws_iam_role.lambda_exec.arn # Placeholder

  tags = {
    Name = "MyExampleLambda"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}
