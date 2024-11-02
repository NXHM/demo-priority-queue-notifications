import unittest
import uuid  # Importar el módulo uuid
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
        
        # Generar user_id y salon_id únicos
        self.user_id = f'TestUser_{uuid.uuid4()}'  # Generar user_id único
        self.email = 'nxhm2013@gmail.com'
        self.salon_id = f'TestSalon_{uuid.uuid4()}'  # Generar salon_id único
        self.offer_id = f'TestOffer_{uuid.uuid4()}'
        self.description = 'Test offer description'
        self.date = '2023-12-01'
        self.time = '15:00'
        self.service = 'Test Service'
        self.reminder_id = f'TestReminder_{uuid.uuid4()}'

        # Limpiar datos de prueba previos en DynamoDB
        self._clean_dynamodb()

    def tearDown(self):
        # Limpiar datos de prueba después de las pruebas
        self._clean_dynamodb()

    def _clean_dynamodb(self):
        try:
            response = self.standard_manager.dynamodb.scan(
                TableName=self.standard_manager.table_name,
                FilterExpression="begins_with(UserID_TypeBehavior_BeautySalonID, :prefix)",
                ExpressionAttributeValues={
                    ":prefix": {"S": "TestUser_"}
                }
            )
            items = response.get('Items', [])
            for item in items:
                self.standard_manager.dynamodb.delete_item(
                    TableName=self.standard_manager.table_name,
                    Key={
                        'UserID_TypeBehavior_BeautySalonID': item['UserID_TypeBehavior_BeautySalonID'],
                        'Timestamp': item['Timestamp']
                    }
                )
            print(f"✅ Limpieza de DynamoDB completada. {len(items)} items eliminados.")
        except Exception as e:
            print(f"❌ Error limpiando DynamoDB: {str(e)}")

    def test_notification_manager_basic_flow(self):
        """Test basic notification flow with NotificationManager"""
        
        # Test update notifications
        subscription = self.standard_manager.update_notifications(
            self.user_id, 
            self.email,
            'Subscription',
            self.salon_id
        )
        print("subscription updated successfully", subscription)

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
        print("Reminder updated successfully", reminder)

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
            self.user_id,
            self.email,
            self.salon_id,
            self.offer_id, 
            self.description
        )
        print("Offer notification response:", offer_response)
        
        reminder_response = self.standard_manager.send_reminder_notification(
            self.email,
            self.user_id,
            self.salon_id,
            self.date,
            self.time,
            self.service
        )
        print("Reminder notification response:", reminder_response)

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

        # 2. Recuperar notificaciones y añadirlas a la cola
        notifications = [
            ('Reminder', self.standard_manager.get_recent_notifications_by_type_and_salon('Reminder', self.salon_id)),
            ('Offer', self.standard_manager.get_recent_notifications_by_type_and_salon('Offer', self.salon_id)),
            ('Subscription', self.standard_manager.get_recent_notifications_by_type_and_salon('Subscription', self.salon_id))
        ]

        print("\nEnviando notificaciones a SQS...")
        total_notifications = sum(len(items) for _, items in notifications)
        print(f"\n📥 Cantidad de Notificaciones: {total_notifications}")
        for notification_type, items in notifications:
            for item in items:
                # Extraer user_id de la clave compuesta
                user_id = item['UserID_TypeBehavior_BeautySalonID']['S'].split('#')[0]
                data = {
                    'beauty_salon_id': self.salon_id,
                }
                
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

                self.priority_manager.add_notification_to_queue(
                    notification_type, 
                    user_id,  # Pasar user_id explícitamente
                    item['Email']['S'], 
                    **data
                )
                print(f"✅ {notification_type} added to queue for user {user_id}")

        print("\nProcesando cola de prioridad...")
        processed = self.priority_manager.process_queue()
        print("✅ Queue processed")

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

    def test_empty_queue(self):
        """Test behavior with empty queue using real queue operations"""
        # Crear nueva instancia y limpiar cola
        self.priority_manager = PriorityNotificationManager()
        while not self.priority_manager.priority_queue.empty():
            self.priority_manager.priority_queue.get()
        
        # Agregar un elemento de prueba
        test_data = {
            "beauty_salon_id": self.salon_id,
            "date": "2024-03-01",
            "time": "10:00"
        }
        
        # Añadir a la cola pasando 'user_id' y 'email' correctamente
        self.priority_manager.add_notification_to_queue(
            "Reminder",
            self.user_id,
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
        
        # Añadir 'user_id' y 'email' faltantes
        self.priority_manager.add_notification_to_queue(
            "InvalidType",
            self.user_id,
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
                    "beauty_salon_id": self.salon_id
                }
            },
            {
                "type": "Reminder",
                "data": {
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
        
        # Añadir cada notificación pasando 'user_id' y 'email'
        for notification in notifications:
            self.priority_manager.add_notification_to_queue(
                notification["type"],
                self.user_id,  # Pasar user_id explícitamente
                self.email,
                **notification["data"]
            )
            print(f"✅ Añadida notificación tipo {notification['type']} para usuario {self.user_id}")
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