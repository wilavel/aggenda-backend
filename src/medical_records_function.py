import json
import os
import uuid
from datetime import datetime
import logging

import boto3
from boto3.dynamodb.conditions import Key

from shared.utils import parse_event, ok, err

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')

WRITE_GROUPS = {'Doctors', 'Administrators', 'Managers'}


def _records_table():
    return dynamodb.Table(os.environ['MEDICAL_RECORDS_TABLE'])


def _notes_table():
    return dynamodb.Table(os.environ['MEDICAL_RECORD_NOTES_TABLE'])


def _caller_groups(event):
    try:
        claims = (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('jwt', {})
            .get('claims', {})
        )
        groups_str = claims.get('cognito:groups', '')
        if not groups_str or groups_str == '[]':
            return set()
        return {g.strip() for g in groups_str.strip('[]').split(',') if g.strip()}
    except Exception:
        return set()


def _caller_sub(event):
    try:
        return (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('jwt', {})
            .get('claims', {})
            .get('sub', '')
        )
    except Exception:
        return ''


def _can_write(event):
    return bool(_caller_groups(event) & WRITE_GROUPS)


def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        http_method, path = parse_event(event)
        logger.info(f"Method: {http_method}, Path: {path}")

        # /patients/{patient_id}/medical-record
        if _match2(path, '/patients/', '/medical-record'):
            patient_id = _seg(path, 1)
            if http_method == 'GET':
                return get_record(patient_id)
            if http_method in ('POST', 'PUT'):
                if not _can_write(event):
                    return err('Access denied', 403)
                return upsert_record(patient_id, event)
            return err(f'Method {http_method} not allowed', 405)

        # /patients/{patient_id}/medical-record/notes
        if _match3(path, '/patients/', '/medical-record/notes'):
            patient_id = _seg(path, 1)
            if http_method == 'GET':
                return list_notes(patient_id, event)
            if http_method == 'POST':
                if not _can_write(event):
                    return err('Access denied', 403)
                return create_note(patient_id, event)
            return err(f'Method {http_method} not allowed', 405)

        # /patients/{patient_id}/medical-record/notes/{note_id}
        if _match4(path, '/patients/', '/medical-record/notes/'):
            patient_id = _seg(path, 1)
            note_id = _seg(path, 4)
            if http_method == 'GET':
                return get_note(patient_id, note_id)
            if http_method == 'PUT':
                if not _can_write(event):
                    return err('Access denied', 403)
                return update_note(patient_id, note_id, event)
            if http_method == 'DELETE':
                if not _can_write(event):
                    return err('Access denied', 403)
                return delete_note(patient_id, note_id)
            return err(f'Method {http_method} not allowed', 405)

        return err(f'Path not found: {path}', 404)

    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        return err('Internal server error')


# ── Medical Record Profile ────────────────────────────────────────────────────

def get_record(patient_id):
    try:
        response = _records_table().get_item(Key={'patient_id': patient_id})
        if 'Item' not in response:
            return err('Medical record not found', 404)
        return ok({'medical_record': response['Item']})
    except Exception as exc:
        logger.error(f"Error getting medical record for {patient_id}: {exc}")
        return err('Error getting medical record')


def upsert_record(patient_id, event):
    try:
        body = json.loads(event.get('body', '{}'))
        now = datetime.now().isoformat()

        existing = _records_table().get_item(Key={'patient_id': patient_id}).get('Item')

        if existing:
            update_fields = []
            values = {}
            names = {}

            updatable = ['blood_type', 'allergies', 'chronic_diseases', 'current_medications', 'notes']
            for field in updatable:
                if field in body:
                    update_fields.append(f'#{field} = :{field}')
                    values[f':{field}'] = body[field]
                    names[f'#{field}'] = field

            update_fields.append('#updated_at = :updated_at')
            values[':updated_at'] = now
            names['#updated_at'] = 'updated_at'

            _records_table().update_item(
                Key={'patient_id': patient_id},
                UpdateExpression='SET ' + ', '.join(update_fields),
                ExpressionAttributeValues=values,
                ExpressionAttributeNames=names,
            )
            updated = _records_table().get_item(Key={'patient_id': patient_id})['Item']
            logger.info(f"Updated medical record for patient {patient_id}")
            return ok({'message': 'Medical record updated', 'medical_record': updated})

        record = {
            'patient_id': patient_id,
            'blood_type': body.get('blood_type', ''),
            'allergies': body.get('allergies', []),
            'chronic_diseases': body.get('chronic_diseases', []),
            'current_medications': body.get('current_medications', []),
            'notes': body.get('notes', ''),
            'created_by': _caller_sub(event),
            'created_at': now,
            'updated_at': now,
        }
        _records_table().put_item(Item=record)
        logger.info(f"Created medical record for patient {patient_id}")
        return ok({'message': 'Medical record created', 'medical_record': record}, 201)

    except Exception as exc:
        logger.error(f"Error upserting medical record for {patient_id}: {exc}")
        return err('Error saving medical record')


# ── SOAP Notes ────────────────────────────────────────────────────────────────

def list_notes(patient_id, event):
    try:
        params = event.get('queryStringParameters') or {}
        query_kwargs = {
            'KeyConditionExpression': Key('patient_id').eq(patient_id),
        }
        if params.get('next_token'):
            query_kwargs['ExclusiveStartKey'] = json.loads(params['next_token'])

        response = _notes_table().query(**query_kwargs)
        notes = sorted(response.get('Items', []),
                       key=lambda n: n.get('date', ''), reverse=True)
        result = {'patient_id': patient_id, 'notes': notes}
        if 'LastEvaluatedKey' in response:
            result['next_token'] = json.dumps(response['LastEvaluatedKey'])
        return ok(result)
    except Exception as exc:
        logger.error(f"Error listing notes for patient {patient_id}: {exc}")
        return err('Error listing notes')


def get_note(patient_id, note_id):
    try:
        response = _notes_table().get_item(Key={'patient_id': patient_id, 'note_id': note_id})
        if 'Item' not in response:
            return err('Note not found', 404)
        return ok({'note': response['Item']})
    except Exception as exc:
        logger.error(f"Error getting note {note_id}: {exc}")
        return err('Error getting note')


def create_note(patient_id, event):
    try:
        body = json.loads(event.get('body', '{}'))
        now = datetime.now().isoformat()

        note = {
            'patient_id': patient_id,
            'note_id': str(uuid.uuid4()),
            'doctor_id': body.get('doctor_id', _caller_sub(event)),
            'appointment_id': body.get('appointment_id', ''),
            'clinic_id': body.get('clinic_id', ''),
            'date': body.get('date', now[:10]),
            'subjective': body.get('subjective', ''),
            'objective': body.get('objective', ''),
            'assessment': body.get('assessment', ''),
            'plan': body.get('plan', ''),
            'attachments': body.get('attachments', []),
            'created_by': _caller_sub(event),
            'created_at': now,
            'updated_at': now,
        }
        _notes_table().put_item(Item=note)
        logger.info(f"Created note {note['note_id']} for patient {patient_id}")
        return ok({'message': 'Note created', 'note': note}, 201)
    except Exception as exc:
        logger.error(f"Error creating note for patient {patient_id}: {exc}")
        return err('Error creating note')


def update_note(patient_id, note_id, event):
    try:
        body = json.loads(event.get('body', '{}'))
        response = _notes_table().get_item(Key={'patient_id': patient_id, 'note_id': note_id})
        if 'Item' not in response:
            return err('Note not found', 404)

        updatable = ['subjective', 'objective', 'assessment', 'plan', 'attachments', 'date']
        update_fields = []
        values = {}
        names = {}

        for field in updatable:
            if field in body:
                update_fields.append(f'#{field} = :{field}')
                values[f':{field}'] = body[field]
                names[f'#{field}'] = field

        if not update_fields:
            return err('No fields to update', 400)

        update_fields.append('#updated_at = :updated_at')
        values[':updated_at'] = datetime.now().isoformat()
        names['#updated_at'] = 'updated_at'

        _notes_table().update_item(
            Key={'patient_id': patient_id, 'note_id': note_id},
            UpdateExpression='SET ' + ', '.join(update_fields),
            ExpressionAttributeValues=values,
            ExpressionAttributeNames=names,
        )
        updated = _notes_table().get_item(Key={'patient_id': patient_id, 'note_id': note_id})['Item']
        logger.info(f"Updated note {note_id}")
        return ok({'message': 'Note updated', 'note': updated})
    except Exception as exc:
        logger.error(f"Error updating note {note_id}: {exc}")
        return err('Error updating note')


def delete_note(patient_id, note_id):
    try:
        response = _notes_table().get_item(Key={'patient_id': patient_id, 'note_id': note_id})
        if 'Item' not in response:
            return err('Note not found', 404)
        _notes_table().delete_item(Key={'patient_id': patient_id, 'note_id': note_id})
        logger.info(f"Deleted note {note_id} for patient {patient_id}")
        return ok({'message': 'Note deleted', 'note_id': note_id})
    except Exception as exc:
        logger.error(f"Error deleting note {note_id}: {exc}")
        return err('Error deleting note')


# ── helpers ───────────────────────────────────────────────────────────────────

def _seg(path, index):
    return path.strip('/').split('/')[index]


def _match2(path, prefix, suffix):
    """Match /patients/{id}/medical-record (3 segments)."""
    parts = path.strip('/').split('/')
    return (len(parts) == 3
            and parts[0] == prefix.strip('/')
            and parts[2] == suffix.strip('/'))


def _match3(path, prefix, middle):
    """Match /patients/{id}/medical-record/notes (4 segments)."""
    parts = path.strip('/').split('/')
    return (len(parts) == 4
            and parts[0] == prefix.strip('/')
            and '/'.join(parts[2:]) == middle.strip('/'))


def _match4(path, prefix, suffix_prefix):
    """Match /patients/{id}/medical-record/notes/{note_id} (5 segments)."""
    parts = path.strip('/').split('/')
    return (len(parts) == 5
            and parts[0] == prefix.strip('/')
            and parts[2] == 'medical-record'
            and parts[3] == 'notes')
