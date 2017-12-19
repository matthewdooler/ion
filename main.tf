module "ion" {
  source = "./ion"

  aws_region = "eu-west-1"

  input_queue_name = "ion-input-queue"
  input_deadletter_queue_name = "ion-input-deadletter-queue"
  input_topic_name = "ion-input-topic"

  lambda_function_name = "ion"
  lambda_role_name = "ion-lambda-role"
}