from pathlib import Path
from tganalytics.infra.tele_client import get_client_for_session

GCONF_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_PATH = GCONF_ROOT / "data" / "sessions" / "gconf_support.session"

def get_gconf_client(session_path: str = None):
    """
    Возвращает клиент для профиля gconf. По умолчанию ищет локальный путь
    gconf/data/sessions/gconf_support.session.
    """
    target = Path(session_path) if session_path else DEFAULT_SESSION_PATH
    return get_client_for_session(str(target))





