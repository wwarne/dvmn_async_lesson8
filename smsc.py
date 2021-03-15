"""
Working with the API for https://smsc.ru/
"""
import functools
from typing import Dict
from unittest.mock import AsyncMock
from urllib.parse import urljoin

import asks
from asks.errors import AsksException
from asks.response_objects import Response

import settings


class SmscApiError(Exception):
    pass


SMSC_BASE_URL = 'https://smsc.ru/sys/'
SMSC_FORMAT_JSON = 3


def optional_mock(func):
    counter = 0

    @functools.wraps(func)
    def inner(*args, **kwargs):
        nonlocal counter
        counter += 1
        api_call_result = {'id': counter, 'cnt': 1, 'cost': '2.7', 'balance': '87.4'}
        return AsyncMock(return_value=api_call_result)()

    return inner if settings.SMSC_USE_MOCK else func


@optional_mock
async def request_smsc(method: str, login: str, password: str, payload: Dict[str, str]) -> Dict[str, str]:
    """
    Send request to SMSC.ru service.

    Args:
        method (str): API method. E.g. 'send' or 'status'.
        login (str): Login for account on SMSC.
        password (str): Password for account on SMSC.
        payload (dict): Additional request params, override default ones.
    Returns:
        dict: Response from SMSC API.
    Raises:
        SmscApiError: If SMSC API response status is not 200 or it has `"ERROR" in response.

    Examples:
        >>> request_smsc("send", "my_login", "my_password", {"phones": "+79123456789"})
        {"cnt": 1, "id": 24}
        >>> request_smsc("status", "my_login", "my_password", {"phone": "+79123456789", "id": "24"})
        {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
    """
    if method not in ['send', 'status']:
        raise SmscApiError('Selected API method yet not supported.')
    if 'phones' not in payload and 'phone' not in payload:
        raise SmscApiError('Payload must contain "phone" (for `status` call) or "phones" (for `send` call)')

    query_params = {
        'login': login,
        'psw': password,
        'fmt': SMSC_FORMAT_JSON,
        'charset': 'utf-8'
    }
    if method == 'send':
        query_params['cost'] = 3  # server will add sms price and new money balance in response
    query_params.update(payload)
    try:
        response: Response = await asks.post(
            url=urljoin(SMSC_BASE_URL, f'{method}.php'),
            params=query_params,
        )
        response.raise_for_status()
    except AsksException as e:
        raise SmscApiError('Request to smsc.ru has failed')
    response_body = response.json()
    if 'error' in response_body:
        raise SmscApiError(response_body)
    return response_body
