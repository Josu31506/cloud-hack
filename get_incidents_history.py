import boto3
import os
from datetime import datetime

def get_incidents_history(event, context):
    print("Event recibido en get_incidents_history:", event)  # Log en CloudWatch

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

        # Verificar si el usuario no es un estudiante
        if user_role == 'estudiante':
            return {
                'statusCode': 403,
                'body': 'Solo los roles no estudiantes pueden ver el historial'
            }

        # Si no es estudiante, permitimos ver el historial de incidencias
        incidencias_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_INCIDENCIAS'])

        response = incidencias_table.scan()  # Recuperar todas las incidencias
        return {
            'statusCode': 200,
            'body': response['Items']
        }

    except Exception as e:
        print("Error en get_incidents_history:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }