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
        # Definir URLs de las colas por prioridad
        self.priority_queue_urls = {
            'high': os.getenv('SQS_HIGH_PRIORITY_URL'),
            'medium': os.getenv('SQS_MEDIUM_PRIORITY_URL'),
            'low': os.getenv('SQS_LOW_PRIORITY_URL')
        }

    def get_queue_url(self, priority_level):
        return self.priority_queue_urls.get(priority_level)

    def put(self, priority_level, item):
        try:
            queue_url = self.get_queue_url(priority_level)
            if not queue_url:
                print(f"❌ URL de cola no encontrada para prioridad '{priority_level}'")
                return

            # Agregar timestamp para ayudar con el ordenamiento
            message = {
                'timestamp': str(int(time.time())),
                'data': item  # item ya contiene los datos necesarios
            }

            response = self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                DelaySeconds=0  # Entrega inmediata
            )
            return response
        except ClientError as e:
            print(f"Error enviando mensaje a SQS: {e}")
            raise

    def get(self):
        # Prioridades en orden descendente
        for priority_level in ['high', 'medium', 'low']:
            queue_url = self.get_queue_url(priority_level)
            try:
                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=5,
                    VisibilityTimeout=30
                )

                if 'Messages' in response:
                    msg = response['Messages'][0]
                    body = json.loads(msg['Body'])
                    receipt_handle = msg['ReceiptHandle']
                    # Eliminar el mensaje procesado
                    self.sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=receipt_handle
                    )
                    return (priority_level, body['data'])
            except ClientError as e:
                print(f"Error recibiendo mensaje de SQS: {e}")
                continue  # Intentar con la siguiente cola

        print("❌ No se encontraron mensajes en ninguna cola.")
        return None

    def empty(self):
        total_messages = 0
        for priority_level in ['high', 'medium', 'low']:
            queue_url = self.get_queue_url(priority_level)
            try:
                response = self.sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages']
                )
                num_messages = int(response['Attributes']['ApproximateNumberOfMessages'])
                total_messages += num_messages
            except ClientError as e:
                print(f"Error comprobando estado de la cola {priority_level}: {e}")
        return total_messages == 0

    def purge(self):
        for priority_level in ['high', 'medium', 'low']:
            queue_url = self.get_queue_url(priority_level)
            try:
                self.sqs.purge_queue(QueueUrl=queue_url)
                print(f"✅ Cola SQS '{priority_level}' purgada exitosamente.")
                time.sleep(1)  # Pequeño delay entre purgas
            except ClientError as e:
                print(f"Error purgando la cola SQS '{priority_level}': {e}")
