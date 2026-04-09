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


def is_admin_user(event):
    """
    Check admin privileges from JWT claims injected by the API GW v2 JWT authorizer.
    Reads claims directly from the event — no additional Cognito API call needed.
    """
    try:
        claims = (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('jwt', {})
            .get('claims', {})
        )
        groups_str = claims.get('cognito:groups', '')
        if not groups_str or groups_str == '[]':
            return False
        groups = [g.strip() for g in groups_str.strip('[]').split(',') if g.strip()]
        return 'Administrators' in groups
    except Exception as exc:
        logger.error(f"Error checking admin privileges: {exc}")
        return False


def ok(body, status=200):
    """Build a successful HTTP response."""
    return {'statusCode': status, 'body': json.dumps(body, default=str)}


def err(message, status=500, **kwargs):
    """Build an error HTTP response."""
    body = {'message': message}
    body.update(kwargs)
    return {'statusCode': status, 'body': json.dumps(body, default=str)}
