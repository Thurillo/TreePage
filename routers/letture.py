"""
Letture — API endpoints per la pagina di ricerca letture RFID.

Endpoint:
  GET    /api/letture?varco=X   → ricerca righe per varco (r.id o reader_uuid)
  DELETE /api/letture/{row_id}  → cancella singola riga tag_log
  DELETE /api/letture?varco=X   → cancella tutte le righe per il varco

Credenziali DB: db_configs/letture.yaml
"""

import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from lib.db import get_connection

router = APIRouter(prefix="/api/letture", tags=["letture"])

_SELECT_SQL = """
SELECT
  CASE
    WHEN MID(a.epc,1,3) = 'IDN' THEN JSON_VALUE(a.json_parameters, '$.lancio')
    ELSE JSON_VALUE(a.json_parameters, '$.Lancio')
  END AS Lancio,
  JSON_VALUE(a.json_parameters, '$.Cart') AS Cart,
  CASE
    WHEN MID(a.epc,1,3) != 'IDN' THEN JSON_VALUE(a.json_parameters, '$.Cliente')
    ELSE JSON_VALUE(a.json_parameters, '$.cliente')
  END AS Cliente,
  CASE
    WHEN MID(a.epc,1,3) != 'IDN' THEN JSON_VALUE(a.json_parameters, '$.Articolo')
    ELSE JSON_VALUE(a.json_parameters, '$.art')
  END AS Articolo,
  CASE
    WHEN MID(a.epc,1,3) != 'IDN' THEN JSON_VALUE(a.json_parameters, '$.DexArticolo')
    ELSE JSON_VALUE(a.json_parameters, '$.desc')
  END AS DexArticolo,
  tl.processed,
  tl.cancel,
  tl.tag_scan_id,
  ts.created AS Orario_Lettura,
  IFNULL(r.id, ts.reader_uuid) AS Varco,
  CASE
    WHEN MID(a.epc,1,3) != 'IDN' THEN JSON_VALUE(a.json_parameters, '$.Taglia')
    ELSE JSON_VALUE(a.json_parameters, '$.taglia')
  END AS Taglia,
  JSON_VALUE(a.json_parameters, '$.ParteCapo') AS ParteCapo,
  JSON_VALUE(a.json_parameters, '$.DexParteCapo') AS DexParteCapo,
  JSON_VALUE(a.json_parameters, '$.Quantita') AS Quantita,
  JSON_VALUE(a.json_parameters, '$.Variante') AS Variante,
  JSON_VALUE(a.json_parameters, '$.DexVariante') AS DexVariante,
  CASE
    WHEN MID(a.epc,1,3) != 'IDN' THEN JSON_VALUE(a.json_parameters, '$.Bagno')
    ELSE JSON_VALUE(a.json_parameters, '$.bagno')
  END AS Bagno,
  JSON_VALUE(a.json_parameters, '$.Filato1') AS Filato1,
  JSON_VALUE(a.json_parameters, '$.CodiceColore1') AS CodiceColore1,
  JSON_VALUE(a.json_parameters, '$.Bagno1') AS Bagno1,
  JSON_VALUE(a.json_parameters, '$.Filato2') AS Filato2,
  JSON_VALUE(a.json_parameters, '$.CodiceColore2') AS CodiceColore2,
  JSON_VALUE(a.json_parameters, '$.Bagno2') AS Bagno2,
  tl.epc,
  tl.id
FROM tag_log tl
INNER JOIN asset a ON tl.asset_id = a.id
INNER JOIN tag_scan ts ON tl.tag_scan_id = ts.id
LEFT JOIN readers r ON ts.reader_uuid = r.reader_uuid
WHERE (r.id = %s OR ts.reader_uuid = %s)
ORDER BY tl.tag_scan_id DESC
"""

_DELETE_ONE_SQL = "DELETE FROM tag_log WHERE id = %s"

_DELETE_ALL_SQL = """
DELETE tl FROM tag_log tl
INNER JOIN tag_scan ts ON tl.tag_scan_id = ts.id
LEFT JOIN readers r ON ts.reader_uuid = r.reader_uuid
WHERE (r.id = %s OR ts.reader_uuid = %s)
"""


def _serialize(row: dict) -> dict:
    """Convert non-JSON-serializable types (datetime, Decimal) to strings."""
    result = {}
    for k, v in row.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


@router.get("")
def search(varco: str = Query(..., description="ID numerico o UUID del varco")):
    try:
        conn = get_connection("letture")
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Connessione DB fallita: {e}")

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_SELECT_SQL, (varco, varco))
                rows = [_serialize(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(500, f"Errore query: {e}")

    return JSONResponse({"rows": rows, "total": len(rows)})


@router.delete("/{row_id}")
def delete_row(row_id: int):
    try:
        conn = get_connection("letture")
    except Exception as e:
        raise HTTPException(500, f"Connessione DB fallita: {e}")

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_DELETE_ONE_SQL, (row_id,))
                if cur.rowcount == 0:
                    raise HTTPException(404, f"Riga {row_id} non trovata")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Errore cancellazione: {e}")

    return {"deleted": row_id}


@router.delete("")
def delete_all(varco: str = Query(..., description="ID numerico o UUID del varco")):
    try:
        conn = get_connection("letture")
    except Exception as e:
        raise HTTPException(500, f"Connessione DB fallita: {e}")

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_DELETE_ALL_SQL, (varco, varco))
                deleted = cur.rowcount
    except Exception as e:
        raise HTTPException(500, f"Errore cancellazione: {e}")

    return {"deleted": deleted}
