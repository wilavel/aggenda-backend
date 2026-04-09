import json
import os
import logging

import boto3

from shared.utils import parse_event, ok, err

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ses = boto3.client('ses')


def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event: {json.dumps(event)}")
        http_method, path = parse_event(event)

        if http_method == 'POST' and path == '/send-json-email':
            return send_contact_email(event)

        return err(f'Method {http_method} not allowed for path {path}', 400)

    except Exception as exc:
        logger.error(f"Unhandled error: {exc}")
        return err('Internal server error')


def send_contact_email(event):
    try:
        body = json.loads(event.get('body', '{}'))
    except Exception as exc:
        return err(f'Invalid JSON: {exc}', 400)

    name = body.get('name', '').strip()
    email = body.get('email', '').strip()
    phone = body.get('phone', '').strip()

    if not all([name, email, phone]):
        return err('Missing required fields: name, email, phone', 400)

    sender = os.environ.get('SES_FROM_EMAIL', '')
    recipient = os.environ.get('SES_TO_EMAIL', '')

    if not sender or not recipient:
        logger.error("SES_FROM_EMAIL or SES_TO_EMAIL environment variable not configured")
        return err('Email service not configured', 500)

    text = f"Nombre: {name}\nEmail: {email}\nTeléfono: {phone}"

    try:
        response = ses.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': 'Nuevo contacto recibido', 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': text, 'Charset': 'UTF-8'}},
            },
        )
        logger.info(f"Email sent successfully. MessageId: {response['MessageId']}")
        return ok({'message': 'Correo enviado'})
    except Exception as exc:
        logger.error(f"Error sending email via SES: {exc}")
        return err('Error enviando correo')
