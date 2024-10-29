import boto3
import os
import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from botocore.config import Config

# Cargar las variables de entorno desde el archivo .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

class NotificationManager:
    def __init__(self):
        self.config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
        self.dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=os.getenv('ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'),
            region_name='us-east-2',
            config=self.config
        )
        self.sns_client = boto3.client(
            'sns',
            aws_access_key_id=os.getenv('ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'),
            region_name='us-east-2',
            config=self.config
        )
        self.table_name = 'notifications'
        
    def validate_input(self, user_id, email, type_to_behavior):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid UserID")
        if not email or "@" not in email:
            raise ValueError("Invalid Email Address")
        if type_to_behavior not in ['Subscription', 'Reminder', 'Offer']:
            raise ValueError("Invalid TypeBehavior")

    def create_notifications_table(self):
        try:
            response = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'UserID_TypeBehavior_BeautySalonID',
                        'KeyType': 'HASH'  # Clave de partición
                    },
                    {
                        'AttributeName': 'Timestamp',
                        'KeyType': 'RANGE'  # Clave de ordenación
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'UserID_TypeBehavior_BeautySalonID',
                        'AttributeType': 'S'  # Tipo de atributo: String
                    },
                    {
                        'AttributeName': 'Timestamp',
                        'AttributeType': 'S'  # Tipo de atributo: String
                    },
                    {
                        'AttributeName': 'TypeBehavior',
                        'AttributeType': 'S'  # Tipo de atributo: String
                    },
                    {
                        'AttributeName': 'BeautySalonID',
                        'AttributeType': 'S'  # Tipo de atributo: String
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'TypeBehavior-BeautySalonID-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'TypeBehavior',
                                'KeyType': 'HASH'  # Clave de partición
                            },
                            {
                                'AttributeName': 'BeautySalonID',
                                'KeyType': 'RANGE'  # Clave de ordenación
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            print("Table created successfully!")
            
            # Esperar hasta que la tabla esté en estado ACTIVE
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            print("Table is now active!")
            
            return response
        except self.dynamodb.exceptions.ResourceInUseException:
            print("Table already exists.")
        except ClientError as e:
            print(f"Client error while creating table: {e}")
        except Exception as e:
            print(f"Error creating table: {e}")

    def update_notifications(self, user_id, email, type_to_behavior, beauty_salon_id=None, date=None, time=None, service=None, offer_id=None, description=None, reminder_id=None):
        try:
            # Validar entradas
            self.validate_input(user_id, email, type_to_behavior)
            
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            user_id_type_behavior_beauty_salon_id = f"{user_id}#{type_to_behavior}#{beauty_salon_id}"

            item = {
                'UserID_TypeBehavior_BeautySalonID': {'S': user_id_type_behavior_beauty_salon_id},
                'Timestamp': {'S': timestamp},
                'Email': {'S': email},
                'TypeBehavior': {'S': type_to_behavior},  
                'Active': {'BOOL': True}
            }

            if beauty_salon_id is not None:
                item['BeautySalonID'] = {'S': beauty_salon_id}  

            if type_to_behavior == 'Reminder':
                if date is not None:
                    item['Date'] = {'S': date}
                if time is not None:
                    item['Time'] = {'S': time}
                if service is not None:
                    item['Service'] = {'S': service}
                if reminder_id is not None:
                    item['ReminderID'] = {'S': reminder_id}
            elif type_to_behavior == 'Offer':
                if offer_id is not None:
                    item['OfferID'] = {'S': offer_id}
                if description is not None:
                    item['Description'] = {'S': description}

            self.dynamodb.put_item(
                TableName=self.table_name,
                Item=item
            )
            print("Notification updated successfully.")
        except ClientError as e:
            print(f"Client error while updating notification: {e}")
        except Exception as e:
            print(f"Error updating notification: {e}")

    def subscribe_to_sns_topic(self, email):
        try:
            topic_arn = os.getenv('ARN')
            response = self.sns_client.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint=email
            )
            return response
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def send_offer_notification(self, email, beauty_salon_id, offer_id, description):
        try:
            subject = "New Offer Available"
            body = f"Hello,\n\nBeauty salon {beauty_salon_id} has a new offer: {description}."
            response = self.sns_client.publish(
                TopicArn=os.getenv('ARN'),
                Message=body,
                Subject=subject,
                MessageAttributes={
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    }
                }
            )
            return response
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def send_reminder_notification(self, email, user_id, beauty_salon_id, date, time, service):
        try:
            subject = "Appointment Reminder"
            body = f"Hello {user_id},\n\nThis is a reminder for your appointment at beauty salon {beauty_salon_id} on {date} at {time} for {service}."
            response = self.sns_client.publish(
                TopicArn=os.getenv('ARN'),
                Message=body,
                Subject=subject,
                MessageAttributes={
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    }
                }
            )
            return response
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def send_unsubscription_notification(self, email, user_id, beauty_salon_id):
        try:
            subject = "Unsubscription Confirmation"
            body = f"Hello {user_id},\n\nYou have successfully unsubscribed from beauty salon {beauty_salon_id}."
            response = self.sns_client.publish(
                TopicArn=os.getenv('ARN'),
                Message=body,
                Subject=subject,
                MessageAttributes={
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    }
                }
            )
            return response
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def send_offer_notification_to_all_followers(self, beauty_salon_id, offer_id, description):
        try:
            response = self.dynamodb.query(
                TableName=self.table_name,
                IndexName='TypeBehavior-BeautySalonID-index',
                KeyConditionExpression='TypeBehavior = :type_behavior AND BeautySalonID = :beauty_salon_id',
                ExpressionAttributeValues={
                    ':type_behavior': {'S': 'Subscription'},
                    ':beauty_salon_id': {'S': beauty_salon_id}
                }
            )
            
            for item in response.get('Items', []):
                if item.get('Active', {}).get('BOOL', False):  # Verificar si está activo
                    email = item['Email']['S']
                    self.send_offer_notification(email, beauty_salon_id, offer_id, description)
            
            return {"status": "success", "message": "Notifications sent to all active followers"}
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def get_recent_notifications_by_type_and_salon(self, type_behavior, beauty_salon_id):
        try:
            response = self.dynamodb.query(
                IndexName='TypeBehavior-BeautySalonID-index',  
                TableName=self.table_name,
                KeyConditionExpression='TypeBehavior = :type_behavior AND BeautySalonID = :beauty_salon_id',
                ExpressionAttributeValues={
                    ':type_behavior': {'S': type_behavior},
                    ':beauty_salon_id': {'S': beauty_salon_id}
                }
            )
            return response.get('Items', [])
        except self.dynamodb.exceptions.ValidationException as e:
            print(f"Validation error while getting recent notifications: {e}")
        except ClientError as e:
            print(f"Client error while getting recent notifications: {e}")
        except Exception as e:
            print(f"Error getting recent notifications: {e}")
        return []

