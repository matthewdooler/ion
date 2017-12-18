provider "aws" {
  region = "${var.aws_region}"
}

resource "aws_sqs_queue" "input_queue" {
  name                      = "ion-input-queue"
  receive_wait_time_seconds = 20
  redrive_policy            = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.input_deadletter_queue.arn}\",\"maxReceiveCount\":3}"
}

resource "aws_sqs_queue" "input_deadletter_queue" {
  name = "ion-input-deadletter-queue"
}

resource "aws_sns_topic" "input_topic" {
  name = "ion-input-topic"
}

resource "aws_sns_topic_subscription" "input_queue_subscription" {
  topic_arn            = "${aws_sns_topic.input_topic.arn}"
  protocol             = "sqs"
  endpoint             = "${aws_sqs_queue.input_queue.arn}"
  raw_message_delivery = true
}

resource "aws_sqs_queue_policy" "input_queue_sns_policy" {
  queue_url = "${aws_sqs_queue.input_queue.id}"

  policy = <<POLICY
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Sid":"SNSPolicy",
      "Effect":"Allow",
      "Principal":"*",
      "Action":"sqs:SendMessage",
      "Resource":"${aws_sqs_queue.input_queue.arn}",
      "Condition":{
        "ArnEquals":{
          "aws:SourceArn":"${aws_sns_topic.input_topic.arn}"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_lambda_function" "ion" {
    function_name = "ion"
    handler = "server.run"
    runtime = "python3.6"
    filename = "server.zip"
    source_code_hash = "${base64sha256(file("server.zip"))}"
    role = "${aws_iam_role.ion_lambda_role.arn}"
    timeout = 60
}

resource "aws_iam_role" "ion_lambda_role" {
  name = "ion-lambda-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "ion_lambda_role_policy" {
  name = "ion-lambda-role-policy"
  role = "${aws_iam_role.ion_lambda_role.id}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "sqs:*"
      ],
      "Effect": "Allow",
      "Resource": "${aws_sqs_queue.input_queue.arn}"
    },
    {
      "Action": [
        "sqs:*"
      ],
      "Effect": "Allow",
      "Resource": "${aws_sqs_queue.input_deadletter_queue.arn}"
    }
  ]
}
EOF
}