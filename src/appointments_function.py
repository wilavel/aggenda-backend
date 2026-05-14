import json
import os
import uuid
from datetime import datetime, timedelta, date
import logging

import boto3
from boto3.dynamodb.conditions import Key

from shared.utils import parse_event, is_manager_or_admin, get_user_groups, ok, err

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table(os.environ['APPOINTMENTS_TABLE'])
availability_table = dynamodb.Table(os.environ['AVAILABILITY_TABLE'])

APPOINTMENT_DURATION_MINUTES = 40


def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        http_method, path = parse_event(event)
        logger.info(f"Method: {http_method}, Path: {path}")

        # POST /appointments — managers, admins and doctors
        if http_method == 'POST' and path == '/appointments':
            if not _can_manage_appointments(event):
                return err('Access denied. Only Managers, Administrators or Doctors can create appointments.', 403)
            return create_appointment(event)

        # GET /appointments/{id}
        if http_method == 'GET' and _match_id(path, '/appointments/'):
            appointment_id = _extract_segment(path, 1)
            return get_appointment(appointment_id)

        # GET /doctors/{doctor_id}/appointments
        if http_method == 'GET' and _match(path, '/doctors/', '/appointments'):
            doctor_id = _extract_segment(path, 1)
            params = event.get('queryStringParameters') or {}
            return get_appointments_by_doctor(doctor_id, params.get('date'))

        # GET /patients/{patient_id}/appointments
        if http_method == 'GET' and _match(path, '/patients/', '/appointments'):
            patient_id = _extract_segment(path, 1)
            params = event.get('queryStringParameters') or {}
            return get_appointments_by_patient(patient_id, params.get('date'))

        # DELETE /appointments/{id} — managers, admins and doctors
        if http_method == 'DELETE' and _match_id(path, '/appointments/'):
            if not _can_manage_appointments(event):
                return err('Access denied. Only Managers, Administrators or Doctors can cancel appointments.', 403)
            appointment_id = _extract_segment(path, 1)
            return cancel_appointment(appointment_id)

        return err(f'Method {http_method} not allowed for path {path}', 400)

    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        return err('Internal server error')


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_appointment(event):
    try:
        body = json.loads(event.get('body', '{}'))
        required = ['doctor_id', 'patient_id', 'appointment_date', 'start_time']
        missing = [f for f in required if f not in body]
        if missing:
            return err('Missing required fields', 400, missing_fields=missing)

        doctor_id = body['doctor_id']
        patient_id = body['patient_id']
        appointment_date = body['appointment_date']
        start_time = body['start_time']
        clinic_id = body.get('clinic_id')

        # Validate date format
        try:
            appt_date = date.fromisoformat(appointment_date)
        except ValueError:
            return err('appointment_date must be in YYYY-MM-DD format', 400)

        # Validate time format
        if not _valid_time(start_time):
            return err('start_time must be in HH:MM format (e.g. "09:00")', 400)

        # Prevent past dates
        if appt_date < date.today():
            return err('Cannot create appointments in the past', 400)

        # Calculate end_time (40-minute duration)
        end_time = _add_minutes(start_time, APPOINTMENT_DURATION_MINUTES)

        # Convert date to day_of_week using project convention (0=Sunday, 1=Monday, ..., 6=Saturday)
        # Python weekday(): 0=Monday, 6=Sunday → project: (weekday+1)%7
        day_of_week = (appt_date.weekday() + 1) % 7

        # Verify doctor has an active availability slot covering the requested time
        availability_ok, avail_error = _check_availability(doctor_id, day_of_week, start_time, end_time, clinic_id)
        if not availability_ok:
            return err(avail_error, 409)

        # Check for conflicting appointments with the same doctor on the same date
        conflict, conflict_error = _check_conflicts(doctor_id, appointment_date, start_time, end_time)
        if conflict:
            return err(conflict_error, 409)

        now = datetime.now().isoformat()
        appointment = {
            'id': str(uuid.uuid4()),
            'doctor_id': doctor_id,
            'patient_id': patient_id,
            'appointment_date': appointment_date,
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': APPOINTMENT_DURATION_MINUTES,
            'status': 'scheduled',
            'created_at': now,
            'updated_at': now,
        }
        if clinic_id:
            appointment['clinic_id'] = clinic_id

        appointments_table.put_item(Item=appointment)
        logger.info(f"Created appointment {appointment['id']} for patient {patient_id} with doctor {doctor_id}")
        return ok({'message': 'Appointment created', 'appointment': appointment}, 201)

    except Exception as exc:
        logger.error(f"Error creating appointment: {exc}")
        return err('Error creating appointment')


def get_appointment(appointment_id):
    try:
        response = appointments_table.get_item(Key={'id': appointment_id})
        if 'Item' not in response:
            return err('Appointment not found', 404)
        return ok({'appointment': response['Item']})
    except Exception as exc:
        logger.error(f"Error getting appointment {appointment_id}: {exc}")
        return err('Error getting appointment')


def get_appointments_by_doctor(doctor_id, appointment_date=None):
    try:
        if appointment_date:
            response = appointments_table.query(
                IndexName='DoctorAppointmentsIndex',
                KeyConditionExpression=(
                    Key('doctor_id').eq(doctor_id) & Key('appointment_date').eq(appointment_date)
                ),
            )
        else:
            response = appointments_table.query(
                IndexName='DoctorAppointmentsIndex',
                KeyConditionExpression=Key('doctor_id').eq(doctor_id),
            )
        appointments = sorted(response.get('Items', []),
                              key=lambda a: (a['appointment_date'], a['start_time']))
        return ok({'doctor_id': doctor_id, 'appointments': appointments})
    except Exception as exc:
        logger.error(f"Error getting appointments for doctor {doctor_id}: {exc}")
        return err('Error getting appointments')


def get_appointments_by_patient(patient_id, appointment_date=None):
    try:
        if appointment_date:
            response = appointments_table.query(
                IndexName='PatientAppointmentsIndex',
                KeyConditionExpression=(
                    Key('patient_id').eq(patient_id) & Key('appointment_date').eq(appointment_date)
                ),
            )
        else:
            response = appointments_table.query(
                IndexName='PatientAppointmentsIndex',
                KeyConditionExpression=Key('patient_id').eq(patient_id),
            )
        appointments = sorted(response.get('Items', []),
                              key=lambda a: (a['appointment_date'], a['start_time']))
        return ok({'patient_id': patient_id, 'appointments': appointments})
    except Exception as exc:
        logger.error(f"Error getting appointments for patient {patient_id}: {exc}")
        return err('Error getting appointments')


def cancel_appointment(appointment_id):
    try:
        response = appointments_table.get_item(Key={'id': appointment_id})
        if 'Item' not in response:
            return err('Appointment not found', 404)

        appointments_table.update_item(
            Key={'id': appointment_id},
            UpdateExpression='SET #s = :status, updated_at = :updated_at',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'cancelled',
                ':updated_at': datetime.now().isoformat(),
            },
        )
        logger.info(f"Cancelled appointment {appointment_id}")
        return ok({'message': 'Appointment cancelled', 'appointment_id': appointment_id})
    except Exception as exc:
        logger.error(f"Error cancelling appointment {appointment_id}: {exc}")
        return err('Error cancelling appointment')


# ── business logic ────────────────────────────────────────────────────────────

def _check_availability(doctor_id, day_of_week, start_time, end_time, clinic_id):
    """Return (True, None) if the doctor has an active slot covering [start_time, end_time]."""
    response = availability_table.query(
        KeyConditionExpression=Key('doctor_id').eq(doctor_id)
    )
    slots = response.get('Items', [])

    matching_slots = [
        s for s in slots
        if int(s['day_of_week']) == day_of_week
        and s.get('is_active', True)
        and s['start_time'] <= start_time
        and s['end_time'] >= end_time
        and (clinic_id is None or s.get('clinic_id') == clinic_id)
    ]

    if not matching_slots:
        return False, (
            f'The doctor has no availability on that day and time. '
            f'The appointment ({start_time}–{end_time}) must fall within an active availability slot.'
        )
    return True, None


def _check_conflicts(doctor_id, appointment_date, start_time, end_time):
    """Return (True, error_msg) if any existing scheduled appointment overlaps."""
    response = appointments_table.query(
        IndexName='DoctorAppointmentsIndex',
        KeyConditionExpression=(
            Key('doctor_id').eq(doctor_id) & Key('appointment_date').eq(appointment_date)
        ),
    )
    existing = [a for a in response.get('Items', []) if a.get('status') != 'cancelled']

    for appt in existing:
        existing_start = appt['start_time']
        existing_end = appt['end_time']
        # Overlap when: new_start < existing_end AND new_end > existing_start
        if start_time < existing_end and end_time > existing_start:
            return True, (
                f'Time conflict: the doctor already has an appointment from '
                f'{existing_start} to {existing_end} on {appointment_date}.'
            )
    return False, None


# ── helpers ───────────────────────────────────────────────────────────────────

def _add_minutes(time_str, minutes):
    """Add minutes to an HH:MM string, return HH:MM."""
    dt = datetime.strptime(time_str, '%H:%M') + timedelta(minutes=minutes)
    return dt.strftime('%H:%M')


def _valid_time(t):
    try:
        parts = t.split(':')
        return (len(parts) == 2
                and 0 <= int(parts[0]) <= 23
                and 0 <= int(parts[1]) <= 59)
    except Exception:
        return False


def _can_manage_appointments(event):
    """Managers, Administrators and Doctors can create/cancel appointments."""
    return bool(get_user_groups(event) & {'Managers', 'Administrators', 'Doctors'})


def _match(path, prefix, suffix):
    """True if path matches /prefix/{id}/suffix."""
    parts = path.strip('/').split('/')
    return (len(parts) == 3
            and path.startswith(prefix.rstrip('/'))
            and path.endswith(suffix.strip('/')))


def _match_id(path, prefix):
    """True if path matches /prefix/{id} (exactly 2 segments)."""
    parts = path.strip('/').split('/')
    return len(parts) == 2 and path.startswith(prefix.rstrip('/'))


def _extract_segment(path, index):
    return path.strip('/').split('/')[index]
