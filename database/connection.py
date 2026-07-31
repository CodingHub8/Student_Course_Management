import configparser
import os
import sys
import base64
import threading
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

_CONFIG = None
_POOL = None
_POOL_LOCK = threading.Lock()

def get_config_path():
    # 1. PyInstaller bundle temp directory
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_config = os.path.join(sys._MEIPASS, 'config.ini')
        if os.path.exists(bundle_config):
            return bundle_config
    
    # 2. Executable folder (if running as compiled exe)
    if getattr(sys, 'frozen', False):
        exe_dir_config = os.path.join(os.path.dirname(sys.executable), 'config.ini')
        if os.path.exists(exe_dir_config):
            return exe_dir_config

    # 3. Source directory
    source_dir_config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
    if os.path.exists(source_dir_config):
        return source_dir_config

    # 4. Current working directory
    cwd_config = os.path.join(os.getcwd(), 'config.ini')
    if os.path.exists(cwd_config):
        return cwd_config

    return None

def load_config():
    global _CONFIG
    if _CONFIG is None:
        cfg = {}
        config_path = get_config_path()
        if config_path and os.path.exists(config_path):
            try:
                config = configparser.ConfigParser()
                config.read(config_path)
                if config.has_section('DATABASE'):
                    cfg['host'] = config.get('DATABASE', 'host', fallback=None)
                    cfg['port'] = config.get('DATABASE', 'port', fallback=None)
                    cfg['database'] = config.get('DATABASE', 'database', fallback=None)
                    cfg['user'] = config.get('DATABASE', 'user', fallback=None)
                    cfg['password'] = config.get('DATABASE', 'password', fallback=None)
            except Exception:
                pass

        # Environment variable overrides
        cfg['host'] = os.environ.get('DB_HOST', cfg.get('host'))
        cfg['port'] = os.environ.get('DB_PORT', cfg.get('port'))
        cfg['database'] = os.environ.get('DB_NAME', cfg.get('database'))
        cfg['user'] = os.environ.get('DB_USER', cfg.get('user'))
        cfg['password'] = os.environ.get('DB_PASSWORD', cfg.get('password'))

        cfg['port'] = int(cfg['port']) if cfg.get('port') else 5432
        cfg['sslmode'] = os.environ.get('DB_SSLMODE', 'require')
        _CONFIG = cfg

    return _CONFIG

def _get_pool():
    global _POOL
    if _POOL is None or _POOL.closed:
        with _POOL_LOCK:
            if _POOL is None or _POOL.closed:
                cfg = load_config()
                _POOL = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=cfg['host'],
                    port=cfg['port'],
                    database=cfg['database'],
                    user=cfg['user'],
                    password=cfg['password'],
                    sslmode=cfg['sslmode'],
                    connect_timeout=10
                )
    return _POOL

@contextmanager
def get_connection():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        if conn.closed != 0:
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        yield conn
    except Exception:
        if conn and conn.closed == 0:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            if conn.closed != 0:
                pool.putconn(conn, close=True)
            else:
                pool.putconn(conn)

def close_pool():
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None and not _POOL.closed:
            _POOL.closeall()
            _POOL = None