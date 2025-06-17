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

def is_admin_user(event):
    try:
        # Obtener el token de autorización del header
        auth_header = event.get('headers', {}).get('authorization', '')
        if not auth_header.startswith('Bearer '):
            print("No Bearer token found in authorization header")
            return False
        
        token = auth_header.split(' ')[1]
        print("Attempting to get user with token", token)
        
        try:
            # Verificar el token y obtener los atributos del usuario
            response = cognito.get_user(
                AccessToken=token
            )
            print(f"Successfully got user: {response}")
            
            # Obtener el username directamente de la respuesta
            username = response.get('Username')
            
            if not username:
                print("No username found in response")
                return False
                
            print(f"Found username: {username}")
                
            # Verificar si el usuario pertenece al grupo Administrator
            try:
                groups_response = cognito.admin_list_groups_for_user(
                    Username=username,
                    UserPoolId=os.environ['COGNITO_USER_POOL_ID']
                )
                print(f"User groups: {groups_response}")
                
                for group in groups_response['Groups']:
                    if group['GroupName'] == 'Administrator':
                        print("User is an administrator")
                        return True
                        
                print("User is not an administrator")
                return False
            except cognito.exceptions.UserNotFoundException as e:
                print(f"User not found in Cognito: {str(e)}")
                return False
            except Exception as e:
                print(f"Error checking user groups: {str(e)}")
                return False
                
        except cognito.exceptions.NotAuthorizedException as e:
            print(f"Not authorized: {str(e)}")
            return False
        except cognito.exceptions.UserNotFoundException as e:
            print(f"User not found: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error in get_user: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error in is_admin_user: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event: {event}")
        print("Event received:", json.dumps(event))
        
        # Obtener el método HTTP y la ruta
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        # Remover el prefijo del entorno de la ruta si existe
        if path.startswith('/dev/'):
            path = path[5:]
        elif path.startswith('/prod/'):
            path = path[6:]
        
        # Asegurar que la ruta siempre comience con '/'
        if not path.startswith('/'):
            path = '/' + path
        
        print(f"Method: {http_method}, Path: {path}")
        
        # Verificar permisos de administrador para operaciones sensibles
        if http_method in ['POST', 'PUT', 'DELETE']:
            if not is_admin_user(event):
                return {
                    'statusCode': 403,
                    'body': json.dumps({
                        'message': 'Access denied',
                        'details': 'Only administrators can perform this operation'
                    })
                }
        
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
        print("Error:", str(e))
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
                }, default=str)
            }

        print("Creating user with event:", json.dumps(event, default=str))
        
        # Obtener el cuerpo de la solicitud
        body = json.loads(event.get('body', '{}'))
        print("Request body:", json.dumps(body, default=str))
        
        user_id = body.get('id', str(uuid.uuid4()))
        name = body.get('name')
        email = body.get('email')
        password = body.get('password')
        is_admin = body.get('is_admin', False)
        user_group = body.get('group')  # Nuevo campo para el grupo del usuario
        
        print(f"User data - ID: {user_id}, Name: {name}, Email: {email}, Is Admin: {is_admin}, Group: {user_group}")
        
        if not all([name, email, password, user_group]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing required fields',
                    'required_fields': ['name', 'email', 'password', 'group']
                }, default=str)
            }
        
        # Validar que el grupo sea válido
        valid_groups = ['doctors', 'patients', 'managers']
        if user_group not in valid_groups:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid group',
                    'details': f'Group must be one of: {", ".join(valid_groups)}'
                }, default=str)
            }
        
        try:
            # Crear usuario en Cognito
            print("Creating user in Cognito...")
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
            print("Cognito user created:", json.dumps(cognito_response, default=str))

            # Establecer contraseña permanente
            print("Setting user password...")
            cognito.admin_set_user_password(
                UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                Username=email,
                Password=password,
                Permanent=True
            )
            print("Password set successfully")

            # Agregar usuario al grupo especificado
            print(f"Adding user to {user_group} group...")
            try:
                # Primero verificar que el grupo existe
                try:
                    group_info = cognito.get_group(
                        GroupName=user_group,
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID']
                    )
                    print(f"Group info: {json.dumps(group_info, default=str)}")
                except cognito.exceptions.ResourceNotFoundException:
                    print(f"Group {user_group} does not exist, creating it...")
                    cognito.create_group(
                        GroupName=user_group,
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Description=f"Group for {user_group}"
                    )
                    print(f"Group {user_group} created successfully")

                # Intentar agregar el usuario al grupo
                try:
                    group_response = cognito.admin_add_user_to_group(
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Username=email,
                        GroupName=user_group
                    )
                    print(f"Group assignment response: {json.dumps(group_response, default=str)}")
                except cognito.exceptions.UserNotFoundException:
                    print(f"User {email} not found in Cognito")
                    raise Exception(f"User {email} not found in Cognito")
                except cognito.exceptions.InvalidParameterException as e:
                    print(f"Invalid parameter when adding user to group: {str(e)}")
                    raise e
                except Exception as e:
                    print(f"Error adding user to group: {str(e)}")
                    raise e

                # Verificar que el usuario fue agregado al grupo
                try:
                    groups = cognito.admin_list_groups_for_user(
                        Username=email,
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID']
                    )
                    print(f"User groups after assignment: {json.dumps(groups, default=str)}")
                    
                    if not any(group['GroupName'] == user_group for group in groups['Groups']):
                        print(f"Warning: User was not successfully added to group {user_group}")
                        # Intentar agregar el usuario al grupo nuevamente
                        cognito.admin_add_user_to_group(
                            UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                            Username=email,
                            GroupName=user_group
                        )
                        # Verificar nuevamente
                        groups = cognito.admin_list_groups_for_user(
                            Username=email,
                            UserPoolId=os.environ['COGNITO_USER_POOL_ID']
                        )
                        if not any(group['GroupName'] == user_group for group in groups['Groups']):
                            raise Exception(f"Failed to add user to group {user_group} after retry")
                    
                    print(f"User successfully added to {user_group} group")
                except Exception as e:
                    print(f"Error verifying group assignment: {str(e)}")
                    raise e

            except Exception as e:
                print(f"Error in group assignment process: {str(e)}")
                # Si falla la asignación del grupo, eliminar el usuario de Cognito
                try:
                    cognito.admin_delete_user(
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Username=email
                    )
                    print(f"User {email} deleted from Cognito due to group assignment failure")
                except Exception as delete_error:
                    print(f"Error deleting user after group assignment failure: {str(delete_error)}")
                raise Exception(f"Failed to complete user creation: {str(e)}")

            # Si el usuario es administrador, agregarlo también al grupo Administrator
            if is_admin:
                print("Adding user to Administrator group...")
                cognito.admin_add_user_to_group(
                    UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                    Username=email,
                    GroupName='Administrator'
                )
                print("User added to Administrator group")

            # Crear usuario en DynamoDB
            print("Creating user in DynamoDB...")
            current_time = datetime.now().isoformat()
            item = {
                'id': user_id,
                'name': name,
                'email': email,
                'phone': body.get('phone', ''),  # Agregar el número de teléfono
                'cognito_username': email,
                'is_admin': is_admin,
                'group': user_group,
                'created_at': current_time,
                'updated_at': current_time
            }
            
            try:
                # Verificar si el usuario ya existe en DynamoDB
                existing_user = table.get_item(
                    Key={'id': user_id}
                )
                
                if 'Item' in existing_user:
                    print(f"User {user_id} already exists in DynamoDB")
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'message': 'User already exists',
                            'details': 'A user with this ID already exists in the database'
                        }, default=str)
                    }
                
                # Crear el usuario en DynamoDB
                table.put_item(
                    Item=item,
                    ConditionExpression='attribute_not_exists(id)'  # Asegurar que el ID no existe
                )
                print("DynamoDB user created successfully:", json.dumps(item, default=str))
                
                # Verificar que el usuario fue creado
                verification = table.get_item(
                    Key={'id': user_id}
                )
                if 'Item' not in verification:
                    raise Exception("Failed to verify user creation in DynamoDB")
                
                return {
                    'statusCode': 201,
                    'body': json.dumps({
                        'message': 'User created successfully',
                        'user': item
                    }, default=str)
                }
            except Exception as e:
                print(f"Error creating user in DynamoDB: {str(e)}")
                # Si falla la creación en DynamoDB, eliminar el usuario de Cognito
                try:
                    cognito.admin_delete_user(
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Username=email
                    )
                    print(f"User {email} deleted from Cognito due to DynamoDB creation failure")
                except Exception as delete_error:
                    print(f"Error deleting user from Cognito: {str(delete_error)}")
                raise Exception(f"Failed to create user in DynamoDB: {str(e)}")
        except cognito.exceptions.UsernameExistsException:
            print("User already exists in Cognito")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'User already exists',
                    'details': 'A user with this email already exists'
                }, default=str)
            }
        except Exception as e:
            print("Error in user creation:", str(e))
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Error creating user',
                    'error': str(e)
                }, default=str)
            }
    except Exception as e:
        print("Error in create_user function:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            }, default=str)
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
        
        # Manejar cambios en el estado de administrador
        if 'is_admin' in body:
            try:
                if body['is_admin']:
                    # Agregar al grupo Administrator
                    cognito.admin_add_user_to_group(
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Username=user['cognito_username'],
                        GroupName='Administrator'
                    )
                else:
                    # Remover del grupo Administrator
                    cognito.admin_remove_user_from_group(
                        UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                        Username=user['cognito_username'],
                        GroupName='Administrator'
                    )
            except Exception as e:
                print("Error updating user group:", str(e))
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'message': 'Error updating user group',
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
            
        if 'is_admin' in body:
            update_expression += 'is_admin = :is_admin, '
            expression_values[':is_admin'] = body['is_admin']
        
        update_expression += 'updated_at = :updated_at'
        expression_values[':updated_at'] = datetime.now().isoformat()
        
        table.update_item(
            Key={'id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        # Obtener el usuario actualizado
        updated_user = table.get_item(Key={'id': user_id})['Item']
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User updated successfully',
                'user': updated_user
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