"""
Shared MySQL connection helper.

Usage in any router:
    from lib.db import get_connection

    conn = get_connection("letture")   # loads db_configs/letture.yaml
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            rows = cur.fetchall()
"""

import pathlib

import pymysql
import pymysql.cursors
import yaml

_CONFIG_DIR = pathlib.Path(__file__).parent.parent / "db_configs"


def get_connection(config_name: str) -> pymysql.connections.Connection:
    """
    Open and return a MySQL connection configured by db_configs/<config_name>.yaml.

    The YAML file must contain: host, user, password, database.
    Optional: port (default 3306).
    """
    cfg_path = _CONFIG_DIR / f"{config_name}.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"DB config not found: {cfg_path}. "
            "Create db_configs/{config_name}.yaml with host/user/password/database."
        )
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    return pymysql.connect(
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
