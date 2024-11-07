# Sistema de Notificaciones con AWS SQS

## Descripción General

Este sistema maneja notificaciones para la aplicación InStudio. Es un servicio de notificaciones que, utilizan AWS SQS para la gestión de prioridades, AWS SNS para el envío de las notificaciones y DynamoDB para el almancenamiento de la información de las notificaciones. El sistema procesa tres tipos de notificaciones:

1. **Recordatorios**: Alta prioridad debido a que ello puede marcar una gran diferencia en la experiencia del usuario al querer usar nuevamente la plataforma. Al recibir prioritariamente los recordatorios, puede confiar que le llegaran los recordatorios.
   - Notificaciones de citas programadas
   - Incluye detalles de fecha, hora y servicio

2. **Ofertas**: Media prioridad debido a que es una notificación más informativa con respecto a las salones de belleza que sigue el usuario y el perderse una, es más una oportunidad pérdida que un servicio pagado pérdido.
   - Promociones de salones de belleza
   - Enviadas a usuarios suscritos

3. **Suscripciones**: Baja prioridad porque es informativa. Solo permite a que el usuario se suscriba par arecibir notificaciones en general, puediendo decidir si desuscribirse o no. No es tan relevante como las demás, pues sería más una preferencia del usuario de recibir notificaciones o no.
   - Gestión de suscripciones de usuarios
   - Confirmaciones y actualizaciones

## Arquitectura del demo

El sistema utiliza:

- **AWS SQS**: Cola de mensajes para priorización
- **AWS SNS**: Envío de notificaciones por email
- **AWS DynamoDB**: Almacenamiento de datos de notificaciones

### Flujo de Trabajo Actualizado

1. Se genera una notificación (Reminder, Offer o Subscription)
2. La notificación se guarda en DynamoDB a través de NotificationManager con su estado correspondiente
3. Se recupera la notificación de DynamoDB
4. Se envía a la cola de priorización (SQS) a través de PriorityNotificationManager
5. Las notificaciones se procesan según su prioridad:
   - Reminders: Prioridad 1 (Alta)
   - Offers: Prioridad 2 (Media)
   - Subscriptions: Prioridad 3 (Baja)
6. Se envían las notificaciones vía SNS según el orden de prioridad y se actualizan los estados de las notificaciones
7. Se mantiene almacenado el registro de envíos en DynamoDB

## Comparación de Alternativas

### AWS SQS vs RabbitMQ vs Apache Kafka

- **AWS SQS**:
- **Ventajas**:
  - ✅ Integración nativa con AWS
  - ✅ Escalado automático (no gestión de servidores)
  - ✅ Capa gratuita disponible
  - ✅ Más simple de implementar
  - ✅ Es distribuido
- **Desventajas**:
  - ❌ Menor control sobre la infraestructura
  - ❌ Mayor Latencia

- **RabbitMQ**:
- **Ventajas**:
  - ✅ Mayor control y personalización
  - ✅ Mejor rendimiento en local
- **Desventajas**:
  - ❌ Requiere mantenimiento
  - ❌ Necesita infraestructura propia

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
- Mantenimiento y recursos necesarios

**Decisión**:
Se elige AWS SQS.

**Justificación**:
AWS SQS ha sido seleccionado debido a su facilidad de uso en sistemas distribuidos y su capacidad de garantizar la entrega de mensajes sin necesidad de gestionar servidores, a pesar de tener una latencia ligeramente mayor. Además, su simplicidad de implementación y menor costo operativo lo hacen más adecuado para cargas moderadas, mientras que Redis, RabbitMQ y Apache Kafka requieren más mantenimiento y recursos, aunque ofrecen ventajas en latencia y personalización.

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

#### NotificationManager - Clase padre

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

#### PriorityNotificationManager - Clase Hija

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


# Fuentes

- https://docs.aws.amazon.com/decision-guides/latest/sns-or-sqs-or-eventbridge/sns-or-sqs-or-eventbridge.html
- https://aws.amazon.com/es/sqs/pricing/
- https://docs.aws.amazon.com/es_es/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs/client/purge_queue.html
- https://github.com/boto/botocore/issues/458#issuecomment-1358117993
- https://joelmccoy.medium.com/python-and-boto3-performance-adventures-synchronous-vs-asynchronous-aws-api-interaction-22f625ec6909

# Info extra 
- https://youtu.be/UPkOsXKG4ns?si=yjcgrBtPtFW0aaW_
- https://youtu.be/x4k1XEjNzYQ?si=Iab3LFK3MokYGGlm