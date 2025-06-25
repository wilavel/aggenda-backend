import json
import os
import sys
from datetime import datetime

# Add lib directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')
clinics_table = dynamodb.Table(os.environ['CLINICS_TABLE'])
users_table = dynamodb.Table(os.environ['USERS_TABLE'])

# Get environment variables
USERS_TABLE = os.environ['USERS_TABLE']
CLINICS_TABLE = os.environ['CLINICS_TABLE']
USER_POOL_ID = os.environ['USER_POOL_ID']

def is_admin_user(event):
    """Check if the user has admin privileges"""
    try:
        # Get the claims from the authorizer
        claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
        print("User claims:", json.dumps(claims))
        
        # Get the groups from the claims
        groups_str = claims.get('cognito:groups', '[]')
        # Handle empty or invalid string
        if not groups_str or groups_str == '[]':
            groups = []
        else:
            # Remove the square brackets and split by comma
            groups_str = groups_str.strip('[]')
            groups = [group.strip() for group in groups_str.split(',') if group.strip()]
        
        print(f"User groups: {groups}")
        is_admin = 'Administrator' in groups
        print(f"Is admin: {is_admin}")
        
        return is_admin
    except Exception as e:
        print(f"Error checking admin privileges: {str(e)}")
        print("Event structure:", json.dumps(event))
        return False

def lambda_handler(event, context: LambdaContext):
    """Handle clinic operations based on HTTP method and path"""
    try:
        # Log the received event
        print("Received event:", json.dumps(event))
        
        # Get HTTP method and path from API Gateway v2 format
        http_method = event.get('requestContext', {}).get('http', {}).get('method', '')
        path = event.get('requestContext', {}).get('http', {}).get('path', '')
        
        # Remove environment prefix if exists
        if path.startswith('/dev/'):
            path = path[5:]
        elif path.startswith('/prod/'):
            path = path[6:]
        
        # Ensure path starts with '/'
        if not path.startswith('/'):
            path = '/' + path
        
        print(f"Processing request - Method: {http_method}, Path: {path}")
        
        # Check if user is admin for write operations
        if http_method in ['POST', 'PUT', 'DELETE'] and not is_admin_user(event):
            print(f"Access denied for non-admin user - Method: {http_method}, Path: {path}")
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'message': 'Access denied',
                    'details': 'Only administrators can perform this operation'
                })
            }

        # Handle different HTTP methods and paths
        if http_method == 'POST' and path == '/clinics':
            return create_clinic(event)
        elif http_method == 'GET' and path == '/clinics':
            return get_clinics()
        elif http_method == 'GET' and path.startswith('/clinics/'):
            clinic_id = path.split('/')[-1]
            return get_clinic(clinic_id)
        elif http_method == 'PUT' and path.startswith('/clinics/'):
            clinic_id = path.split('/')[-1]
            return update_clinic(event, clinic_id)
        elif http_method == 'DELETE' and path.startswith('/clinics/'):
            clinic_id = path.split('/')[-1]
            return delete_clinic(clinic_id)
        else:
            print(f"Invalid request - Method: {http_method}, Path: {path}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid request',
                    'details': f'Method {http_method} not allowed for path {path}'
                })
            }

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }

def get_clinics():
    """Get all clinics from DynamoDB"""
    try:
        print("Fetching all clinics")
        table = dynamodb.Table(CLINICS_TABLE)
        response = table.scan()
        
        print(f"Successfully retrieved {len(response.get('Items', []))} clinics")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'clinics': response.get('Items', [])
            })
        }
    except Exception as e:
        print(f"Error getting clinics: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error getting clinics',
                'error': str(e)
            })
        }

def get_clinic(clinic_id):
    """Get a specific clinic by ID"""
    try:
        print(f"Fetching clinic with ID: {clinic_id}")
        table = dynamodb.Table(CLINICS_TABLE)
        response = table.get_item(Key={'id': clinic_id})
        
        if 'Item' not in response:
            print(f"Clinic not found with ID: {clinic_id}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'Clinic not found',
                    'clinic_id': clinic_id
                })
            }
        
        print(f"Successfully retrieved clinic with ID: {clinic_id}")
        return {
            'statusCode': 200,
            'body': json.dumps(response['Item'])
        }
    except Exception as e:
        print(f"Error getting clinic {clinic_id}: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error getting clinic',
                'error': str(e)
            })
        }

def create_clinic(event):
    """Create a new clinic"""
    try:
        table = dynamodb.Table(CLINICS_TABLE)
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['name', 'address']
        missing_fields = [field for field in required_fields if field not in body]
        
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing required fields',
                    'required_fields': missing_fields
                })
            }
        
        # Create clinic with timestamp
        current_time = datetime.now().isoformat()
        clinic = {
            'id': str(datetime.now().timestamp()),
            'name': body['name'],
            'address': body['address'],
            'offices': body.get('offices', []),
            'created_at': current_time,
            'updated_at': current_time
        }
        
        print(f"Creating new clinic: {clinic['name']}")
        table.put_item(Item=clinic)
        
        print(f"Successfully created clinic with ID: {clinic['id']}")
        return {
            'statusCode': 201,
            'body': json.dumps({
                'message': 'Clinic created successfully',
                'clinic': clinic
            })
        }
    except Exception as e:
        print(f"Error creating clinic: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error creating clinic',
                'error': str(e)
            })
        }

def update_clinic(event, clinic_id):
    """Update an existing clinic"""
    try:
        table = dynamodb.Table(CLINICS_TABLE)
        body = json.loads(event.get('body', '{}'))
        
        # Check if clinic exists
        response = table.get_item(Key={'id': clinic_id})
        if 'Item' not in response:
            print(f"Clinic not found with ID: {clinic_id}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'Clinic not found',
                    'clinic_id': clinic_id
                })
            }
        
        # Update clinic
        update_expression = 'SET '
        expression_values = {}
        
        if 'name' in body:
            update_expression += 'name = :name, '
            expression_values[':name'] = body['name']
        
        if 'address' in body:
            update_expression += 'address = :address, '
            expression_values[':address'] = body['address']
            
        if 'offices' in body:
            update_expression += 'offices = :offices, '
            expression_values[':offices'] = body['offices']
        
        update_expression += 'updated_at = :updated_at'
        expression_values[':updated_at'] = datetime.now().isoformat()
        
        print(f"Updating clinic with ID: {clinic_id}")
        table.update_item(
            Key={'id': clinic_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        # Get updated clinic
        response = table.get_item(Key={'id': clinic_id})
        print(f"Successfully updated clinic with ID: {clinic_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Clinic updated successfully',
                'clinic': response['Item']
            })
        }
    except Exception as e:
        print(f"Error updating clinic: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error updating clinic',
                'error': str(e)
            })
        }

def delete_clinic(clinic_id):
    """Delete a clinic"""
    try:
        table = dynamodb.Table(CLINICS_TABLE)
        
        # Check if clinic exists
        response = table.get_item(Key={'id': clinic_id})
        if 'Item' not in response:
            print(f"Clinic not found with ID: {clinic_id}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'Clinic not found',
                    'clinic_id': clinic_id
                })
            }
        
        print(f"Deleting clinic with ID: {clinic_id}")
        table.delete_item(Key={'id': clinic_id})
        
        print(f"Successfully deleted clinic with ID: {clinic_id}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Clinic deleted successfully',
                'clinic_id': clinic_id
            })
        }
    except Exception as e:
        print(f"Error deleting clinic: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error deleting clinic',
                'error': str(e)
            })
        } 