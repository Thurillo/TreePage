"""
Shared database connection helper.

Supports MySQL (via PyMySQL) and MS SQL Server (via pymssql).
Config files live in db_configs/<name>.yaml:

  type: mysql        # or mssql  (default: mysql)
  host: 192.168.1.10
  port: 3306         # optional (default: 3306 mysql / 1433 mssql)
  user: utente
  password: "secret"
  database: nome_db
"""

import pathlib

import yaml

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "db_configs"


def get_connection(config_name: str):
    """Open and return a DB connection configured by db_configs/<config_name>.yaml."""
    cfg_path = _CONFIG_DIR / f"{config_name}.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"DB config non trovato: {cfg_path}. "
            "Crea db_configs/{config_name}.yaml con host/user/password/database."
        )
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    db_type = cfg.get("type", "mysql").lower()

    if db_type == "mysql":
        import pymysql
        import pymysql.cursors
        return pymysql.connect(
            host=cfg["host"],
            port=int(cfg.get("port", 3306)),
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    elif db_type == "mssql":
        import pymssql  # noqa: F401
        return pymssql.connect(
            server=cfg["host"],
            port=str(cfg.get("port", 1433)),
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            as_dict=True,
        )
    else:
        raise ValueError(f"Tipo DB non supportato: '{db_type}'. Usa 'mysql' o 'mssql'.")


def test_connection(config_name: str) -> tuple[bool, str]:
    """Return (ok, error_message). Runs SELECT 1 to verify connectivity."""
    try:
        conn = get_connection(config_name)
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, ""
    except Exception as exc:
        return False, str(exc)
