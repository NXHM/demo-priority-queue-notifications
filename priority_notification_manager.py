from notification_manager import NotificationManager
from distributed_priority_queue import DistributedPriorityQueue  # Importar la cola de prioridad distribuida

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

    def add_notification_to_queue(self, notification_type, email, **kwargs):
        # Verificar si la notificación ya está en la cola para evitar duplicados
        existing = self.check_existing_notification(notification_type, email, **kwargs)
        if existing:
            print(f"⚠️ Notificación {notification_type} para {email} ya está en la cola.")
            return
        priority = self.get_priority_for_type(notification_type)
        self.priority_queue.put((priority, notification_type, email, kwargs))
        print(f"✅ {notification_type} añadido a la cola")

    def check_existing_notification(self, notification_type, email, **kwargs):
        try:
            beauty_salon_id = kwargs.get('beauty_salon_id')
            if not beauty_salon_id:
                return False

            # Verificar si la notificación ya fue enviada
            user_key = f"{email}#{notification_type}#{beauty_salon_id}"
            response = self.dynamodb.query(
                TableName=self.table_name,
                KeyConditionExpression='UserID_TypeBehavior_BeautySalonID = :key',
                ExpressionAttributeValues={
                    ':key': {'S': user_key},
                    ':enviado': {'S': 'Enviado'}
                },
                FilterExpression='#s = :enviado',
                ExpressionAttributeNames={
                    '#s': 'Status'
                },
                ScanIndexForward=False,
                Limit=1
            )
            
            # Si encontramos una notificación ya enviada, no la procesamos de nuevo
            return len(response.get('Items', [])) > 0
            
        except Exception as e:
            print(f"Error checking existing notification: {e}")
            return False

    def process_queue(self):
        processed_items = []
        while not self.priority_queue.empty():
            message = self.priority_queue.get()
            if message is None:
                continue
                
            priority, notification_type, email, data = message
            
            # Verificar si la notificación ya fue enviada antes de procesarla
            if self.check_existing_notification(notification_type, email, **data):
                print(f"⚠️ Notificación {notification_type} para {email} ya fue enviada anteriormente")
                continue
                
            processed_items.append((notification_type, priority))
            
            # Procesar según tipo
            if notification_type == "Reminder":
                self.send_reminder_notification(email, **data)
            elif notification_type == "Offer":
                self.send_offer_notification(email, **data)
            elif notification_type == "Subscription":
                print(f"Subscription processed for {email}")
                
            print(f"Processed {notification_type} with priority {priority}")
            
        return processed_items

    def send_reminder_notification(self, email, **data):
        # Llamar al método de la clase base para enviar recordatorios
        super().send_reminder_notification(
            email,
            user_id=data.get("user_id"),
            beauty_salon_id=data.get("beauty_salon_id"),
            date=data.get("date"),
            time=data.get("time"),
            service=data.get("service")
        )

    def send_offer_notification(self, email, **data):
        # Llamar al método de la clase base para enviar ofertas
        super().send_offer_notification(
            email,
            beauty_salon_id=data.get("beauty_salon_id"),
            offer_id=data.get("offer_id"),
            description=data.get("description")
        )
