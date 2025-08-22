#!/usr/bin/env python3
"""
Kleine FastAPI-server die:
- je Zermelo-token beheert via de koppelcode (authorization_code → access_token),
- het weekrooster ophaalt via /api/v3/appointments,
- een smalle frontend (index.html) serveert die het rooster visueel toont.

Starten:
    pip install fastapi uvicorn requests
    python zermelo_frontend.py
    # of: uvicorn zermelo_frontend:app --reload
Open:
    http://localhost:8000
"""

import os
import sys
import json
import time
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse
from zoneinfo import ZoneInfo

# ======= Config =======
SCHOOL = "hetrhedens"  # jouw schoolslug
BASE = f"https://{SCHOOL}.zportal.nl/api/v3"
TOKEN_FILE = Path("zermelo_token.json")
INDEX_FILE = Path(__file__).with_name("index.html")
TZ = ZoneInfo("Europe/Amsterdam")

# ======= Helpers =======
def now_tz() -> dt.datetime:
    return dt.datetime.now(TZ)

def monday_of_week(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())  # maandag

def sunday_of_week(d: dt.date) -> dt.date:
    return monday_of_week(d) + dt.timedelta(days=6)

def to_unix_seconds(dt_aware: dt.datetime) -> int:
    if dt_aware.tzinfo is None:
        raise ValueError("Datetime moet timezone-aware zijn")
    return int(dt_aware.timestamp())

def parse_epoch_any(x: Any) -> Optional[dt.datetime]:
    if x is None:
        return None
    try:
        val = int(x)
    except Exception:
        return None
    # Heuristiek: < 1e11 is seconden; anders milliseconden
    sec = val if abs(val) < 10**11 else int(round(val / 1000))
    try:
        return dt.datetime.fromtimestamp(sec, tz=TZ)
    except Exception:
        return None

def iso_week_str(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}{w:02d}"

def read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)

def http_json(method: str, url: str, *, headers=None, params=None, data=None, retries=2, timeout=20) -> tuple[int, dict]:
    headers = headers or {}
    params = params or {}
    data = data or {}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, headers=headers, params=params, data=data, timeout=timeout)
            try:
                payload = r.json()
            except Exception:
                payload = {"_raw": r.text}
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.2 * (attempt + 1))
                continue
            return r.status_code, payload
        except requests.RequestException as e:
            last_exc = e
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    raise last_exc or RuntimeError("Netwerkfout")

# ======= Token =======
def token_is_expired(tok: Optional[dict]) -> bool:
    if not tok:
        return True
    obtained = tok.get("obtained_at", 0)
    ttl = tok.get("expires_in") or 0
    # 5 min veiligheidsmarge
    return (time.time() - obtained) > max(0, ttl - 300)

def exchange_code_for_token(authorization_code: str) -> dict:
    status, payload = http_json(
        "POST",
        f"{BASE}/oauth/token",
        data={"grant_type": "authorization_code", "code": authorization_code.strip()},
    )
    if status != 200 or "access_token" not in payload:
        raise RuntimeError(f"Token ophalen mislukt ({status}): {payload}")
    tok = {
        "access_token": payload["access_token"],
        "expires_in": payload.get("expires_in", 0),
        "obtained_at": int(time.time()),
        "raw": payload,
    }
    write_json(TOKEN_FILE, tok)
    print("Nieuw access token opgeslagen in zermelo_token.json")
    return tok

def get_bearer_token_interactive() -> str:
    tok = read_json(TOKEN_FILE)
    if token_is_expired(tok):
        code = os.getenv("ZERM_CODE")
        if not code:
            print("Geen (geldige) token gevonden. Voer je Zermelo koppelcode in (Portaal → Koppel externe applicatie):")
            code = input("> ").strip()
        tok = exchange_code_for_token(code)
    return tok["access_token"]

# ======= Zermelo API =======
def get_me(token: str) -> dict:
    status, payload = http_json("GET", f"{BASE}/users/~me", headers={"Authorization": f"Bearer {token}"})
    if status != 200:
        raise RuntimeError(f"/users/~me {status}: {payload}")
    data = (payload.get("response") or {}).get("data") or []
    if not data:
        raise RuntimeError("Lege respons van /users/~me")
    return data[0]

def get_appointments_week(token: str, user_code: str, any_date_in_week: dt.date) -> List[dict]:
    start = dt.datetime.combine(monday_of_week(any_date_in_week), dt.time(0, 0, tzinfo=TZ))
    end = dt.datetime.combine(sunday_of_week(any_date_in_week), dt.time(23, 59, tzinfo=TZ))
    params = {
        "user": user_code,                 # expliciet op jezelf filteren
        "start": to_unix_seconds(start),   # epoch seconden
        "end": to_unix_seconds(end),       # epoch seconden
        "valid": "true",
    }
    status, payload = http_json("GET", f"{BASE}/appointments", headers={"Authorization": f"Bearer {token}"}, params=params)
    if status != 200:
        raise RuntimeError(f"appointments {status}: {payload}")
    return (payload.get("response") or {}).get("data") or []

# ======= FastAPI app =======
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if not INDEX_FILE.exists():
        return HTMLResponse("<h1>index.html ontbreekt naast zermelo_frontend.py</h1>", status_code=500)
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

@app.get("/api/user")
def api_user() -> JSONResponse:
    try:
        token = get_bearer_token_interactive()
        me = get_me(token)
        return JSONResponse({"ok": True, "user": me})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/week")
def api_week(date: Optional[str] = Query(None, description="YYYY-MM-DD binnen de gewenste week")) -> JSONResponse:
    """
    Retourneert het weekrooster gegroepeerd per dag voor de opgegeven datum (of vandaag).
    Structuur: { week: 'YYYYWW', days: [ {date, items:[...]}, ... ] }
    """
    try:
        token = get_bearer_token_interactive()
        me = get_me(token)
        me_code = me.get("code")

        if date:
            try:
                d = dt.date.fromisoformat(date)
            except Exception:
                return JSONResponse({"ok": False, "error": "Ongeldige datum; gebruik YYYY-MM-DD"}, status_code=400)
        else:
            d = now_tz().date()

        appts = get_appointments_week(token, me_code, d)

        # Normaliseren en groeperen per dag
        days_map: Dict[str, List[dict]] = {}
        for a in appts:
            start = parse_epoch_any(a.get("start"))
            end = parse_epoch_any(a.get("end"))
            if not start or not end:
                continue
            date_key = start.date().isoformat()
            subs = a.get("subjects") or a.get("subject") or []
            if isinstance(subs, list):
                subject = ", ".join(s.lower() for s in subs if s) or "-"
            else:
                subject = str(subs).lower()
            locs = a.get("locations") or a.get("location") or []
            location = ", ".join(locs) if isinstance(locs, list) else (locs or "-")
            teachers = a.get("teachers") or []
            if isinstance(teachers, list):
                teacher_str = ", ".join(teachers)
            else:
                teacher_str = str(teachers or "-")

            item = {
                "start": int(start.timestamp() * 1000),  # ms voor de frontend
                "end": int(end.timestamp() * 1000),
                "subject": subject,
                "location": location,
                "teachers": teacher_str,
                "type": a.get("type") or a.get("appointmentType") or "",
            }
            days_map.setdefault(date_key, []).append(item)

        # Zorg voor maandag t/m zondag keys (ook als er geen afspraken zijn)
        mon = monday_of_week(d)
        days = []
        for i in range(7):
            day = mon + dt.timedelta(days=i)
            key = day.isoformat()
            items = days_map.get(key, [])
            # sorteer per dag op starttijd
            items.sort(key=lambda x: x["start"])
            days.append({"date": key, "items": items})

        return JSONResponse({
            "ok": True,
            "week": iso_week_str(d),
            "range": {"monday": mon.isoformat(), "sunday": (mon + dt.timedelta(days=6)).isoformat()},
            "user": {"code": me_code, "name": f"{me.get('firstName','')} {me.get('lastName','')}".strip()},
            "days": days
        })

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

if __name__ == "__main__":
    # Interactieve start zodat je desnoods meteen een koppelcode kunt invoeren.
    import uvicorn
    print("Start de server op http://localhost:8000")
    uvicorn.run("zermelo_frontend:app", host="0.0.0.0", port=8000, reload=False)