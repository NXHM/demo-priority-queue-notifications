import boto3
from botocore.exceptions import ClientError
import os  
import json  
import time  

class DistributedPriorityQueue:
    def __init__(self):
        self.sqs = boto3.client(
            'sqs',
            aws_access_key_id=os.getenv('ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'),
            region_name='us-east-2'
        )
        self.queue_url = os.getenv('SQS_QUEUE_URL')

    def put(self, item):
        try:
            priority, *message_data = item
            # Agregar timestamp para ayudar con el ordenamiento
            message = {
                'timestamp': str(int(time.time())),
                'data': message_data
            }
            
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'Priority': {
                        'DataType': 'Number',
                        'StringValue': str(priority)
                    }
                },
                DelaySeconds=0  # Entrega inmediata
            )
            return response
        except ClientError as e:
            print(f"Error sending message to SQS: {e}")
            raise

    def get(self):
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=10,  # Obtener varios mensajes para ordenar
                MessageAttributeNames=['Priority'],
                WaitTimeSeconds=5,
                VisibilityTimeout=30
            )
            
            if 'Messages' not in response:
                return None

            # Filtrar y ordenar mensajes
            messages = []
            for msg in response.get('Messages', []):
                try:
                    if 'MessageAttributes' in msg and 'Priority' in msg['MessageAttributes']:
                        priority = int(msg['MessageAttributes']['Priority']['StringValue'])
                        body = json.loads(msg['Body'])
                        messages.append({
                            'priority': priority,
                            'timestamp': body['timestamp'],
                            'data': body['data'],
                            'receipt': msg['ReceiptHandle']
                        })
                except (KeyError, ValueError, json.JSONDecodeError):
                    continue

            if not messages:
                return None

            # Ordenar primero por prioridad (menor número = mayor prioridad)
            messages.sort(key=lambda x: (x['priority'], x['timestamp']))
            selected = messages[0]

            # Eliminar el mensaje procesado
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=selected['receipt']
            )

            # Retornar el mensaje en el formato esperado
            return (selected['priority'], *selected['data'])

        except ClientError as e:
            print(f"Error receiving message from SQS: {e}")
            return None

    def empty(self):
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            return int(response['Attributes']['ApproximateNumberOfMessages']) == 0
        except ClientError as e:
            print(f"Error checking queue status: {e}")
            return True  # Asumimos cola vacía en caso de error

    def purge(self):
        try:
            # Verificar última purga
            last_purge = getattr(self, 'last_purge', 0)
            current_time = time.time()
            if current_time - last_purge < 60:
                print("⚠️ La cola ya fue purgada recientemente. Espera antes de purgar de nuevo.")
                return
            self.sqs.purge_queue(QueueUrl=self.queue_url)
            print("✅ Cola SQS purgada exitosamente.")
            self.last_purge = current_time
        except ClientError as e:
            print(f"Error purgando la cola SQS: {e}")
