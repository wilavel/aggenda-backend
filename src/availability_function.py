import json
import os
import uuid
from datetime import datetime
import logging

import boto3
from boto3.dynamodb.conditions import Key

from shared.utils import parse_event, is_manager_or_admin, get_user_groups, ok, err

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
availability_table = dynamodb.Table(os.environ['AVAILABILITY_TABLE'])

DAYS = {0: 'Domingo', 1: 'Lunes', 2: 'Martes', 3: 'Miércoles',
        4: 'Jueves', 5: 'Viernes', 6: 'Sábado'}


def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        http_method, path = parse_event(event)
        logger.info(f"Method: {http_method}, Path: {path}")

        # POST /doctors/{doctor_id}/availability
        if http_method == 'POST' and _match(path, '/doctors/', '/availability'):
            if not _can_write_availability(event):
                return err('Access denied. Only Managers, Administrators or Doctors can configure availability.', 403)
            doctor_id = _extract_segment(path, 1)
            return create_slot(event, doctor_id)

        # GET /doctors/{doctor_id}/availability
        if http_method == 'GET' and _match(path, '/doctors/', '/availability'):
            doctor_id = _extract_segment(path, 1)
            return get_slots_by_doctor(doctor_id)

        # PUT /doctors/{doctor_id}/availability/{slot_id}
        if http_method == 'PUT' and _match_deep(path, '/doctors/', '/availability/'):
            if not _can_write_availability(event):
                return err('Access denied. Only Managers, Administrators or Doctors can edit availability.', 403)
            doctor_id, slot_id = _extract_doctor_and_slot(path)
            return update_slot(event, doctor_id, slot_id)

        # DELETE /doctors/{doctor_id}/availability/{slot_id}
        if http_method == 'DELETE' and _match_deep(path, '/doctors/', '/availability/'):
            if not _can_write_availability(event):
                return err('Access denied. Only Managers, Administrators or Doctors can delete availability.', 403)
            doctor_id, slot_id = _extract_doctor_and_slot(path)
            return delete_slot(doctor_id, slot_id)

        # GET /clinics/{clinic_id}/availability?day=2
        if http_method == 'GET' and _match(path, '/clinics/', '/availability'):
            clinic_id = _extract_segment(path, 1)
            params = event.get('queryStringParameters') or {}
            day = params.get('day')
            return get_slots_by_clinic(clinic_id, day)

        return err(f'Method {http_method} not allowed for path {path}', 400)

    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        return err('Internal server error')


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_slot(event, doctor_id):
    try:
        body = json.loads(event.get('body', '{}'))
        required = ['day_of_week', 'start_time', 'end_time', 'clinic_id']
        missing = [f for f in required if f not in body]
        if missing:
            return err('Missing required fields', 400, missing_fields=missing)

        day = body['day_of_week']
        if not isinstance(day, int) or day < 0 or day > 6:
            return err('day_of_week must be an integer between 0 (Sunday) and 6 (Saturday)', 400)

        if not _valid_time(body['start_time']) or not _valid_time(body['end_time']):
            return err('start_time and end_time must be in HH:MM format (e.g. "09:00")', 400)

        if body['start_time'] >= body['end_time']:
            return err('start_time must be earlier than end_time', 400)

        now = datetime.now().isoformat()
        slot = {
            'doctor_id': doctor_id,
            'slot_id': str(uuid.uuid4()),
            'day_of_week': day,
            'day_name': DAYS[day],
            'start_time': body['start_time'],
            'end_time': body['end_time'],
            'clinic_id': body['clinic_id'],
            'is_active': body.get('is_active', True),
            'created_at': now,
            'updated_at': now,
        }
        availability_table.put_item(Item=slot)
        logger.info(f"Created slot {slot['slot_id']} for doctor {doctor_id}")
        return ok({'message': 'Availability slot created', 'slot': slot}, 201)
    except Exception as exc:
        logger.error(f"Error creating slot: {exc}")
        return err('Error creating availability slot')


def get_slots_by_doctor(doctor_id):
    try:
        response = availability_table.query(
            KeyConditionExpression=Key('doctor_id').eq(doctor_id)
        )
        slots = sorted(response.get('Items', []),
                       key=lambda s: (int(s['day_of_week']), s['start_time']))
        return ok({'doctor_id': doctor_id, 'slots': slots})
    except Exception as exc:
        logger.error(f"Error getting slots for doctor {doctor_id}: {exc}")
        return err('Error getting availability')


def get_slots_by_clinic(clinic_id, day):
    try:
        query_kwargs = {
            'IndexName': 'ClinicDayIndex',
            'KeyConditionExpression': Key('clinic_id').eq(clinic_id),
        }
        if day is not None:
            query_kwargs['KeyConditionExpression'] = (
                Key('clinic_id').eq(clinic_id) & Key('day_of_week').eq(int(day))
            )

        response = availability_table.query(**query_kwargs)
        slots = sorted(response.get('Items', []),
                       key=lambda s: (int(s['day_of_week']), s['start_time']))
        return ok({'clinic_id': clinic_id, 'slots': slots})
    except Exception as exc:
        logger.error(f"Error getting slots for clinic {clinic_id}: {exc}")
        return err('Error getting clinic availability')


def update_slot(event, doctor_id, slot_id):
    try:
        body = json.loads(event.get('body', '{}'))

        # Verify the slot exists
        response = availability_table.get_item(
            Key={'doctor_id': doctor_id, 'slot_id': slot_id}
        )
        if 'Item' not in response:
            return err('Availability slot not found', 404)

        update_fields = []
        expression_values = {}

        for field in ('start_time', 'end_time', 'clinic_id', 'is_active'):
            if field in body:
                update_fields.append(f'{field} = :{field}')
                expression_values[f':{field}'] = body[field]

        if 'day_of_week' in body:
            day = body['day_of_week']
            if not isinstance(day, int) or day < 0 or day > 6:
                return err('day_of_week must be between 0 and 6', 400)
            update_fields.append('day_of_week = :day_of_week')
            update_fields.append('day_name = :day_name')
            expression_values[':day_of_week'] = day
            expression_values[':day_name'] = DAYS[day]

        if not update_fields:
            return err('No fields to update', 400)

        update_fields.append('updated_at = :updated_at')
        expression_values[':updated_at'] = datetime.now().isoformat()

        availability_table.update_item(
            Key={'doctor_id': doctor_id, 'slot_id': slot_id},
            UpdateExpression='SET ' + ', '.join(update_fields),
            ExpressionAttributeValues=expression_values,
        )
        updated = availability_table.get_item(
            Key={'doctor_id': doctor_id, 'slot_id': slot_id}
        )['Item']
        logger.info(f"Updated slot {slot_id} for doctor {doctor_id}")
        return ok({'message': 'Slot updated', 'slot': updated})
    except Exception as exc:
        logger.error(f"Error updating slot {slot_id}: {exc}")
        return err('Error updating availability slot')


def delete_slot(doctor_id, slot_id):
    try:
        response = availability_table.get_item(
            Key={'doctor_id': doctor_id, 'slot_id': slot_id}
        )
        if 'Item' not in response:
            return err('Availability slot not found', 404)

        availability_table.delete_item(Key={'doctor_id': doctor_id, 'slot_id': slot_id})
        logger.info(f"Deleted slot {slot_id} for doctor {doctor_id}")
        return ok({'message': 'Slot deleted', 'slot_id': slot_id})
    except Exception as exc:
        logger.error(f"Error deleting slot {slot_id}: {exc}")
        return err('Error deleting availability slot')


# ── path helpers ──────────────────────────────────────────────────────────────

def _match(path, prefix, suffix):
    """True if path looks like /prefix/{id}/suffix  (no extra segment after suffix)."""
    parts = path.strip('/').split('/')
    # e.g. doctors / {id} / availability  → 3 parts
    return (len(parts) == 3
            and path.startswith(prefix.rstrip('/'))
            and path.endswith(suffix.strip('/')))


def _match_deep(path, prefix, mid):
    """True if path looks like /prefix/{id}/mid/{slot_id}."""
    parts = path.strip('/').split('/')
    return (len(parts) == 4
            and path.startswith(prefix.rstrip('/'))
            and f'/{mid.strip("/")}/' in path)


def _extract_segment(path, index):
    """Return the segment at position `index` (0-based) after splitting by '/'."""
    return path.strip('/').split('/')[index]


def _extract_doctor_and_slot(path):
    parts = path.strip('/').split('/')
    # doctors / {doctor_id} / availability / {slot_id}
    return parts[1], parts[3]


def _can_write_availability(event):
    """Managers, Administrators and Doctors can write availability slots."""
    groups = get_user_groups(event)
    return bool(groups & {'Managers', 'Administrators', 'Doctors'})


def _valid_time(t):
    try:
        parts = t.split(':')
        return (len(parts) == 2
                and 0 <= int(parts[0]) <= 23
                and 0 <= int(parts[1]) <= 59)
    except Exception:
        return False
