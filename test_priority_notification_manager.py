import unittest
from priority_notification_manager import PriorityNotificationManager, NotificationManager
import boto3
from unittest.mock import MagicMock, patch
import time

class TestNotificationManagers(unittest.TestCase):

    def setUp(self):
        self.standard_manager = NotificationManager()
        self.priority_manager = PriorityNotificationManager()
        # Purgar la cola SQS al inicio
        self.priority_manager.priority_queue.purge()
        
        # Test data
        self.user_id = 'TestUser123'
        self.email = 'nxhm2013@gmail.com'
        self.salon_id = 'TestSalon123' 
        self.offer_id = 'TestOffer123'
        self.description = 'Test offer description'
        self.date = '2023-12-01'
        self.time = '15:00'
        self.service = 'Test Service'
        self.reminder_id = 'TestReminder123'

    #@patch('boto3.client') # Sirve para simular llamadas externas
    def test_notification_manager_basic_flow(self):
        """Test basic notification flow with NotificationManager"""
        
        # Test update notifications
        subscription=self.standard_manager.update_notifications(
            self.user_id, 
            self.email,
            'Subscription',
            self.salon_id
        )
        print("subscription updated successfully",subscription)
        reminder=self.standard_manager.update_notifications(
            self.user_id,
            self.email, 
            'Reminder',
            self.salon_id,
            self.date,
            self.time,
            self.service,
            reminder_id=self.reminder_id
        )
        print("Reminder updated successfully",reminder)
        # Test offer notifications update
        offer = self.standard_manager.update_notifications(
            self.user_id,
            self.email,
            'Offer',
            self.salon_id,
            offer_id=self.offer_id,
            description=self.description
        )
        print("Offer notification updated successfully:", offer)
        # Test sending notifications
        offer_response = self.standard_manager.send_offer_notification(
            self.email,
            self.salon_id,
            self.offer_id, 
            self.description
        )
        
        reminder_response = self.standard_manager.send_reminder_notification(
            self.email,
            self.user_id,
            self.salon_id,
            self.date,
            self.time,
            self.service
        )

    def test_priority_queue_ordering(self):
        """Test complete notification flow: save to DynamoDB, queue and process"""
        
        # 1. Guardar notificaciones en DynamoDB
        reminder = self.standard_manager.update_notifications(
            self.user_id,
            self.email,
            'Reminder',
            self.salon_id,
            self.date,
            self.time,
            self.service,
            reminder_id=self.reminder_id
        )
        print("✅ Reminder saved to DynamoDB")
        
        offer = self.standard_manager.update_notifications(
            self.user_id,
            self.email,
            'Offer',
            self.salon_id,
            offer_id=self.offer_id,
            description=self.description
        )
        print("✅ Offer saved to DynamoDB")
        
        subscription = self.standard_manager.update_notifications(
            self.user_id,
            self.email,
            'Subscription',
            self.salon_id
        )
        print("✅ Subscription saved to DynamoDB")

        # 2. Recuperar notificaciones de DynamoDB y añadirlas a la cola
        notifications = [
            ('Reminder', self.standard_manager.get_recent_notifications_by_type_and_salon('Reminder', self.salon_id)),
            ('Offer', self.standard_manager.get_recent_notifications_by_type_and_salon('Offer', self.salon_id)),
            ('Subscription', self.standard_manager.get_recent_notifications_by_type_and_salon('Subscription', self.salon_id))
        ]

        print("\nEnviando notificaciones a SQS...")
        print("\n📥 Cantidad de Notificaciones:", len(notifications))
        for notification_type, items in notifications:
            for item in items:
                data = {
                    'user_id': self.user_id,
                    'beauty_salon_id': self.salon_id,
                }
                # Removemos email del diccionario data ya que lo pasaremos como argumento separado
                print(f"📩 Adding {notification_type} to queue - email {item['Email']['S']}")
                # Añadir datos específicos según el tipo
                if notification_type == 'Reminder':
                    data.update({
                        'date': item.get('Date', {}).get('S'),
                        'time': item.get('Time', {}).get('S'),
                        'service': item.get('Service', {}).get('S')
                    })
                elif notification_type == 'Offer':
                    data.update({
                        'offer_id': item.get('OfferID', {}).get('S'),
                        'description': item.get('Description', {}).get('S')
                    })

                self.priority_manager.add_notification_to_queue(notification_type, item['Email']['S'], **data)
                print(f"✅ {notification_type} added to queue")

        print("\nProcesando cola de prioridad...")
        self.priority_manager.process_queue()
        print("✅ Queue processed")

    def test_empty_queue(self):
        """Test behavior with empty queue using real queue operations"""
        # Crear nueva instancia y limpiar cola
        self.priority_manager = PriorityNotificationManager()
        while not self.priority_manager.priority_queue.empty():
            self.priority_manager.priority_queue.get()
        
        # Agregar un elemento de prueba
        test_data = {
            "user_id": self.user_id,
            "beauty_salon_id": self.salon_id,
            "date": "2024-03-01",
            "time": "10:00"
        }
        
        # Añadir a la cola
        self.priority_manager.add_notification_to_queue(
            "Reminder",
            self.email,
            **test_data
        )
        
        # Esperar un momento para que el mensaje se procese
        time.sleep(2)
        
        # Obtener y verificar el elemento
        item = self.priority_manager.priority_queue.get()
        self.assertIsNotNone(item)
        print("✅ Cola vacía manejada correctamente")

    def test_invalid_notification_type(self):
        """Test handling of invalid notification types"""
        
        self.priority_manager.add_notification_to_queue(
            "InvalidType",
            self.email
        )
        
        # Should use default low priority (10)
        priority = self.priority_manager.get_priority_for_type("InvalidType")
        self.assertEqual(priority, 10)
        print("✅ Tipo invalido manejado correctamente")

    def test_notification_priority_order_real(self):
        """Test que las notificaciones se procesan en orden de prioridad usando servicios reales"""
        # Purgar la cola SQS antes de la prueba
        print("\n🧹 Purga de cola antes de la prueba...")
        time.sleep(65) # Espera 60s porque es necesario esperar para poder purgar la cola
        self.priority_manager.priority_queue.purge()
        print("✅ Cola purgada")

        # Limpiar completamente la cola antes de empezar
        print("\n🧹 Limpiando cola...")
        while not self.priority_manager.priority_queue.empty():
            # Simplemente obtener y descartar los mensajes
            self.priority_manager.priority_queue.get()
        print("✅ Cola limpiada")

        # Conjunto único de notificaciones de prueba
        notifications = [
            {
                "type": "Subscription",
                "data": {
                    "user_id": self.user_id,
                    "beauty_salon_id": self.salon_id
                }
            },
            {
                "type": "Reminder",
                "data": {
                    "user_id": self.user_id,
                    "beauty_salon_id": self.salon_id,
                    "date": "2024-03-01",
                    "time": "10:00",
                    "service": "Corte de cabello"
                }
            },
            {
                "type": "Offer",
                "data": {
                    "beauty_salon_id": self.salon_id,
                    "offer_id": self.offer_id,
                    "description": "50% descuento"
                }
            }
        ]
        
        print("\n🔄 Iniciando prueba de priorización...")
        
        # Añadir cada notificación una única vez
        for notification in notifications:
            self.priority_manager.add_notification_to_queue(
                notification["type"],
                self.email,
                **notification["data"]
            )
            print(f"✅ Añadida notificación tipo {notification['type']}")
            time.sleep(1)  # Pequeña pausa entre mensajes
        
        time.sleep(2)  # Esperar a que todos los mensajes estén disponibles
        
        # Procesar y verificar orden
        processed = self.priority_manager.process_queue()
        # Ordenar por prioridad para comparación consistente
        processed.sort(key=lambda x: x[1])
        
        expected_order = [
            ("Reminder", 1),     # Prioridad alta
            ("Offer", 2),        # Prioridad media
            ("Subscription", 3)  # Prioridad baja
        ]
        
        print("\n📋 Verificando orden de prioridad...")
        print(f"Procesado: {processed}")
        print(f"Esperado: {expected_order}")
        
        self.assertEqual(processed, expected_order)
        print("✅ Orden de prioridad verificado correctamente")

if __name__ == '__main__':
    try:
        # Inicializar y crear tabla
        print("Iniciando creación de tabla notifications...")
        test = TestNotificationManagers()
        test.setUp()
        
        # Intentar crear la tabla usando el manager estándar
        response = test.standard_manager.create_notifications_table()
        
        if response:
            print("✅ Tabla creada exitosamente")
        else:
            print("⚠️ La tabla ya existe o hubo un error")
            
        # Ejecutar pruebas
        print("\nEjecutando pruebas...")
        unittest.main(argv=[''], verbosity=2, exit=False)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")