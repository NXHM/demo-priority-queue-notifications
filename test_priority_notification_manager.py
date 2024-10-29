from priority_notification_manager import PriorityNotificationManager, NotificationManager

def test_notification_manager():
    # Crear instancia de NotificationManager
    manager = NotificationManager()
    user_id = 'NicoGod2'
    email = 'nxhm2013@gmail.com'
    beauty_salon_id = 'Salon123'
    offer_id = 'Offer123'
    description = '50% off on all services'
    date = '2023-10-01'
    time = '10:00 AM'
    service = 'Haircut'
    reminder_id = 'Reminder123'

    # Crear la tabla de notificaciones (descomentar si es necesario crear la tabla)
    # manager.create_notifications_table()

    # Actualizar notificaciones
    manager.update_notifications(user_id, email, 'Subscription', beauty_salon_id)
    manager.update_notifications(user_id, email, 'Reminder', beauty_salon_id, date, time, service, reminder_id=reminder_id)
    manager.update_notifications(user_id, email, 'Offer', beauty_salon_id, offer_id=offer_id, description=description)

    # Send offer notification
    offer_response = manager.send_offer_notification(email, beauty_salon_id, offer_id, description)
    print(f"Offer response: {offer_response}")

    # Send reminder notification
    reminder_response = manager.send_reminder_notification(email, user_id, beauty_salon_id, date, time, service)
    print(f"Reminder response: {reminder_response}")

    # Send offer notification to all followers
    manager.send_offer_notification_to_all_followers(beauty_salon_id, offer_id, description)

    recent_offers = manager.get_recent_notifications_by_type_and_salon('Offer', beauty_salon_id)
    print(f"Recent offers: {recent_offers}")

    # Obtener notificaciones recientes por tipo y salón
    recent_notifications = manager.get_recent_notifications_by_type_and_salon('Reminder', beauty_salon_id)
    print(f"Recent notifications: {recent_notifications}")

def test_priority_notification_manager():
    manager = PriorityNotificationManager()

    # Añadir notificaciones a la cola con datos adicionales
    manager.add_notification_to_queue(
        "Reminder", "user1@example.com",
        user_id="User1", beauty_salon_id="SalonA", date="2023-11-01", time="10:30 AM", service="Haircut"
    )
    manager.add_notification_to_queue(
        "Offer", "user2@example.com",
        beauty_salon_id="SalonB", offer_id="Offer456", description="30% off on manicure"
    )
    manager.add_notification_to_queue(
        "Subscription", "user3@example.com",
        user_id="User3", beauty_salon_id="SalonC"
    )

    # Probar con un tipo de notificación desconocido
    manager.add_notification_to_queue(
        "Unknown", "user4@example.com"
    )

    # Procesar las notificaciones en orden de prioridad
    manager.process_queue()

def main():
    print("Testing NotificationManager")
    test_notification_manager()

    print("\nTesting PriorityNotificationManager")
    test_priority_notification_manager()

if __name__ == "__main__":
    main()
