from pathlib import Path

from decouple import AutoConfig

BASE_DIR = Path(__file__).parent

config = AutoConfig(search_path=BASE_DIR.joinpath('config'))

SMSC_LOGIN = config('SMSC_LOGIN')
SMSC_PASSWORD = config('SMSC_PASSWORD')
SMSC_USE_MOCK = config('SMSC_USE_MOCK', cast=bool)
REDIS_URI = config('REDIS_URI')
REDIS_PASSWORD = config('REDIS_PASSWORD') or None
