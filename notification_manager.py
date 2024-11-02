import boto3
import os
import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from botocore.config import Config
import time  

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
            raise ValueError("Invalid UserID (username)")
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
                'Active': {'BOOL': True},
                'Status': {'S': 'Pendiente'}  # Agregar estado 'Pendiente'
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

    def send_offer_notification(self, user_id, email, beauty_salon_id, offer_id, description):
        max_retries = 3
        retry_delay = 2  # segundos
        attempt = 0
        while attempt < max_retries:
            try:
                subject = "New Offer Available"
                body = f"Hello {user_id},\n\nBeauty salon {beauty_salon_id} has a new offer: {description}."
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
                # Actualizar el estado a 'Enviado' después de enviar la notificación
                self.update_notification_status(user_id, 'Offer', beauty_salon_id, 'Enviado')
                print(f"Offer notification sent to {user_id} and status updated.")
                return response
            except ClientError as e:
                attempt += 1
                print(f"❌ Error enviando oferta (Intento {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    print(f"🔄 Volviendo a intentar en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    # Actualizar el estado a 'Error' si hubo una excepción
                    self.update_notification_status(user_id, 'Offer', beauty_salon_id, 'Error')
                    return {"status": "error", "message": str(e)}

    def send_reminder_notification(self, email, user_id, beauty_salon_id, date, time_str, service):
        max_retries = 3
        retry_delay = 2  # segundos
        attempt = 0
        while attempt < max_retries:
            try:
                print(f"\n📤 Enviando recordatorio a {email}:")
                print(f"- Salón: {beauty_salon_id}")
                print(f"- Fecha: {date}")
                print(f"- Hora: {time_str}")
                
                subject = "Appointment Reminder"
                body = f"Hello {user_id},\n\nThis is a reminder for your appointment at beauty salon {beauty_salon_id} on {date} at {time_str} for {service}."
                
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
                print("✅ Notificación SNS enviada exitosamente")
                print(f"- MessageId: {response.get('MessageId')}")
                
                print("\n🔄 Actualizando estado en DynamoDB...")
                self.update_notification_status(user_id, 'Reminder', beauty_salon_id, 'Enviado')
                
                return response
            except ClientError as e:
                attempt += 1
                print(f"❌ Error enviando recordatorio (Intento {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    print(f"🔄 Volviendo a intentar en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    print("❌ Se alcanzó el número máximo de reintentos para enviar el recordatorio.")
                    self.update_notification_status(user_id, 'Reminder', beauty_salon_id, 'Error')
                    return {"status": "error", "message": str(e)}

    def update_notification_status(self, user_id, type_to_behavior, beauty_salon_id, status):
        try:
            # La clave compuesta debe usar user_id, no email
            user_key = f"{user_id}#{type_to_behavior}#{beauty_salon_id}"
            print(f"\n🔄 Actualizando estado de notificación:")
            print(f"- User ID: {user_id}")
            print(f"- Tipo: {type_to_behavior}")
            print(f"- Salón ID: {beauty_salon_id}")
            print(f"- Key compuesta: {user_key}")
            print(f"- Nuevo estado: {status}")
            time.sleep(3)
            # Obtener la notificación más reciente
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='UserID_TypeBehavior_BeautySalonID = :key',
                ExpressionAttributeValues={
                    ':key': {'S': user_key}
                },
                ScanIndexForward=False,  # Obtener el más reciente primero
                Limit=1
            )
            print(f"- Búsqueda de notificación: {'Items' in response}")
            print(f"- Respuesta de búsqueda: {response}")
            if response.get('Items'):
                timestamp = response['Items'][0]['Timestamp']['S']
                print(f"- Encontrada notificación con timestamp: {timestamp}")
                
                update_response = self.dynamodb.update_item(
                    TableName=self.table_name,
                    Key={
                        'UserID_TypeBehavior_BeautySalonID': {'S': user_key},
                        'Timestamp': {'S': timestamp}
                    },
                    UpdateExpression='SET #s = :status',
                    ExpressionAttributeNames={'#s': 'Status'},
                    ExpressionAttributeValues={':status': {'S': status}},
                    ReturnValues='ALL_NEW'  # Retorna el item actualizado
                )
                print(f"✅ Estado actualizado exitosamente a '{status}'")
                print(f"- Respuesta de actualización: {update_response}")
            else:
                print(f"❌ No se encontró la notificación para actualizar")
                
        except Exception as e:
            print(f"❌ Error actualizando estado: {str(e)}")
            raise

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
                    ':beauty_salon_id': {'S': beauty_salon_id},
                    ':status': {'S': 'Pendiente'}
                },
                FilterExpression='Status = :status'
            )
            
            for item in response.get('Items', []):
                if item.get('Active', {}).get('BOOL', False):
                    email = item['Email']['S']
                    # Extraer el user_id directamente de la clave compuesta
                    user_id = item['UserID_TypeBehavior_BeautySalonID']['S'].split('#')[0]
                    self.send_offer_notification(user_id, email, beauty_salon_id, offer_id, description)
            
            return {"status": "success", "message": "Notifications sent to all active followers"}
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def get_recent_notifications_by_type_and_salon(self, type_behavior, beauty_salon_id):
        try:
            # Consultar solo las notificaciones pendientes
            response = self.dynamodb.query(
                TableName=self.table_name,
                IndexName='TypeBehavior-BeautySalonID-index',
                KeyConditionExpression='TypeBehavior = :type_behavior AND BeautySalonID = :beauty_salon_id',
                ExpressionAttributeValues={
                    ':type_behavior': {'S': type_behavior},
                    ':beauty_salon_id': {'S': beauty_salon_id},
                    ':status': {'S': 'Pendiente'},  # Solo notificaciones pendientes
                    ':active': {'BOOL': True}  # Solo notificaciones activas
                },
                FilterExpression='#s = :status AND Active = :active',
                ExpressionAttributeNames={
                    '#s': 'Status'
                }
            )
            
            items = response.get('Items', [])
            print(f"Encontradas {len(items)} notificaciones pendientes de tipo {type_behavior}")
            return items
            
        except ClientError as e:
            print(f"Client error while getting recent notifications: {e}")
        except Exception as e:
            print(f"Error getting recent notifications: {e}")
            print(f"Error getting recent notifications: {e}")
        return []


        try:
            # Buscar en la tabla el user_id correspondiente al email
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression='Email = :email',
                ExpressionAttributeValues={
                    ':email': {'S': email}
                },
                ProjectionExpression='UserID_TypeBehavior_BeautySalonID',
                Limit=1
            )
            
            if response.get('Items'):
                # Extraer el user_id de la clave compuesta
                user_id = response['Items'][0]['UserID_TypeBehavior_BeautySalonID']['S'].split('#')[0]
                return user_id
            
            return None
        except Exception as e:
            print(f"Error getting user_id for email {email}: {e}")
            return None


        return []

