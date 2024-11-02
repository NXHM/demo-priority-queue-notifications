from notification_manager import NotificationManager
from distributed_priority_queue import DistributedPriorityQueue  # Importar la cola de prioridad distribuida
import time  # Importar time para delays en reintentos

class PriorityNotificationManager(NotificationManager):
    def __init__(self):
        super().__init__()
        self.priority_queue = DistributedPriorityQueue()  # Usar la cola de prioridad distribuida

    def get_priority_for_type(self, notification_type):
        # Definir las prioridades según el tipo de notificación
        priority_map = {
            "Reminder": 1,
            "Offer": 2,
            "Subscription": 3
        }
        # Asignar la prioridad en función del tipo de notificación
        return priority_map.get(notification_type, 10)  # Por defecto, prioridad baja si no se encuentra el tipo

    def add_notification_to_queue(self, notification_type, user_id, email, **kwargs):
        # Verificar si la notificación ya está en la cola para evitar duplicados
        existing = self.check_existing_notification(notification_type, user_id, **kwargs)
        if existing:
            print(f"⚠️ Notificación {notification_type} para {user_id} ya está en la cola.")
            return
        priority_level = self.get_priority_level(notification_type)
        self.priority_queue.put(priority_level, (notification_type, user_id, email, kwargs))
        print(f"✅ {notification_type} añadido a la cola '{priority_level}'")

    def get_priority_level(self, notification_type):
        priority_map = {
            "Reminder": "high",
            "Offer": "medium",
            "Subscription": "low"
        }
        return priority_map.get(notification_type, "low")

    def check_existing_notification(self, notification_type, user_id, **kwargs):
        try:
            beauty_salon_id = kwargs.get('beauty_salon_id')
            if not beauty_salon_id:
                return False

            # Verificar si la notificación ya fue enviada usando la clave compuesta correcta
            composite_key = f"{user_id}#{notification_type}#{beauty_salon_id}"
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='UserID_TypeBehavior_BeautySalonID = :key',
                ExpressionAttributeValues={
                    ':key': {'S': composite_key},
                    ':enviado': {'S': 'Enviado'}
                },
                FilterExpression='#s = :enviado',
                ExpressionAttributeNames={
                    '#s': 'Status'
                },
                ScanIndexForward=False,
                Limit=1
            )
            
            return len(response.get('Items', [])) > 0
            
        except Exception as e:
            print(f"Error checking existing notification: {e}")
            return False

    def process_queue(self):
        processed_items = []
        print("\n🔄 Iniciando procesamiento de colas por prioridad...")

        for priority_level in ['high', 'medium', 'low']:
            print(f"\n📥 Procesando cola '{priority_level}'...")
            while True:
                message = self.priority_queue.get()
                if message is None:
                    print(f"✅ Cola '{priority_level}' procesada.")
                    break

                msg_priority_level, data = message
                notification_type, user_id, email, notification_data = data
                print(f"\n📨 Procesando mensaje:")
                print(f"- Tipo: {notification_type}")
                print(f"- Prioridad: {msg_priority_level}")
                print(f"- Usuario: {user_id}")
                print(f"- Email: {email}")
                print(f"- Datos: {notification_data}")
                
                # Verificar si la notificación ya fue enviada antes de procesarla
                if self.check_existing_notification(notification_type, user_id, **notification_data):
                    print(f"⚠️ Notificación {notification_type} para {user_id} ya fue enviada anteriormente")
                    continue
                
                processed_items.append((notification_type, msg_priority_level))
                
                try:
                    # Procesar según tipo
                    if notification_type == "Reminder":
                        print(f"\n📅 Enviando recordatorio...")
                        self.send_reminder_notification(user_id, email, **notification_data)
                    elif notification_type == "Offer":
                        print(f"\n🏷️ Enviando oferta...")
                        self.send_offer_notification(user_id, email, **notification_data)
                    elif notification_type == "Subscription":
                        print(f"\n📫 Procesando suscripción...")
                        print(f"Subscription processed for {user_id}")
                        
                    print(f"✅ Procesado {notification_type} con prioridad {msg_priority_level}")
                except Exception as e:
                    print(f"❌ Error procesando notificación: {str(e)}")

        print(f"\n✅ Procesamiento de colas completado. Items procesados: {len(processed_items)}")
        return processed_items

    def send_reminder_notification(self, user_id, email, **data):
        max_retries = 3
        retry_delay = 2  # segundos
        attempt = 0
        while attempt < max_retries:
            try:
                # Llamar al método de la clase base para enviar recordatorios
                super().send_reminder_notification(
                    email,
                    user_id,  # Pasar user_id directamente
                    beauty_salon_id=data.get("beauty_salon_id"),
                    date=data.get("date"),
                    time_str=data.get("time"),  # Agregar esta línea
                    service=data.get("service")
                )
                return  # Salir si el envío fue exitoso
            except Exception as e:
                attempt += 1
                print(f"❌ Error enviando recordatorio (Intento {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    print(f"🔄 Volviendo a intentar en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    print("❌ Se alcanzó el número máximo de reintentos para enviar el recordatorio.")
                    raise

    def send_offer_notification(self, user_id, email, **data):
        max_retries = 3
        retry_delay = 2  # segundos
        attempt = 0
        while attempt < max_retries:
            try:
                # Llamar al método de la clase base para enviar ofertas
                super().send_offer_notification(
                    user_id,  # Pasar user_id directamente
                    email,
                    beauty_salon_id=data.get("beauty_salon_id"),
                    offer_id=data.get("offer_id"),
                    description=data.get("description")
                )
                return  # Salir si el envío fue exitoso
            except Exception as e:
                attempt += 1
                print(f"❌ Error enviando oferta (Intento {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    print(f"🔄 Volviendo a intentar en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    print("❌ Se alcanzó el número máximo de reintentos para enviar la oferta.")
                    raise
