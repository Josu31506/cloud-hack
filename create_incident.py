import boto3
import os
from datetime import datetime
import uuid
import json

def create_incident(event, context):
    print("Event recibido en create_incident:", event)  # Log en CloudWatch

    try:
        # Obtener el token desde el header Authorization (formato Bearer <token>)
        token = event['headers'].get('Authorization').replace('Bearer ', '')  
        if not token:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Faltan datos en los headers'})  # Convertir a JSON
            }

        # Obtener el nombre de la tabla de tokens desde las variables de entorno
        tokens_table_name = os.environ['DYNAMODB_TABLE_TOKENS']

        dynamodb = boto3.resource('dynamodb')
        tokens_table = dynamodb.Table(tokens_table_name)

        # Buscar el token en la tabla de tokens
        response = tokens_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(token)
        )

        if 'Items' not in response or len(response['Items']) == 0:
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Token no válido o no encontrado'})  # Convertir a JSON
            }

        token_item = response['Items'][0]
        user_role = token_item['role']
        user_id = token_item['user_id']  # Se asume que el token tiene un campo `user_id`

        # Verificar si el usuario es un estudiante
        if user_role != 'estudiante':
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Solo los estudiantes pueden crear incidencias'})  # Convertir a JSON
            }

        # Crear la incidencia
        # Asegurarse de que el cuerpo esté en formato dict (si es un string JSON, lo convertimos)
        body = event['body']
        if isinstance(body, str):  # Si el cuerpo es un string JSON, lo convertimos
            body = json.loads(body)

        descripcion = body.get('descripcion')
        tipo_incidencia = body.get('tipo_incidencia')
        ubicacion = body.get('ubicacion')
        urgencia = body.get('urgencia')

        if not descripcion or not tipo_incidencia or not ubicacion or not urgencia:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Faltan datos en el cuerpo de la solicitud'})  # Convertir a JSON
            }

        # Generar un ID único para la incidencia
        incidente_id = str(uuid.uuid4())

        # Almacenar la incidencia en DynamoDB
        incidencias_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_INCIDENCIAS'])
        incidencia_data = {
            'incidente_id': incidente_id,
            'descripcion': descripcion,
            'tipo_incidencia': tipo_incidencia,
            'ubicacion': ubicacion,
            'urgencia': urgencia,
            'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'fase': 'pendiente',  # Fase inicial
            'gravedad': body.get('gravedad', 'media'),  # Usamos "media" por defecto
            'reportado_por': user_id  # Agregamos el usuario que reportó la incidencia
        }

        incidencias_table.put_item(Item=incidencia_data)

        # Crear notificación
        notificacion_id = str(uuid.uuid4())
        fecha_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Notificación: dependiendo de si es estudiante o no
        if user_role == 'estudiante':
            # El estudiante será notificado solo de la incidencia que creó
            mensaje = f'Incidencia creada por usted: {tipo_incidencia} en {ubicacion}. Gravedad: {incidencia_data["gravedad"]}.'
            destinatario = user_id  # Notificación al propio usuario
        else:
            # Los roles no estudiantes reciben una notificación por cada incidencia creada
            mensaje = f'Nueva incidencia generada: {tipo_incidencia} en {ubicacion}. Gravedad: {incidencia_data["gravedad"]}.'
            destinatario = user_role  # Notificación a todos los usuarios con este rol

        notificacion_data = {
            'notificacion_id': notificacion_id,
            'incidente_id': incidente_id,
            'mensaje': mensaje,
            'fecha': fecha_actualizacion,
            'status': 'pendiente',
            'destinatario': destinatario  # Agregamos el destinatario (usuario o rol)
        }

        # Almacenar la notificación en DynamoDB
        notificaciones_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NOTIFICACIONES'])
        notificaciones_table.put_item(Item=notificacion_data)

        # Guardar la notificación en un archivo S3
        s3 = boto3.client('s3')
        bucket_name = os.environ['NOTIFICACIONES_BUCKET_NAME']
        file_name = f"notificaciones/{notificacion_id}.json"
        
        # Convertir la notificación a JSON
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json.dumps(notificacion_data),  # Convertido a JSON
            ContentType='application/json'
        )
        
        # Imprimir el JSON de la notificación
        print(f'Notificación generada: {json.dumps(notificacion_data)}')

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Incidencia y notificación creada con éxito', 'incidente_id': incidente_id})  # Convertir a JSON
        }

    except Exception as e:
        print("Error en create_incident:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})  # Convertir a JSON
        }