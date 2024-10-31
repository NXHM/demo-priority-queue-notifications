# Sistema de Notificaciones con AWS SQS

## Descripción General

Este sistema maneja notificaciones para un servicio de salones de belleza, utilizando AWS SQS para la gestión de prioridades. El sistema procesa tres tipos de notificaciones:

1. **Recordatorios** (Alta prioridad)
   - Notificaciones de citas programadas
   - Incluye detalles de fecha, hora y servicio

2. **Ofertas** (Media prioridad)
   - Promociones de salones de belleza
   - Enviadas a usuarios suscritos

3. **Suscripciones** (Baja prioridad)
   - Gestión de suscripciones de usuarios
   - Confirmaciones y actualizaciones

## Arquitectura del demo

El sistema utiliza:

- **AWS SQS**: Cola de mensajes para priorización
- **AWS SNS**: Envío de notificaciones por email
- **AWS DynamoDB**: Almacenamiento de datos de notificaciones

### Flujo de Trabajo

1. Las notificaciones se envían a SQS con prioridades
2. El sistema procesa mensajes según prioridad
3. Se envían notificaciones vía SNS
4. Se almacena el registro en DynamoDB

## Comparación de Alternativas

### AWS SQS vs RabbitMQ

- **AWS SQS**:
  - ✅ Serverless y totalmente administrado
  - ✅ Integración nativa con AWS
  - ✅ Escalado automático
  - ✅ Capa gratuita disponible
  - ❌ Menor control sobre la infraestructura

- **RabbitMQ**:
  - ✅ Mayor control y personalización
  - ✅ Mejor rendimiento en local
  - ❌ Requiere mantenimiento
  - ❌ Necesita infraestructura propia

### Comparación de Alternativas

#### AWS SQS vs Redis vs Apache Kafka

**AWS SQS**

- **Ventajas**:
    - ✅ No requiere gestión de servidores
    - ✅ Mejor para sistemas distribuidos
    - ✅ Garantía de entrega de mensajes
    - ✅ Más simple de implementar
    - ✅ Mejor para cargas moderadas
    - ✅ Menor costo operativo
- **Desventajas**:
    - ❌ Latencia ligeramente mayor
    - ❌ Menos adecuado para big data

**Redis**

- **Ventajas**:
    - ✅ Menor latencia
    - ✅ Más versátil (no solo colas)
- **Desventajas**:
    - ❌ Requiere configuración y mantenimiento
    - ❌ Menos robusto para sistemas distribuidos

**Apache Kafka**

- **Ventajas**:
    - ✅ Mejor para grandes volúmenes
    - ✅ Excelente para streaming
- **Desventajas**:
    - ❌ Complejo de mantener
    - ❌ Requiere más recursos

**Métricas de Decisión**:

- Latencia
- Gestión de servidores
- Versatilidad
- Robustez para sistemas distribuidos
- Simplicidad de implementación
- Costo operativo
- Adecuación para big data
- Mantenimiento y recursos necesarios

**Decisión**:
Se elige AWS SQS.

**Justificación**:
AWS SQS es preferido debido a su facilidad de uso en sistemas distribuidos y su capacidad de garantizar la entrega de mensajes sin necesidad de gestionar servidores, a pesar de tener una latencia ligeramente mayor. Además, su simplicidad de implementación y menor costo operativo lo hacen más adecuado para cargas moderadas, mientras que Redis y Apache Kafka requieren más mantenimiento y recursos, aunque ofrecen ventajas en latencia y manejo de grandes volúmenes respectivamente.

## Flujo Detallado del Sistema

### 1. Flujo de Notificaciones
1. El usuario genera una notificación (Reminder, Offer o Subscription)
2. La notificación se guarda en DynamoDB a través de NotificationManager
3. Se recupera la notificación de DynamoDB
4. Se envía a la cola de priorización (SQS) a través de PriorityNotificationManager
5. Las notificaciones se procesan según su prioridad:
   - Reminders: Prioridad 1 (Alta)
   - Offers: Prioridad 2 (Media)
   - Subscriptions: Prioridad 3 (Baja)
6. Se envían las notificaciones vía SNS según el orden de prioridad

### 2. Clases Principales

#### NotificationManager
- **Propósito**: Gestión básica de notificaciones y persistencia
- **Funcionalidades**:
  - Crear/actualizar notificaciones en DynamoDB
  - Enviar notificaciones vía SNS
  - Gestionar suscripciones
  - Consultar notificaciones por tipo y salón
- **Métodos principales**:
  - `update_notifications()`: Guarda notificaciones en DynamoDB
  - `send_offer_notification()`: Envía ofertas
  - `send_reminder_notification()`: Envía recordatorios
  - `get_recent_notifications_by_type_and_salon()`: Consulta notificaciones

#### PriorityNotificationManager
- **Propósito**: Gestión de prioridades de notificaciones
- **Hereda de**: NotificationManager
- **Funcionalidades**:
  - Asignar prioridades a notificaciones
  - Gestionar cola de prioridades
  - Procesar notificaciones según prioridad
- **Métodos principales**:
  - `add_notification_to_queue()`: Añade a cola SQS
  - `process_queue()`: Procesa notificaciones priorizadas
  - `get_priority_for_type()`: Asigna prioridades

#### DistributedPriorityQueue
- **Propósito**: Interfaz con AWS SQS
- **Funcionalidades**:
  - Gestionar mensajes en SQS
  - Mantener orden por prioridad
  - Garantizar entrega de mensajes
- **Métodos principales**:
  - `put()`: Envía mensaje a SQS
  - `get()`: Recupera mensaje más prioritario
  - `empty()`: Verifica si la cola está vacía

### 3. Diagrama de Flujo

# Fuentes

- https://docs.aws.amazon.com/decision-guides/latest/sns-or-sqs-or-eventbridge/sns-or-sqs-or-eventbridge.html
- https://aws.amazon.com/es/sqs/pricing/
- https://docs.aws.amazon.com/es_es/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html

# Info extra 
- https://youtu.be/UPkOsXKG4ns?si=yjcgrBtPtFW0aaW_
- https://youtu.be/x4k1XEjNzYQ?si=Iab3LFK3MokYGGlm