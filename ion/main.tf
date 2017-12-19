provider "aws" {
  region = "${var.aws_region}"
}

resource "aws_sqs_queue" "input_queue" {
  name                      = "${var.input_queue_name}"
  receive_wait_time_seconds = 20
  redrive_policy            = "{\"deadLetterTargetArn\":\"${aws_sqs_queue.input_deadletter_queue.arn}\",\"maxReceiveCount\":3}"
}

resource "aws_sqs_queue" "input_deadletter_queue" {
  name = "${var.input_deadletter_queue_name}"
}

resource "aws_sns_topic" "input_topic" {
  name = "${var.input_topic_name}"
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
    function_name = "${var.lambda_function_name}"
    handler = "ion.run"
    runtime = "python3.6"
    filename = "ion.zip"
    source_code_hash = "${base64sha256(file("ion.zip"))}"
    role = "${aws_iam_role.ion_lambda_role.arn}"
    timeout = 120
    #reserved_concurrent_executions = 1
}

resource "aws_iam_role" "ion_lambda_role" {
  name = "${var.lambda_role_name}"
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
  name = "${aws_iam_role.ion_lambda_role.id}-policy"
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
    },
    {
      "Action": [
        "cloudwatch:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_cloudwatch_metric_alarm" "input_queue_size_alarm" {
  alarm_name                = "${aws_sqs_queue.input_queue.name}-size-alarm"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "1"
  metric_name               = "ApproximateNumberOfMessagesVisible"
  namespace                 = "AWS/SQS"
  dimensions {
    QueueName = "${aws_sqs_queue.input_queue.name}"
  }
  period                    = "60"
  statistic                 = "Maximum"
  threshold                 = "1"
  alarm_description         = "This metric monitors the number of available messages on the input queue"
  insufficient_data_actions = []
  alarm_actions             = ["${aws_sns_topic.input_queue_size_alarm_topic.arn}"]
}

resource "aws_sns_topic" "input_queue_size_alarm_topic" {
  name = "${aws_sqs_queue.input_queue.name}-size-alarm-topic"
}

resource "aws_sns_topic_subscription" "input_queue_size_alarm_topic_lambda" {
  topic_arn = "${aws_sns_topic.input_queue_size_alarm_topic.arn}"
  protocol  = "lambda"
  endpoint  = "${aws_lambda_function.ion.arn}"
}

resource "aws_lambda_permission" "input_queue_size_alarm_topic_lambda_permission" {
    statement_id = "AllowExecutionFromSNS1"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.ion.arn}"
    principal = "sns.amazonaws.com"
    source_arn = "${aws_sns_topic.input_queue_size_alarm_topic.arn}"
}

resource "aws_sns_topic_subscription" "input_topic_lambda" {
  topic_arn = "${aws_sns_topic.input_topic.arn}"
  protocol  = "lambda"
  endpoint  = "${aws_lambda_function.ion.arn}"
}

resource "aws_lambda_permission" "input_topic_lambda_permission" {
    statement_id = "AllowExecutionFromSNS2"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.ion.arn}"
    principal = "sns.amazonaws.com"
    source_arn = "${aws_sns_topic.input_topic.arn}"
}

