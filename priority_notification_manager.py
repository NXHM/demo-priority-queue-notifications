from queue import PriorityQueue
from notification_manager import NotificationManager
class PriorityNotificationManager(NotificationManager):
    def __init__(self):
        super().__init__()
        self.priority_queue = PriorityQueue()

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
        priority = self.get_priority_for_type(notification_type)
        self.priority_queue.put((priority, notification_type, email, kwargs))

    def process_queue(self):
        while not self.priority_queue.empty():
            priority, notification_type, email, data = self.priority_queue.get()
            if notification_type == "Reminder":
                self.send_reminder_notification(email, **data)
            elif notification_type == "Offer":
                self.send_offer_notification(email, **data)
            elif notification_type == "Subscription":
                # Procesar suscripciones si se agrega lógica
                print(f"Subscription processed for {email}")
            # Agregar más casos según el tipo de notificación
            print(f"Processed {notification_type} with priority {priority}")

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
