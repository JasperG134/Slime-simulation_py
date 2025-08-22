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
from fastapi import FastAPI, Query, Response, Request, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from zoneinfo import ZoneInfo

# ======= Config =======
SCHOOL = "hetrhedens"  # jouw schoolslug
BASE = f"https://{SCHOOL}.zportal.nl/api/v3"
TOKEN_FILE = Path("zermelo_token.json")
INDEX_FILE = Path(__file__).with_name("index.html")
ACCOUNTS_FILE = Path(__file__).with_name("accounts.html")
TZ = ZoneInfo("Europe/Amsterdam")
CURRENT_USER_KEY = "current_user_id"

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
def load_accounts() -> dict:
    """Load all accounts from token file. Return dict with accounts and current_user."""
    accounts_data = read_json(TOKEN_FILE)
    if not accounts_data:
        return {"accounts": {}, "current_user": None}

    # Convert old single-account format to multi-account
    if "access_token" in accounts_data:
        # Old format detected, convert to new format
        user_id = "user_1"  # default ID for converted account
        new_format = {
            "accounts": {
                user_id: accounts_data
            },
            "current_user": user_id
        }
        write_json(TOKEN_FILE, new_format)
        return new_format

    return accounts_data

def save_accounts(accounts_data: dict) -> None:
    """Save accounts data to token file."""
    write_json(TOKEN_FILE, accounts_data)

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

    # Get user info to create a proper user ID
    token = payload["access_token"]
    try:
        me = get_me(token)
        user_id = me.get("code", f"user_{int(time.time())}")
        user_name = f"{me.get('firstName', '')} {me.get('lastName', '')}".strip() or user_id
    except:
        user_id = f"user_{int(time.time())}"
        user_name = user_id

    tok = {
        "access_token": payload["access_token"],
        "expires_in": payload.get("expires_in", 0),
        "obtained_at": int(time.time()),
        "raw": payload,
        "user_id": user_id,
        "user_name": user_name,
    }

    # Load current accounts and add this one
    accounts_data = load_accounts()
    accounts_data["accounts"][user_id] = tok
    accounts_data["current_user"] = user_id
    save_accounts(accounts_data)

    print(f"Nieuw access token opgeslagen voor gebruiker {user_name} ({user_id})")
    return tok

def get_current_user_token(user_id: Optional[str] = None) -> Optional[dict]:
    """Get token for current user or specified user_id."""
    accounts_data = load_accounts()

    if user_id:
        return accounts_data["accounts"].get(user_id)

    current_user = accounts_data.get("current_user")
    if not current_user:
        return None

    return accounts_data["accounts"].get(current_user)

def get_bearer_token_interactive(user_id: Optional[str] = None) -> str:
    tok = get_current_user_token(user_id)
    if token_is_expired(tok):
        code = os.getenv("ZERM_CODE")
        if not code:
            print("Geen (geldige) token gevonden. Voer je Zermelo koppelcode in (Portaal → Koppel externe applicatie):")
            code = input("> ").strip()
        tok = exchange_code_for_token(code)
    return tok["access_token"]

def switch_current_user(user_id: str) -> bool:
    """Switch to different user account."""
    accounts_data = load_accounts()
    if user_id not in accounts_data["accounts"]:
        return False

    accounts_data["current_user"] = user_id
    save_accounts(accounts_data)
    return True

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

def get_liveschedule_week(token: str, user_code: str, any_date_in_week: dt.date) -> List[dict]:
    """Get liveschedule for the week to find choice hours."""
    start = dt.datetime.combine(monday_of_week(any_date_in_week), dt.time(0, 0, tzinfo=TZ))
    end = dt.datetime.combine(sunday_of_week(any_date_in_week), dt.time(23, 59, tzinfo=TZ))
    params = {
        "user": user_code,
        "start": to_unix_seconds(start),
        "end": to_unix_seconds(end),
    }
    print(f"DEBUG: Requesting liveschedule with params: {params}")
    print(f"DEBUG: URL: {BASE}/liveschedule")

    status, payload = http_json("GET", f"{BASE}/liveschedule", headers={"Authorization": f"Bearer {token}"}, params=params)
    print(f"DEBUG: Liveschedule response status: {status}")
    print(f"DEBUG: Liveschedule payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'not dict'}")

    if status != 200:
        print(f"DEBUG: Liveschedule request failed with status {status}")
        return []

    data = (payload.get("response") or {}).get("data") or []
    print(f"DEBUG: Found {len(data)} liveschedule items")
    return data

def get_appointmentinstances_week(token: str, user_code: str, any_date_in_week: dt.date) -> List[dict]:
    """Get appointment instances which might contain choice hour info."""
    start = dt.datetime.combine(monday_of_week(any_date_in_week), dt.time(0, 0, tzinfo=TZ))
    end = dt.datetime.combine(sunday_of_week(any_date_in_week), dt.time(23, 59, tzinfo=TZ))
    params = {
        "user": user_code,
        "start": to_unix_seconds(start),
        "end": to_unix_seconds(end),
    }
    print(f"DEBUG: Requesting appointmentinstances with params: {params}")
    print(f"DEBUG: URL: {BASE}/appointmentinstances")

    status, payload = http_json("GET", f"{BASE}/appointmentinstances", headers={"Authorization": f"Bearer {token}"}, params=params)
    print(f"DEBUG: Appointmentinstances response status: {status}")

    if status != 200:
        print(f"DEBUG: Appointmentinstances request failed with status {status}")
        return []

    data = (payload.get("response") or {}).get("data") or []
    print(f"DEBUG: Found {len(data)} appointmentinstances")
    return data

def get_choice_options(token: str, appointment_id: int) -> List[dict]:
    """Try to get choice options from various possible endpoints."""
    print(f"DEBUG: Trying to get choice options for appointment {appointment_id}")

    # Try 1: Get more info about the specific appointment
    status, payload = http_json("GET", f"{BASE}/appointments/{appointment_id}", headers={"Authorization": f"Bearer {token}"})
    print(f"DEBUG: Single appointment {appointment_id} status: {status}")

    if status == 200:
        data = (payload.get("response") or {}).get("data") or []
        if data:
            appointment = data[0]
            print(f"DEBUG: Appointment {appointment_id} keys: {list(appointment.keys())}")

            # Look for choice-related fields
            if "choices" in appointment:
                return appointment["choices"]
            if "availableChoices" in appointment:
                return appointment["availableChoices"]
            if "choosableInDepartmentCodes" in appointment:
                choosable_codes = appointment["choosableInDepartmentCodes"]
                print(f"DEBUG: Appointment has choosableInDepartmentCodes: {choosable_codes}")
                # Create mock choices based on department codes for now
                return [{"id": i+1, "subject": code, "teacher": "TBD", "location": "TBD", "choosable": True, "full": False} 
                       for i, code in enumerate(choosable_codes)]

    # Try 2: Check if there's an appointment options endpoint
    status, payload = http_json("GET", f"{BASE}/appointments/{appointment_id}/options", headers={"Authorization": f"Bearer {token}"})
    print(f"DEBUG: Appointment options endpoint status: {status}")
    if status == 200:
        data = (payload.get("response") or {}).get("data") or []
        return data

    # Try 3: Check if there's a choices endpoint
    status, payload = http_json("GET", f"{BASE}/appointments/{appointment_id}/choices", headers={"Authorization": f"Bearer {token}"})
    print(f"DEBUG: Appointment choices endpoint status: {status}")
    if status == 200:
        data = (payload.get("response") or {}).get("data") or []
        return data

    # Try 4: Check for department choices
    status, payload = http_json("GET", f"{BASE}/departments/choices", 
                               params={"appointment": appointment_id},
                               headers={"Authorization": f"Bearer {token}"})
    print(f"DEBUG: Department choices endpoint status: {status}")
    if status == 200:
        data = (payload.get("response") or {}).get("data") or []
        return data

    print(f"DEBUG: No choice options found for appointment {appointment_id}")

    return []

def make_choice_selection(token: str, appointment_id: int, choice_id: int) -> bool:
    """Try to make a choice selection using various possible endpoints."""
    print(f"DEBUG: Trying to make choice selection for appointment {appointment_id}, choice {choice_id}")

    # Try 1: POST to appointment choice endpoint
    data = {"choice": choice_id}
    status, payload = http_json("POST", f"{BASE}/appointments/{appointment_id}/choice", 
                               headers={"Authorization": f"Bearer {token}"}, 
                               data=data)
    print(f"DEBUG: POST /appointments/{appointment_id}/choice response: {status} - {payload}")
    if status == 200:
        return True

    # Try 2: PUT to appointment endpoint
    data = {"choiceId": choice_id}
    status, payload = http_json("PUT", f"{BASE}/appointments/{appointment_id}", 
                               headers={"Authorization": f"Bearer {token}"}, 
                               data=data)
    print(f"DEBUG: PUT /appointments/{appointment_id} response: {status} - {payload}")
    if status == 200:
        return True

    # Try 3: POST to a general choices endpoint
    data = {"appointmentId": appointment_id, "choiceId": choice_id}
    status, payload = http_json("POST", f"{BASE}/choices", 
                               headers={"Authorization": f"Bearer {token}"}, 
                               data=data)
    print(f"DEBUG: POST /choices response: {status} - {payload}")
    if status == 200:
        return True

    # Try 4: POST to student choices
    data = {"appointment": appointment_id, "choice": choice_id}
    status, payload = http_json("POST", f"{BASE}/students/~me/choices", 
                               headers={"Authorization": f"Bearer {token}"}, 
                               data=data)
    print(f"DEBUG: POST /students/~me/choices response: {status} - {payload}")
    if status == 200:
        return True

    print(f"DEBUG: All choice selection attempts failed")
    return False

# ======= FastAPI app =======
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if not INDEX_FILE.exists():
        return HTMLResponse("<h1>index.html ontbreekt naast zermelo_frontend.py</h1>", status_code=500)
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

@app.get("/accounts", response_class=HTMLResponse)
def accounts_page() -> HTMLResponse:
    if not ACCOUNTS_FILE.exists():
        return HTMLResponse("<h1>accounts.html ontbreekt naast zermelo_frontend.py</h1>", status_code=500)
    return HTMLResponse(ACCOUNTS_FILE.read_text(encoding="utf-8"))

@app.get("/api/user")
def api_user() -> JSONResponse:
    try:
        token = get_bearer_token_interactive()
        me = get_me(token)
        return JSONResponse({"ok": True, "user": me})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/accounts")
def api_accounts() -> JSONResponse:
    """Get all available accounts."""
    try:
        accounts_data = load_accounts()
        accounts = {}

        for user_id, token_data in accounts_data["accounts"].items():
            try:
                # Try to get fresh user info if token is still valid
                if not token_is_expired(token_data):
                    me = get_me(token_data["access_token"])
                    user_name = f"{me.get('firstName', '')} {me.get('lastName', '')}".strip() or user_id
                else:
                    user_name = token_data.get("user_name", user_id)

                accounts[user_id] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "is_expired": token_is_expired(token_data),
                    "obtained_at": token_data.get("obtained_at", 0)
                }
            except:
                accounts[user_id] = {
                    "user_id": user_id,
                    "user_name": token_data.get("user_name", user_id),
                    "is_expired": True,
                    "obtained_at": token_data.get("obtained_at", 0)
                }

        return JSONResponse({
            "ok": True,
            "accounts": accounts,
            "current_user": accounts_data.get("current_user")
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/switch-account")
async def api_switch_account(request: Request) -> JSONResponse:
    """Switch to a different account."""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        if not user_id:
            return JSONResponse({"ok": False, "error": "user_id is required"}, status_code=400)

        if switch_current_user(user_id):
            return JSONResponse({"ok": True, "current_user": user_id})
        else:
            return JSONResponse({"ok": False, "error": "Account niet gevonden"}, status_code=404)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/add-account")
async def api_add_account(request: Request) -> JSONResponse:
    """Add a new account using authorization code."""
    try:
        data = await request.json()
        authorization_code = data.get("authorization_code")
        if not authorization_code:
            return JSONResponse({"ok": False, "error": "authorization_code is required"}, status_code=400)

        token_data = exchange_code_for_token(authorization_code.strip())
        return JSONResponse({
            "ok": True,
            "user_id": token_data["user_id"],
            "user_name": token_data["user_name"]
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/choice-options/{appointment_id}")
def api_choice_options(appointment_id: int) -> JSONResponse:
    """Get available choice options for an appointment."""
    try:
        token = get_bearer_token_interactive()
        options = get_choice_options(token, appointment_id)
        return JSONResponse({"ok": True, "options": options})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/make-choice")
async def api_make_choice(request: Request) -> JSONResponse:
    """Make a choice selection."""
    try:
        data = await request.json()
        appointment_id = data.get("appointment_id")
        choice_id = data.get("choice_id")

        if not appointment_id or not choice_id:
            return JSONResponse({"ok": False, "error": "appointment_id and choice_id are required"}, status_code=400)

        token = get_bearer_token_interactive()
        success = make_choice_selection(token, appointment_id, choice_id)

        if success:
            return JSONResponse({"ok": True})
        else:
            return JSONResponse({"ok": False, "error": "Keuze maken mislukt"}, status_code=500)
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
        liveschedule = get_liveschedule_week(token, me_code, d)
        appointmentinstances = get_appointmentinstances_week(token, me_code, d)

        # Normaliseren en groeperen per dag
        days_map: Dict[str, List[dict]] = {}

        # Process regular appointments and look for choice indicators
        print(f"DEBUG: Processing {len(appts)} appointments")
        for i, a in enumerate(appts):
            print(f"DEBUG: Appointment {i} keys: {list(a.keys())}")
            print(f"DEBUG: Appointment {i} full data: {a}")

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

            # Check if this is a choice hour based on the 'optional' field being True
            is_choice = False
            choice_status = None
            appointment_id = a.get("id")

            # Primary check: appointment must be marked as optional
            is_optional = a.get("optional", False)
            if is_optional:
                print(f"DEBUG: Found optional appointment {i}: {appointment_id}")
                is_choice = True

            # Secondary check: look for choosable department codes (indicates choice possibility)
            choosable_codes = a.get("choosableInDepartmentCodes", [])
            if choosable_codes:
                print(f"DEBUG: Found choosable department codes in appointment {i}: {choosable_codes}")
                # This might indicate it's related to choice hours even if not optional

            # Check appointment type for choice indicators
            appt_type = a.get("type") or a.get("appointmentType") or ""
            if any(word in appt_type.lower() for word in ["keuze", "choice"]):
                print(f"DEBUG: Choice detected in appointment type: {appt_type}")
                is_choice = True

            # Check subject for choice indicators
            if any(word in subject.lower() for word in ["keuze", "choice"]):
                print(f"DEBUG: Choice detected in subject: {subject}")
                is_choice = True

            item = {
                "start": int(start.timestamp() * 1000),  # ms voor de frontend
                "end": int(end.timestamp() * 1000),
                "subject": subject,
                "location": location,
                "teachers": teacher_str,
                "type": appt_type,
                "is_choice_hour": is_choice,
                "appointment_id": appointment_id,
            }

            if is_choice:
                item["choice_status"] = "available"  # Default to available
                item["available_choices"] = 1  # Placeholder
                print(f"DEBUG: Created choice hour from appointment: {item}")

            days_map.setdefault(date_key, []).append(item)

        # Process liveschedule data for additional choice hour info
        print(f"DEBUG: Processing {len(liveschedule)} liveschedule items")
        for i, ls in enumerate(liveschedule):
            print(f"DEBUG: Liveschedule {i} keys: {list(ls.keys())}")
            print(f"DEBUG: Liveschedule {i}: {ls}")

        # Process appointment instances
        print(f"DEBUG: Processing {len(appointmentinstances)} appointment instances")
        for i, ai in enumerate(appointmentinstances):
            print(f"DEBUG: AppointmentInstance {i} keys: {list(ai.keys())}")
            if i < 3:  # Only show first 3 to avoid spam
                print(f"DEBUG: AppointmentInstance {i}: {ai}")

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

        # Debug: Count choice hours in response
        choice_count = 0
        for day in days:
            for item in day["items"]:
                if item.get("is_choice_hour"):
                    choice_count += 1
        print(f"DEBUG: Returning {choice_count} choice hours in response")

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