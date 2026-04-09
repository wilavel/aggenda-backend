import json
import os
import uuid
from datetime import datetime
import logging

import boto3

from shared.utils import parse_event, is_admin_user, ok, err, PAGE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
clinics_table = dynamodb.Table(os.environ['CLINICS_TABLE'])


def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        http_method, path = parse_event(event)
        logger.info(f"Method: {http_method}, Path: {path}")

        if http_method in ('POST', 'PUT', 'DELETE') and not is_admin_user(event):
            return err('Access denied. Only Administrators can perform this operation.', 403)

        if http_method == 'POST' and path == '/clinics':
            return create_clinic(event)
        if http_method == 'GET' and path == '/clinics':
            return get_clinics(event)
        if http_method == 'GET' and path.startswith('/clinics/'):
            return get_clinic(path.split('/')[-1])
        if http_method == 'PUT' and path.startswith('/clinics/'):
            return update_clinic(event, path.split('/')[-1])
        if http_method == 'DELETE' and path.startswith('/clinics/'):
            return delete_clinic(path.split('/')[-1])

        return err(f'Method {http_method} not allowed for path {path}', 400)

    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        return err('Internal server error')


def get_clinics(event):
    try:
        params = event.get('queryStringParameters') or {}
        last_key = params.get('next_token')

        scan_kwargs = {'Limit': PAGE_SIZE}
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = json.loads(last_key)

        response = clinics_table.scan(**scan_kwargs)
        result = {'clinics': response.get('Items', [])}

        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(response['LastEvaluatedKey'])

        logger.info(f"Retrieved {len(result['clinics'])} clinics")
        return ok(result)
    except Exception as exc:
        logger.error(f"Error getting clinics: {exc}")
        return err('Error getting clinics')


def get_clinic(clinic_id):
    try:
        response = clinics_table.get_item(Key={'id': clinic_id})
        if 'Item' not in response:
            return err('Clinic not found', 404, clinic_id=clinic_id)
        return ok(response['Item'])
    except Exception as exc:
        logger.error(f"Error getting clinic {clinic_id}: {exc}")
        return err('Error getting clinic')


def create_clinic(event):
    try:
        body = json.loads(event.get('body', '{}'))
        required = ['name', 'address', 'phone', 'email']
        missing = [f for f in required if f not in body]
        if missing:
            return err('Missing required fields', 400, missing_fields=missing)

        now = datetime.now().isoformat()
        clinic = {
            'id': str(uuid.uuid4()),
            'name': body['name'],
            'address': body['address'],
            'phone': body['phone'],
            'email': body['email'],
            'offices': body.get('offices', []),
            'created_at': now,
            'updated_at': now,
        }
        clinics_table.put_item(Item=clinic)
        logger.info(f"Created clinic {clinic['id']}")
        return ok({'message': 'Clinic created successfully', 'clinic': clinic}, 201)
    except Exception as exc:
        logger.error(f"Error creating clinic: {exc}")
        return err('Error creating clinic')


def update_clinic(event, clinic_id):
    try:
        body = json.loads(event.get('body', '{}'))
        response = clinics_table.get_item(Key={'id': clinic_id})
        if 'Item' not in response:
            return err('Clinic not found', 404, clinic_id=clinic_id)

        update_fields = []
        expression_values = {}
        expression_names = {}

        for field in ('phone', 'email', 'address', 'offices'):
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
            'Key': {'id': clinic_id},
            'UpdateExpression': 'SET ' + ', '.join(update_fields),
            'ExpressionAttributeValues': expression_values,
        }
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names

        clinics_table.update_item(**update_params)
        updated = clinics_table.get_item(Key={'id': clinic_id})['Item']
        logger.info(f"Updated clinic {clinic_id}")
        return ok({'message': 'Clinic updated successfully', 'clinic': updated})
    except Exception as exc:
        logger.error(f"Error updating clinic {clinic_id}: {exc}")
        return err('Error updating clinic')


def delete_clinic(clinic_id):
    try:
        response = clinics_table.get_item(Key={'id': clinic_id})
        if 'Item' not in response:
            return err('Clinic not found', 404, clinic_id=clinic_id)
        clinics_table.delete_item(Key={'id': clinic_id})
        logger.info(f"Deleted clinic {clinic_id}")
        return ok({'message': 'Clinic deleted successfully', 'clinic_id': clinic_id})
    except Exception as exc:
        logger.error(f"Error deleting clinic {clinic_id}: {exc}")
        return err('Error deleting clinic')
