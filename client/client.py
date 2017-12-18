import boto3

input_queue_name = 'ion-input'

if __name__ == "__main__":
	sqs = boto3.resource('sqs')
	queue = sqs.get_queue_by_name(QueueName=input_queue_name)
	print(queue.url)
	print(queue.attributes.get('DelaySeconds'))