#!/usr/bin/env python3
"""Add TL and Intern profiles to database."""

from sqlalchemy import create_engine, text
from app.core.config import settings
import uuid

engine = create_engine(settings.DATABASE_URL)

# Check existing profiles
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, name, email, role FROM profiles'))
    existing = [(row[2], row[3]) for row in result]
    print("Existing profiles:")
    for email, role in existing:
        print(f"  {email} - {role}")
    
    # Add TL profile if not exists
    tl_email = "tl@knowledgefactory.com"
    if not any(email == tl_email for email, _ in existing):
        tl_id = uuid.uuid4()
        conn.execute(text(
            "INSERT INTO profiles (id, name, email, role, tech_stack, created_at, updated_at) VALUES (:id, :name, :email, :role, :tech_stack, NOW(), NOW())"
        ), {"id": str(tl_id), "name": "Technical Lead", "email": tl_email, "role": "TECHNICAL_LEAD", "tech_stack": "Full Stack"})
        print(f"✓ Added TL profile: {tl_email}")
    else:
        print(f"TL profile already exists: {tl_email}")
    
    # Add Intern profile if not exists
    intern_email = "intern@knowledgefactory.com"
    if not any(email == intern_email for email, _ in existing):
        intern_id = uuid.uuid4()
        conn.execute(text(
            "INSERT INTO profiles (id, name, email, role, tech_stack, created_at, updated_at) VALUES (:id, :name, :email, :role, :tech_stack, NOW(), NOW())"
        ), {"id": str(intern_id), "name": "Intern User", "email": intern_email, "role": "INTERN", "tech_stack": "Frontend"})
        print(f"✓ Added Intern profile: {intern_email}")
    else:
        print(f"Intern profile already exists: {intern_email}")
    
    conn.commit()

print("\n✅ Done! Test credentials:")
print("  Admin:  admin@knowledgefactory.com / Admin@12345")
print("  TL:     tl@knowledgefactory.com / Admin@12345")
print("  Intern: intern@knowledgefactory.com / Admin@12345")