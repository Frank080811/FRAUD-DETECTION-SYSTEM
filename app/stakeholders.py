from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text
from app.settings import settings

router = APIRouter(prefix="/demo/stakeholders", tags=["Demo Stakeholders"])

engine = create_engine(settings.db_url, future=True)


class StakeholderCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    is_active: bool = True


def init_stakeholders_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_stakeholders (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))


@router.on_event("startup")
def startup():
    init_stakeholders_table()


@router.get("")
def list_stakeholders():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, email, name, is_active, created_at
            FROM alert_stakeholders
            ORDER BY id DESC
        """)).mappings().all()

    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.post("")
def add_stakeholder(payload: StakeholderCreate):
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM alert_stakeholders WHERE email = :email"),
            {"email": payload.email}
        ).fetchone()

        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")

        conn.execute(text("""
            INSERT INTO alert_stakeholders (email, name, is_active)
            VALUES (:email, :name, :is_active)
        """), {
            "email": payload.email,
            "name": payload.name,
            "is_active": payload.is_active
        })

    return {"message": "Stakeholder added", "email": payload.email}


@router.delete("/{email}")
def delete_stakeholder(email: str):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM alert_stakeholders WHERE email = :email"),
            {"email": email}
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Email not found")

    return {"message": "Stakeholder removed", "email": email}


@router.patch("/{email}/activate")
def activate_stakeholder(email: str):
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE alert_stakeholders
            SET is_active = TRUE
            WHERE email = :email
        """), {"email": email})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Email not found")

    return {"message": "Stakeholder activated", "email": email}


@router.patch("/{email}/deactivate")
def deactivate_stakeholder(email: str):
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE alert_stakeholders
            SET is_active = FALSE
            WHERE email = :email
        """), {"email": email})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Email not found")

    return {"message": "Stakeholder deactivated", "email": email}