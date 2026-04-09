import json
import os
import uuid
from datetime import datetime
import logging

import boto3
from boto3.dynamodb.conditions import Key

from shared.utils import parse_event, is_admin_user, ok, err, PAGE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')

VALID_GROUPS = ('Doctors', 'Patients', 'Managers')


def _table():
    return dynamodb.Table(os.environ['USERS_TABLE'])


def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event: {json.dumps(event, default=str)}")
        http_method, path = parse_event(event)
        logger.info(f"Method: {http_method}, Path: {path}")

        # Admin-only mutations
        if http_method in ('POST', 'PUT', 'DELETE') and not is_admin_user(event):
            return err('Access denied. Only Administrators can perform this operation.', 403)

        if http_method == 'POST' and path == '/users':
            return create_user(event)
        if http_method == 'GET' and path == '/users':
            return get_users(event)
        if http_method == 'GET' and path == '/users/patients':
            return get_patients(event)
        if http_method == 'GET' and path.startswith('/users/'):
            return get_user(path.split('/')[-1])
        if http_method == 'PUT' and path.startswith('/users/'):
            return update_user(path.split('/')[-1], event)
        if http_method == 'DELETE' and path.startswith('/users/'):
            return delete_user(path.split('/')[-1])

        return err(f'Method {http_method} not allowed for path {path}', 400)

    except Exception as exc:
        logger.error(f"Unhandled exception: {exc}")
        return err('Internal server error')


def get_users(event):
    try:
        params = event.get('queryStringParameters') or {}
        last_key = params.get('next_token')

        scan_kwargs = {'Limit': PAGE_SIZE}
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = json.loads(last_key)

        response = _table().scan(**scan_kwargs)
        result = {'users': response.get('Items', [])}
        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(response['LastEvaluatedKey'])

        return ok(result)
    except Exception as exc:
        logger.error(f"Error getting users: {exc}")
        return err('Error getting users')


def get_patients(event):
    """
    Uses the GroupIndex GSI to query patients efficiently without a full table scan.
    Requires the 'group' attribute to be projected in the GSI (see dynamodb/main.tf).
    """
    try:
        params = event.get('queryStringParameters') or {}
        last_key = params.get('next_token')

        query_kwargs = {
            'IndexName': 'GroupIndex',
            'KeyConditionExpression': Key('group').eq('Patients'),
            'Limit': PAGE_SIZE,
        }
        if last_key:
            query_kwargs['ExclusiveStartKey'] = json.loads(last_key)

        response = _table().query(**query_kwargs)
        result = {'users': response.get('Items', [])}
        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(response['LastEvaluatedKey'])

        return ok(result)
    except Exception as exc:
        logger.error(f"Error getting patients: {exc}")
        return err('Error getting patients')


def get_user(user_id):
    try:
        response = _table().get_item(Key={'id': user_id})
        if 'Item' not in response:
            return err('User not found', 404, user_id=user_id)
        return ok(response['Item'])
    except Exception as exc:
        logger.error(f"Error getting user {user_id}: {exc}")
        return err('Error getting user')


def create_user(event):
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('id', str(uuid.uuid4()))
        name = body.get('name')
        email = body.get('email')
        password = body.get('password')
        is_admin = body.get('is_admin', False)
        user_group = body.get('group')
        document_type = body.get('document_type')
        document_number = body.get('document_number')
        clinics = body.get('clinics')

        if not all([name, email, password, user_group, document_type, document_number]):
            return err('Missing required fields', 400,
                       required_fields=['name', 'email', 'password', 'group',
                                        'document_type', 'document_number'])

        if user_group not in VALID_GROUPS:
            return err(f'Invalid group. Must be one of: {", ".join(VALID_GROUPS)}', 400)

        pool_id = os.environ['USER_POOL_ID']

        # Create in Cognito
        try:
            cognito.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': name},
                    {'Name': 'email_verified', 'Value': 'true'},
                ],
                MessageAction='SUPPRESS',
            )
            cognito.admin_set_user_password(
                UserPoolId=pool_id, Username=email, Password=password, Permanent=True
            )
        except cognito.exceptions.UsernameExistsException:
            return err('A user with this email already exists', 400)

        # Assign group — rollback Cognito on failure
        try:
            _ensure_group(pool_id, user_group)
            cognito.admin_add_user_to_group(
                UserPoolId=pool_id, Username=email, GroupName=user_group
            )
            if is_admin:
                cognito.admin_add_user_to_group(
                    UserPoolId=pool_id, Username=email, GroupName='Administrators'
                )
        except Exception as exc:
            logger.error(f"Group assignment failed, rolling back Cognito user: {exc}")
            _delete_cognito_user(pool_id, email)
            return err('Error assigning user group')

        # Create in DynamoDB — rollback Cognito on failure
        now = datetime.now().isoformat()
        item = {
            'id': user_id,
            'name': name,
            'email': email,
            'phone': body.get('phone', ''),
            'cognito_username': email,
            'is_admin': is_admin,
            'group': user_group,
            'document_type': document_type,
            'document_number': document_number,
            'clinics': clinics,
            'created_at': now,
            'updated_at': now,
        }
        try:
            _table().put_item(Item=item, ConditionExpression='attribute_not_exists(id)')
        except Exception as exc:
            logger.error(f"DynamoDB creation failed, rolling back Cognito user: {exc}")
            _delete_cognito_user(pool_id, email)
            return err('Error saving user to database')

        logger.info(f"Created user {user_id}")
        return ok({'message': 'User created successfully', 'user': item}, 201)

    except Exception as exc:
        logger.error(f"Error creating user: {exc}")
        return err('Error creating user', error=str(exc))


def update_user(user_id, event):
    try:
        body = json.loads(event.get('body', '{}'))
        response = _table().get_item(Key={'id': user_id})
        if 'Item' not in response:
            return err('User not found', 404, user_id=user_id)

        user = response['Item']
        pool_id = os.environ['USER_POOL_ID']

        # Update Cognito attributes if needed
        cognito_attrs = []
        if 'email' in body:
            cognito_attrs.append({'Name': 'email', 'Value': body['email']})
        if 'name' in body:
            cognito_attrs.append({'Name': 'name', 'Value': body['name']})
        if cognito_attrs:
            cognito.admin_update_user_attributes(
                UserPoolId=pool_id,
                Username=user['cognito_username'],
                UserAttributes=cognito_attrs,
            )

        # Update Administrators group membership
        if 'is_admin' in body:
            fn = (cognito.admin_add_user_to_group
                  if body['is_admin'] else cognito.admin_remove_user_from_group)
            fn(UserPoolId=pool_id, Username=user['cognito_username'],
               GroupName='Administrators')

        # Build DynamoDB update expression
        update_fields = []
        expression_values = {}
        expression_names = {}

        for field in ('email', 'is_admin', 'document_type', 'document_number'):
            if field in body:
                update_fields.append(f'{field} = :{field}')
                expression_values[f':{field}'] = body[field]

        if 'name' in body:
            update_fields.append('#n = :name')
            expression_values[':name'] = body['name']
            expression_names['#n'] = 'name'

        update_fields.append('updated_at = :updated_at')
        expression_values[':updated_at'] = datetime.now().isoformat()

        update_params = {
            'Key': {'id': user_id},
            'UpdateExpression': 'SET ' + ', '.join(update_fields),
            'ExpressionAttributeValues': expression_values,
        }
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names

        _table().update_item(**update_params)
        updated = _table().get_item(Key={'id': user_id})['Item']
        logger.info(f"Updated user {user_id}")
        return ok({'message': 'User updated successfully', 'user': updated})

    except Exception as exc:
        logger.error(f"Error updating user {user_id}: {exc}")
        return err('Error updating user')


def delete_user(user_id):
    try:
        response = _table().get_item(Key={'id': user_id})
        if 'Item' not in response:
            return err('User not found', 404, user_id=user_id)

        user = response['Item']
        pool_id = os.environ['USER_POOL_ID']

        cognito.admin_delete_user(UserPoolId=pool_id, Username=user['cognito_username'])
        _table().delete_item(Key={'id': user_id})
        logger.info(f"Deleted user {user_id}")
        return ok({'message': 'User deleted successfully', 'user_id': user_id})

    except Exception as exc:
        logger.error(f"Error deleting user {user_id}: {exc}")
        return err('Error deleting user')


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_group(pool_id, group_name):
    try:
        cognito.get_group(GroupName=group_name, UserPoolId=pool_id)
    except cognito.exceptions.ResourceNotFoundException:
        cognito.create_group(
            GroupName=group_name,
            UserPoolId=pool_id,
            Description=f'Group for {group_name}',
        )


def _delete_cognito_user(pool_id, email):
    try:
        cognito.admin_delete_user(UserPoolId=pool_id, Username=email)
    except Exception as exc:
        logger.error(f"Failed to delete Cognito user {email} during rollback: {exc}")
