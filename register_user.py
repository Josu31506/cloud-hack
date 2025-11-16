import boto3
import hashlib
import uuid
import os
from datetime import datetime

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(event, context):
    print("Event recibido en register_user:", event)  # Log en CloudWatch

    try:
        body = event['body']
        tenant_id = body.get('tenant_id')  # Correo electrónico del usuario
        password = body.get('password')
        role = body.get('role')  # Estudiante, administrativo o autoridad
        nombre = body.get('nombre')
        apellido = body.get('apellido')

        if not tenant_id or not password or not role or not nombre or not apellido:
            return {
                'statusCode': 400,
                'body': {'error': 'Faltan datos en el cuerpo de la solicitud'}
            }

        # Hashear la contraseña
        hashed_password = hash_password(password)

        # Obtener el UUID del usuario
        user_id = str(uuid.uuid4())

        # Fecha de registro
        fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Conectar a DynamoDB
        dynamodb = boto3.resource('dynamodb')
        usuarios_table = dynamodb.Table(os.environ['DYNAMODB_TABLE_USUARIOS'])

        # Almacenar el usuario en DynamoDB
        usuario_data = {
            'tenant_id': tenant_id,  # Correo electrónico
            'user_id': user_id,  # UUID
            'password': hashed_password,
            'role': role,  # Guardamos el rol (estudiante, administrativo, autoridad)
            'nombre': nombre,
            'apellido': apellido,
            'fecha_registro': fecha_registro
        }

        usuarios_table.put_item(Item=usuario_data)

        return {
            'statusCode': 200,
            'body': {
                'message': 'Usuario registrado exitosamente',
                'user_id': user_id
            }
        }

    except Exception as e:
        print("Error en register_user:", str(e))  # Log en CloudWatch
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
