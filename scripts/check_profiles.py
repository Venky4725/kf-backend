#!/usr/bin/env python3
"""Check existing profiles in database."""

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text('SELECT id, name, email, role FROM profiles'))
    for row in result:
        print(f"ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Role: {row[3]}")