import json
import logging
import os

logger = logging.getLogger(__name__)

PAGE_SIZE = 50  # Default page size for paginated queries


def parse_event(event):
    """Parse HTTP method and path from API Gateway v2 payload format 2.0."""
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('requestContext', {}).get('http', {}).get('path', '')

    for prefix in ('/dev/', '/prod/'):
        if path.startswith(prefix):
            path = path[len(prefix) - 1:]
            break

    if not path.startswith('/'):
        path = '/' + path

    return http_method, path


def _get_claims(event):
    return (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('jwt', {})
        .get('claims', {})
    )


def get_user_groups(event):
    """Return the set of Cognito groups the caller belongs to."""
    try:
        groups_str = _get_claims(event).get('cognito:groups', '')
        if not groups_str or groups_str == '[]':
            return set()
        return {g.strip() for g in groups_str.strip('[]').split(',') if g.strip()}
    except Exception as exc:
        logger.error(f"Error reading user groups: {exc}")
        return set()


def get_caller_email(event):
    """Return the caller's email from JWT claims."""
    try:
        return _get_claims(event).get('email', '')
    except Exception:
        return ''


def is_admin_user(event):
    """True if the caller belongs to the Administrators group."""
    return 'Administrators' in get_user_groups(event)


def is_manager_or_admin(event):
    """True if the caller is a Manager or Administrator."""
    return bool(get_user_groups(event) & {'Managers', 'Administrators'})


def ok(body, status=200):
    """Build a successful HTTP response."""
    return {'statusCode': status, 'body': json.dumps(body, default=str)}


def err(message, status=500, **kwargs):
    """Build an error HTTP response."""
    body = {'message': message}
    body.update(kwargs)
    return {'statusCode': status, 'body': json.dumps(body, default=str)}
