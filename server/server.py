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

if __name__ == "__main__":
	logging.basicConfig(format='%(asctime)s %(levelname)-s %(module)s:%(lineno)d - %(message)s', level=logging.INFO)

	config = configparser.RawConfigParser()
	config.read('config.cfg')
	input_queue_name = config.get('sqs', 'queue_name')
	sqs_read_delay = float(config.get('sqs', 'read_delay'))
	email_send_delay = float(config.get('smtp', 'send_delay'))

	config_secrets = configparser.RawConfigParser()
	config_secrets.read('config-secrets.cfg')
	smtp_server = config_secrets.get('smtp', 'server')
	smtp_port = int(config_secrets.get('smtp', 'port'))
	smtp_username = config_secrets.get('smtp', 'username')
	smtp_password = config_secrets.get('smtp', 'password')

	sqs = boto3.resource('sqs')
	queue = sqs.get_queue_by_name(QueueName=input_queue_name)

	while True:
		logging.info("Polling SQS for messages...")
		for message in queue.receive_messages(): # TODO: more messages per batch
			try:
				message_json = json.loads(message.body)
				recipient = message_json['recipient']
				subject = message_json['subject']
				body = message_json['body']
				send_email(smtp_server, smtp_port, smtp_username, smtp_password, recipient, subject, body)
				message.delete()
				logging.info("Sent email")
			except Exception as e:
				logging.info("Failed to send email: " + str(e))
				logging.info("Original message from SQS: '" + message.body + "'")
				message.change_visibility(VisibilityTimeout = 60)
			time.sleep(email_send_delay)
		time.sleep(sqs_read_delay)