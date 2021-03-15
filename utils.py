from collections import Counter


def redis2frontend(dict_from_redis):
    """
    Convert data from format we use in db to format needed by frontend.

    From this
    {
        'sms_id': '1',
        'text': 'Вечером будет шторм!',
        'created_at': 1615208863.206527,
        'phones_count': 3,
        'phones': {'+7 999 519 05 57': 'delivered', '911': 'pending', '112': 'failed'}
    }
    To this
    {
        "timestamp": 1123131392.734,
        "SMSText": "Сегодня гроза! Будьте осторожны!",
        "mailingId": "1",
        "totalSMSAmount": 200,
        "deliveredSMSAmount": 0,
        "failedSMSAmount": 0,
    }
    """
    delivery_stats = Counter(dict_from_redis['phones'].values())
    return {
        'timestamp': dict_from_redis['created_at'],
        'SMSText': dict_from_redis['text'],
        'mailingId': str(dict_from_redis['sms_id']),
        'totalSMSAmount': dict_from_redis['phones_count'],
        'deliveredSMSAmount': delivery_stats.get('delivered', 0),
        'failedSMSAmount': delivery_stats.get('failed', 0),
    }
