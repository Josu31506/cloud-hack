import boto3
import hashlib
import uuid
import os
from datetime import datetime, timedelta

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(event, context):
    print("Event recibido en login_user:", event)  # Log en CloudWatch

    try:
        body = event['body']
        tenant_id = body.get('tenant_id')  # Correo electrónico del usuario
        password = body.get('password')

        # Acceder a las variables de entorno para obtener los nombres de las tablas
        usuarios_table_name = os.environ['DYNAMODB_TABLE_USUARIOS']
        tokens_table_name = os.environ['DYNAMODB_TABLE_TOKENS']

        dynamodb = boto3.resource('dynamodb')
        usuarios_table = dynamodb.Table(usuarios_table_name)

        # Buscar el usuario usando solo tenant_id (correo electrónico)
        response = usuarios_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(tenant_id)
        )

        if 'Items' not in response or len(response['Items']) == 0:
            return {
                'statusCode': 403,
                'body': 'Usuario no existe'
            }

        # Supongamos que un usuario puede tener solo un item en la tabla con el mismo tenant_id
        user = response['Items'][0]
        hashed_password_bd = user['password']

        if hashed_password_bd == hash_password(password):
            # Generar token
            token = str(uuid.uuid4())  # UUID único para el token
            token_id = str(uuid.uuid4())  # UUID para el token_id (clave de ordenamiento)
            expiration_time = datetime.now() + timedelta(hours=1)
            token_data = {
                'tenant_id': token,  # El token será la clave de partición (tenant_id)
                'token_id': token_id,  # UUID para el token_id (clave de ordenamiento)
                'user_id': user['user_id'],
                'role': user['role'],  # Incluir el rol del usuario
                'token': token,
                'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'expires': expiration_time.strftime('%Y-%m-%d %H:%M:%S')
            }

            # Almacenar el token en DynamoDB
            tokens_table = dynamodb.Table(tokens_table_name)
            tokens_table.put_item(Item=token_data)

            return {
                'statusCode': 200,
                'body': {
                    'message': 'Login exitoso',
                    'token': token,
                    'role': user['role']  # Incluir el rol en la respuesta
                }
            }
        else:
            return {
                'statusCode': 403,
                'body': 'Password incorrecto'
            }

    except Exception as e:
        print("Error en login_user:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
