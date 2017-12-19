import boto3
import time
import smtplib
import json
import configparser
import logging
import sys
import signal
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def signal_handler(signal, frame):
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def send_email(smtp, user, recipient, subject, body_text, body_html):
	message = MIMEMultipart('alternative')
	message['Subject'] = subject
	message['From'] = user
	message['To'] = recipient
	message.attach(MIMEText(body_text, 'plain'))
	message.attach(MIMEText(body_html, 'html'))
	smtp.sendmail(user, recipient, message.as_string())

def handle_send(message, message_json, smtp, smtp_username):
	recipient = message_json['recipient']
	subject = message_json['subject']
	body_text = message_json['body_text']
	body_html = message_json['body_html']
	send_email(smtp, smtp_username, recipient, subject, body_text, body_html)
	message.delete()
	logging.info("Sent email")

def handle_redrive(message, input_queue, deadletter_queue):
	logging.info("Redriving DLQ...")
	while True:
		messages = deadletter_queue.receive_messages(MaxNumberOfMessages = 10)
		for src_message in messages:
			input_queue.send_message(MessageBody = src_message.body)
			src_message.delete()
		if len(messages) <= 0:
			logging.info("Redrive finished")
			break
	message.delete()

def reset_alarm(input_queue_size_alarm_name):
	client = boto3.client('cloudwatch')
	logging.info("Resetting input queue size alarm state...")
	response = client.set_alarm_state(
		AlarmName = input_queue_size_alarm_name,
		StateValue = 'OK',
		StateReason = 'Ion lambda is terminating'
	)

def run(event, context):
	start_time = time.time()
	logging.basicConfig(format='%(asctime)s %(levelname)-s %(module)s:%(lineno)d - %(message)s', level = logging.INFO)

	config = configparser.RawConfigParser()
	config.read('config.cfg')
	input_queue_name = config.get('sqs', 'input_queue_name')
	deadletter_queue_name = config.get('sqs', 'deadletter_queue_name')
	input_queue_size_alarm_name = config.get('cloudwatch', 'input_queue_size_alarm_name')
	lambda_timeout = int(config.get('lambda', 'timeout'))
	early_timeout = lambda_timeout - 30

	config_secrets = configparser.RawConfigParser()
	config_secrets.read('config-secrets.cfg')
	smtp_server = config_secrets.get('smtp', 'server')
	smtp_port = int(config_secrets.get('smtp', 'port'))
	smtp_username = config_secrets.get('smtp', 'username')
	smtp_password = config_secrets.get('smtp', 'password')

	smtp = smtplib.SMTP(smtp_server, smtp_port)
	smtp.ehlo()
	smtp.starttls()
	smtp.login(smtp_username, smtp_password)

	sqs = boto3.resource('sqs')
	input_queue = sqs.get_queue_by_name(QueueName=input_queue_name)
	deadletter_queue = sqs.get_queue_by_name(QueueName=deadletter_queue_name)

	while True:
		logging.info("Polling SQS for messages...")
		messages = input_queue.receive_messages(MaxNumberOfMessages = 10)
		for message in messages:
			try:
				message_json = json.loads(message.body)
				action = message_json['action']
				if action == "send":
					handle_send(message, message_json, smtp, smtp_username)
				elif action == "redrive":
					handle_redrive(message, input_queue, deadletter_queue)
			except Exception as e:
				logging.error("Error handling message: " + str(e) + ". Original message: '" + message.body + "'")
				message.change_visibility(VisibilityTimeout = 60)
		elapsed_time = time.time() - start_time
		if elapsed_time >= early_timeout:
			logging.info("Elapsed time is " + str(elapsed_time) + "/" + str(lambda_timeout) + " seconds. Terminating...")
			smtp.close()
			reset_alarm(input_queue_size_alarm_name)
			break

if __name__ == "__main__":
	run(None, None)
