variable "aws_region" {
  description = "AWS region"
}

variable "input_queue_name" {
  description = "Input queue name"
}

variable "input_deadletter_queue_name" {
  description = "Input deadletter queue name"
}

variable "input_topic_name" {
  description = "Input topic name"
}

variable "lambda_function_name" {
  description = "Lambda function name"
}

variable "lambda_role_name" {
  description = "Lambda role name"
}
