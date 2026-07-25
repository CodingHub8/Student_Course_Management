import configparser
import os
import psycopg2
from psycopg2.extras import RealDictCursor

_CONFIG = None

def load_config():
    global _CONFIG
    if _CONFIG is None:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        config.read(config_path)
        _CONFIG = {
            'host': config.get('DATABASE', 'host'),
            'port': config.getint('DATABASE', 'port'),
            'database': config.get('DATABASE', 'database'),
            'user': config.get('DATABASE', 'user'),
            'password': config.get('DATABASE', 'password')
        }
    return _CONFIG

def get_connection():
    cfg = load_config()
    return psycopg2.connect(
        host=cfg['host'],
        port=cfg['port'],
        database=cfg['database'],
        user=cfg['user'],
        password=cfg['password']
    )

# TODO: add Supabase URI