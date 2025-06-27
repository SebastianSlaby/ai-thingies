resource "aws_ebs_volume" "my_ebs_volume" {
  availability_zone = "us-east-1a" # Placeholder: Replace with a valid AZ for your region
  size              = 10
  type              = "gp2"

  tags = {
    Name = "MyEBSVolume"
  }
}
