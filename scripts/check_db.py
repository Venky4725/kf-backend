#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app.core.config import settings
from sqlalchemy import create_engine, inspect

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
with engine.connect() as conn:
    inspector = inspect(conn)
    print('DATABASE_URL=', settings.DATABASE_URL)
    print('tables=', inspector.get_table_names())
    for table in ['batches', 'profiles', 'users']:
        if table in inspector.get_table_names():
            print(f'--- {table} ---')
            print('columns:', [c['name'] for c in inspector.get_columns(table)])
            print('foreign keys:', inspector.get_foreign_keys(table))
