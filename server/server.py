import boto3
import time
import smtplib
import json
import configparser
import logging
import sys
import signal
import logging

def signal_handler(signal, frame):
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def send_email(server, port, user, pwd, recipient, subject, body):
	message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
	""" % (user, recipient, subject, body)
	server = smtplib.SMTP(server, port) # TODO: does this have to be opened every time?
	server.ehlo()
	server.starttls()
	server.login(user, pwd)
	server.sendmail(user, recipient, message)
	server.close()

def handle_send(message, message_json, email_send_delay, smtp_server, smtp_port, smtp_username, smtp_password):
	recipient = message_json['recipient']
	subject = message_json['subject']
	body = message_json['body']
	send_email(smtp_server, smtp_port, smtp_username, smtp_password, recipient, subject, body)
	message.delete()
	logging.info("Sent email")
	#time.sleep(email_send_delay)

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

def run(event, context):
	logging.basicConfig(format='%(asctime)s %(levelname)-s %(module)s:%(lineno)d - %(message)s', level = logging.INFO)

	config = configparser.RawConfigParser()
	config.read('config.cfg')
	input_queue_name = config.get('sqs', 'input_queue_name')
	deadletter_queue_name = config.get('sqs', 'deadletter_queue_name')
	sqs_read_delay = float(config.get('sqs', 'read_delay'))
	email_send_delay = float(config.get('smtp', 'send_delay'))

	config_secrets = configparser.RawConfigParser()
	config_secrets.read('config-secrets.cfg')
	smtp_server = config_secrets.get('smtp', 'server')
	smtp_port = int(config_secrets.get('smtp', 'port'))
	smtp_username = config_secrets.get('smtp', 'username')
	smtp_password = config_secrets.get('smtp', 'password')

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
					handle_send(message, message_json, email_send_delay, smtp_server, smtp_port, smtp_username, smtp_password)
				elif action == "redrive":
					handle_redrive(message, input_queue, deadletter_queue)
			except Exception as e:
				logging.error("Error handling message: " + str(e) + ". Original message: '" + message.body + "'")
				message.change_visibility(VisibilityTimeout = 60)
		#time.sleep(sqs_read_delay)
		if len(messages) <= 0:
			logging.info("Input queue is empty. Terminating...")
			break

if __name__ == "__main__":
	run(None, None)
