resource "aws_instance" "my_instance" {
  ami           = "ami-0abcdef1234567890" # Placeholder: Replace with a valid AMI for your region
  instance_type = "t2.micro"
  key_name      = "my-key-pair" # Placeholder: Replace with an existing key pair

  tags = {
    Name = "MyEC2Instance"
  }
}
