resource "aws_ecs_cluster" "my_cluster" {
  name = "my-example-cluster"

  tags = {
    Name = "MyECSCluster"
  }
}
