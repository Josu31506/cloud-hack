import boto3
import os
from datetime import datetime
import json
import uuid  # Asegúrate de agregar esta línea

def update_incident(event, context):
    print("Event recibido en update_incident:", event)  # Log en CloudWatch

    try:
        # Obtener el token desde el header Authorization (formato Bearer <token>)
        token = event['headers'].get('Authorization').replace('Bearer ', '')  
        if not token:
            return {
                'statusCode': 400,
                'body': {'error': 'Faltan datos en los headers'}
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
                'body': 'Token no válido o no encontrado'
            }

        token_item = response['Items'][0]
        user_role = token_item['role']

        # Verificar si el usuario tiene el rol adecuado (no estudiante)
        if user_role == 'estudiante':
            return {
                'statusCode': 403,
                'body': 'Solo los roles no estudiantes pueden actualizar incidencias'
            }

        # Obtener el ID de la incidencia desde el cuerpo de la solicitud
        body = event['body']
        incidente_id = body.get('incidente_id')
        nueva_fase = body.get('fase')  # Fase que queremos actualizar
        tiempo_resolucion = body.get('tiempo_resolucion')  # Si ya se resolvió, se guarda el tiempo de resolución

        if not incidente_id or not nueva_fase:
            return {
                'statusCode': 400,
                'body': {'error': 'Faltan datos en el cuerpo de la solicitud'}
            }

        # Actualizar la incidencia
        incidencias_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_INCIDENCIAS'])
        update_data = {'fase': nueva_fase}

        if nueva_fase == 'resuelta' and tiempo_resolucion:
            update_data['tiempo_resolucion'] = tiempo_resolucion  # Actualizar el tiempo de resolución

        incidencias_table.update_item(
            Key={'incidente_id': incidente_id},
            UpdateExpression="SET fase = :fase, tiempo_resolucion = :tiempo_resolucion",
            ExpressionAttributeValues={
                ':fase': nueva_fase,
                ':tiempo_resolucion': tiempo_resolucion if nueva_fase == 'resuelta' else None
            }
        )

        # Crear la notificación
        notificacion_id = str(uuid.uuid4())  # Usar uuid para generar un ID único
        fecha_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Obtener el email del estudiante (quien creó la incidencia) desde la tabla de incidencias
        incidencia_response = incidencias_table.get_item(Key={'incidente_id': incidente_id})
        creador_incidente = incidencia_response['Item'].get('reportado_por')

        if not creador_incidente:
            return {
                'statusCode': 404,
                'body': {'error': 'Incidencia no encontrada o sin creador asociado'}
            }

        # Crear mensaje de notificación
        mensaje = f'La incidencia {incidente_id} ha sido actualizada a la fase {nueva_fase}.'

        # Si la fase es "resuelta", se notifica al estudiante que la creó
        notificacion_data = {
            'notificacion_id': notificacion_id,
            'incidente_id': incidente_id,
            'mensaje': mensaje,
            'fecha': fecha_actualizacion,
            'status': 'pendiente',
            'destinatario': creador_incidente  # Notificación específica para el estudiante que reportó
        }

        # Almacenar la notificación en DynamoDB
        notificaciones_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NOTIFICACIONES'])
        notificaciones_table.put_item(Item=notificacion_data)

        # Guardar la notificación en un archivo S3 (subcarpeta con el email del estudiante)
        s3 = boto3.client('s3')
        bucket_name = os.environ['NOTIFICACIONES_BUCKET_NAME']
        file_name = f"notificaciones/{creador_incidente}/{notificacion_id}.json"

        # Convertir la notificación a JSON
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json.dumps(notificacion_data),
            ContentType='application/json'
        )

        # Imprimir el JSON de la notificación
        print(f'Notificación generada: {json.dumps(notificacion_data)}')

        return {
            'statusCode': 200,
            'body': {'message': 'Incidencia actualizada y notificación generada con éxito', 'incidente_id': incidente_id}
        }

    except Exception as e:
        print("Error en update_incident:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }