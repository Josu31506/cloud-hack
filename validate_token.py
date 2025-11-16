import boto3
import os  # Para acceder a las variables de entorno
from datetime import datetime

def validate_token(event, context):
    print("Event recibido en validate_token:", event)  # Log en CloudWatch

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

        # Ahora necesitamos hacer una consulta usando el token como tenant_id
        response = tokens_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(token)
        )

        # Verificar si existe el token
        if 'Items' not in response or len(response['Items']) == 0:
            return {
                'statusCode': 403,
                'body': 'Token no válido o no encontrado'
            }

        # Obtener el primer item (se supone que el token es único para cada usuario)
        token_item = response['Items'][0]
        
        # Validar si el token ha expirado
        expires = token_item['expires']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if now > expires:
            return {
                'statusCode': 403,
                'body': 'Token expirado'
            }

        return {
            'statusCode': 200,
            'body': 'Token válido'
        }

    except Exception as e:
        print("Error en validate_token:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }