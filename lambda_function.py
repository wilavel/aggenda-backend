import json
import boto3
import os
import uuid
from datetime import datetime
import logging

# Inicializar clientes de AWS
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event: {event}")
        print("Event received:", json.dumps(event))  # Log del evento recibido
        
        # Obtener el método HTTP y la ruta
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        # Remover el prefijo del entorno de la ruta si existe
        if path.startswith('/dev/'):
            path = path[5:]  # Remover '/dev/'
        elif path.startswith('/prod/'):
            path = path[6:]  # Remover '/prod/'
        
        # Asegurar que la ruta siempre comience con '/'
        if not path.startswith('/'):
            path = '/' + path
        
        print(f"Method: {http_method}, Path: {path}")  # Log del método y ruta
        
        # Manejar diferentes operaciones CRUD
        if http_method == 'POST' and path == '/users':
            return create_user(event)
        elif http_method == 'GET' and path == '/users':
            return get_users()
        elif http_method == 'GET' and path.startswith('/users/'):
            user_id = path.split('/')[-1]
            return get_user(user_id)
        elif http_method == 'PUT' and path.startswith('/users/'):
            user_id = path.split('/')[-1]
            return update_user(user_id, event)
        elif http_method == 'DELETE' and path.startswith('/users/'):
            user_id = path.split('/')[-1]
            return delete_user(user_id)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid request',
                    'details': f'Method {http_method} not allowed for path {path}'
                })
            }
    except Exception as e:
        print("Error:", str(e))  # Log del error
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }

def create_user(event):
    try:
        # Verificar variables de entorno requeridas
        required_env_vars = ['COGNITO_USER_POOL_ID', 'DYNAMODB_TABLE']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        
        if missing_vars:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Configuration error',
                    'error': f'Missing required environment variables: {", ".join(missing_vars)}'
                })
            }

        print("Creating user with event:", json.dumps(event))  # Log del evento de creación
        
        # Obtener el cuerpo de la solicitud
        body = json.loads(event.get('body', '{}'))
        print("Request body:", json.dumps(body))  # Log del cuerpo de la solicitud
        
        user_id = body.get('id', str(uuid.uuid4()))
        name = body.get('name')
        email = body.get('email')
        password = body.get('password')
        
        print(f"User data - ID: {user_id}, Name: {name}, Email: {email}")  # Log de los datos del usuario
        
        if not all([name, email, password]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing required fields',
                    'required_fields': ['name', 'email', 'password']
                })
            }
        
        try:
            # Crear usuario en Cognito
            print("Creating user in Cognito...")  # Log de inicio de creación en Cognito
            cognito_response = cognito.admin_create_user(
                UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': name},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                MessageAction='SUPPRESS'
            )
            print("Cognito user created:", json.dumps(cognito_response))  # Log de respuesta de Cognito

            # Establecer contraseña permanente
            print("Setting user password...")  # Log de inicio de establecimiento de contraseña
            cognito.admin_set_user_password(
                UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                Username=email,
                Password=password,
                Permanent=True
            )
            print("Password set successfully")  # Log de contraseña establecida

            # Crear usuario en DynamoDB
            print("Creating user in DynamoDB...")  # Log de inicio de creación en DynamoDB
            item = {
                'id': user_id,
                'name': name,
                'email': email,
                'cognito_username': email,
                'created_at': datetime.now().isoformat()
            }
            
            table.put_item(Item=item)
            print("DynamoDB user created:", json.dumps(item))  # Log de usuario creado en DynamoDB
            
            return {
                'statusCode': 201,
                'body': json.dumps({
                    'message': 'User created successfully',
                    'user': item
                })
            }
        except cognito.exceptions.UsernameExistsException:
            print("User already exists in Cognito")  # Log de usuario existente
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'User already exists',
                    'details': 'A user with this email already exists'
                })
            }
        except Exception as e:
            print("Error in user creation:", str(e))  # Log de error en la creación
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Error creating user',
                    'error': str(e)
                })
            }
    except Exception as e:
        print("Error in create_user function:", str(e))  # Log de error general
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }

def get_users():
    try:
        response = table.scan()
        return {
            'statusCode': 200,
            'body': json.dumps(response['Items'])
        }
    except Exception as e:
        print("Error getting users:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error getting users',
                'error': str(e)
            })
        }

def get_user(user_id):
    try:
        response = table.get_item(Key={'id': user_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'User not found',
                    'user_id': user_id
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response['Item'])
        }
    except Exception as e:
        print("Error getting user:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error getting user',
                'error': str(e)
            })
        }

def update_user(user_id, event):
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Verificar si el usuario existe
        response = table.get_item(Key={'id': user_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'User not found',
                    'user_id': user_id
                })
            }
        
        user = response['Item']
        
        # Actualizar en Cognito si se proporciona email o name
        if 'email' in body or 'name' in body:
            try:
                attributes = []
                if 'email' in body:
                    attributes.append({'Name': 'email', 'Value': body['email']})
                if 'name' in body:
                    attributes.append({'Name': 'name', 'Value': body['name']})
                
                cognito.admin_update_user_attributes(
                    UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                    Username=user['cognito_username'],
                    UserAttributes=attributes
                )
            except Exception as e:
                print("Error updating Cognito user:", str(e))
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Error updating Cognito user',
                        'error': str(e)
                    })
                }
        
        # Actualizar en DynamoDB
        update_expression = 'SET '
        expression_values = {}
        
        if 'name' in body:
            update_expression += 'name = :name, '
            expression_values[':name'] = body['name']
        
        if 'email' in body:
            update_expression += 'email = :email, '
            expression_values[':email'] = body['email']
        
        update_expression += 'updated_at = :updated_at'
        expression_values[':updated_at'] = datetime.now().isoformat()
        
        table.update_item(
            Key={'id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User updated successfully',
                'user_id': user_id
            })
        }
    except Exception as e:
        print("Error updating user:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error updating user',
                'error': str(e)
            })
        }

def delete_user(user_id):
    try:
        # Verificar si el usuario existe
        response = table.get_item(Key={'id': user_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'User not found',
                    'user_id': user_id
                })
            }
        
        user = response['Item']
        
        try:
            # Eliminar usuario de Cognito
            cognito.admin_delete_user(
                UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                Username=user['cognito_username']
            )
            
            # Eliminar usuario de DynamoDB
            table.delete_item(Key={'id': user_id})
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'User deleted successfully',
                    'user_id': user_id
                })
            }
        except Exception as e:
            print("Error deleting user:", str(e))
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Error deleting user',
                    'error': str(e)
                })
            }
    except Exception as e:
        print("Error in delete_user function:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        } 