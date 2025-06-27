resource "aws_ecs_task_definition" "my_task" {
  family                   = "my-app-task"
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_exec.arn # Placeholder
  task_role_arn            = aws_iam_role.ecs_task_exec.arn # Placeholder

  container_definitions = jsonencode([
    {
      name      = "my-app"
      image     = "nginx:latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
        }
      ]
    }
  ])

  tags = {
    Name = "MyAppTask"
  }
}

resource "aws_iam_role" "ecs_task_exec" {
  name = "ecs_task_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}
