provider "aws" {
  region = "${var.aws_region}"
}

resource "aws_sqs_queue" "input_queue" {
  name                      = "ion-input-queue"
  receive_wait_time_seconds = 20
  redrive_policy            = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.input_deadletter_queue.arn}\",\"maxReceiveCount\":10}"
}

resource "aws_sqs_queue" "input_deadletter_queue" {
  name                      = "ion-input-deadletter-queue"
}