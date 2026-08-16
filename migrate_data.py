#!/usr/bin/env python3
"""
Atlas Copco Mechanical Calculator (MechCal) Data Migration Script
Migrates data from local SQLite database (instance/calculators.db) to Neon PostgreSQL
and uploads existing local images/files in static/uploads/ to Cloudinary.

Features:
- 100% Idempotent: Can be run multiple times safely without duplicate records.
- Preserves exact primary keys (id), foreign keys, and timestamps.
- Preserves local SQLite database and uploads untouched.
- Synchronizes PostgreSQL auto-increment sequences after migration.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Cloudinary Setup
import cloudinary
import cloudinary.uploader

CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

IS_CLOUDINARY_CONFIGURED = bool(
    CLOUDINARY_URL or
    (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
)

if IS_CLOUDINARY_CONFIGURED:
    if CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
    else:
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True
        )


def get_sqlite_conn(sqlite_path="instance/calculators.db"):
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database file not found at '{sqlite_path}'.")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def upload_local_file_to_cloudinary(filepath, folder="mechcal/migrated", resource_type="auto"):
    """Uploads a local file to Cloudinary without modifying or deleting the local file."""
    if not os.path.exists(filepath):
        return None
    try:
        res = cloudinary.uploader.upload(
            filepath,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True
        )
        return {
            'url': res.get('secure_url'),
            'public_id': res.get('public_id')
        }
    except Exception as e:
        print(f"    [!] Cloudinary upload error for {filepath}: {e}")
        return None


def run_migration(database_url=None, sqlite_path="instance/calculators.db", upload_images=True):
    target_db_url = database_url or os.environ.get('DATABASE_URL')
    if not target_db_url:
        print("\n[ERROR] DATABASE_URL is not set.")
        print("Please configure DATABASE_URL in your .env file or pass it as an argument.")
        print("Example: python migrate_data.py postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require\n")
        sys.exit(1)

    if target_db_url.startswith('postgres://'):
        target_db_url = target_db_url.replace('postgres://', 'postgresql://', 1)

    if 'sqlite' in target_db_url:
        print("\n[ERROR] Target database URL points to SQLite. Target must be Neon PostgreSQL.")
        sys.exit(1)

    print("=" * 70)
    print("  ATLAS COPCO MECHCAL: NEON POSTGRESQL & CLOUDINARY MIGRATION")
    print("=" * 70)
    print(f"Source SQLite DB : {sqlite_path}")
    masked_url = target_db_url.split('@')[-1] if '@' in target_db_url else target_db_url[:20] + '...'
    print(f"Target Neon DB   : ...@{masked_url}")
    print(f"Cloudinary Sync  : {'Enabled' if (IS_CLOUDINARY_CONFIGURED and upload_images) else 'Skipped/Not Configured'}")
    print("-" * 70)

    # 1. Connect to SQLite
    sqlite_conn = get_sqlite_conn(sqlite_path)
    sqlite_cur = sqlite_conn.cursor()

    # 2. Connect to PostgreSQL using SQLAlchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(target_db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 3. Ensure tables exist in PostgreSQL
    print("[1/4] Ensuring PostgreSQL schema exists...")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "user" (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE,
                password VARCHAR(200),
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                google_id VARCHAR(100) UNIQUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email VARCHAR(120);
            ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_id VARCHAR(100);
            ALTER TABLE "user" ALTER COLUMN password DROP NOT NULL;
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calculator (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calculation_result (
                id SERIAL PRIMARY KEY,
                calculator_id INTEGER NOT NULL REFERENCES calculator(id) ON DELETE CASCADE,
                inputs TEXT NOT NULL,
                outputs TEXT NOT NULL,
                calculated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
    print("      Schema verified.")

    # 4. Migrate Users
    print("\n[2/4] Migrating Users...")
    sqlite_cur.execute('PRAGMA table_info("user")')
    cols = [r['name'] for r in sqlite_cur.fetchall()]
    has_email = 'email' in cols
    has_google = 'google_id' in cols

    sqlite_cur.execute('SELECT * FROM "user"')
    users = sqlite_cur.fetchall()
    user_migrated_count = 0
    for u in users:
        u_email = u['email'] if has_email and 'email' in u.keys() else None
        u_google = u['google_id'] if has_google and 'google_id' in u.keys() else None
        
        # Check if user with same id or username exists
        existing = session.execute(
            text('SELECT id FROM "user" WHERE id = :id OR username = :username OR (email IS NOT NULL AND email = :email)'),
            {'id': u['id'], 'username': u['username'], 'email': u_email}
        ).first()

        created_at_val = u['created_at']
        if isinstance(created_at_val, str):
            try:
                created_at_val = datetime.fromisoformat(created_at_val)
            except Exception:
                created_at_val = datetime.utcnow()

        if not existing:
            session.execute(
                text('INSERT INTO "user" (id, username, email, password, role, google_id, created_at) VALUES (:id, :username, :email, :password, :role, :google_id, :created_at)'),
                {
                    'id': u['id'],
                    'username': u['username'],
                    'email': u_email,
                    'password': u['password'],
                    'role': u['role'],
                    'google_id': u_google,
                    'created_at': created_at_val
                }
            )
            user_migrated_count += 1
            print(f"      + User '{u['username']}' (ID: {u['id']}, Role: {u['role']}) migrated.")
        else:
            # Update email / google_id if missing in target
            session.execute(
                text('UPDATE "user" SET email = COALESCE("user".email, :email), google_id = COALESCE("user".google_id, :google_id) WHERE id = :id'),
                {'id': u['id'], 'email': u_email, 'google_id': u_google}
            )
            print(f"      = User '{u['username']}' (ID: {u['id']}) already exists in target DB; updated if needed.")
    session.commit()
    print(f"      Total Users processed: {len(users)} ({user_migrated_count} inserted)")

    # 5. Migrate Calculators and upload media
    print("\n[3/4] Migrating Calculators and Media...")
    sqlite_cur.execute('SELECT id, title, config, created_at FROM calculator')
    calcs = sqlite_cur.fetchall()
    calc_migrated_count = 0
    uploads_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')

    for c in calcs:
        calc_id = c['id']
        title = c['title']
        config_raw = c['config']
        created_at_val = c['created_at']
        if isinstance(created_at_val, str):
            try:
                created_at_val = datetime.fromisoformat(created_at_val)
            except Exception:
                created_at_val = datetime.utcnow()

        try:
            config_dict = json.loads(config_raw)
        except Exception:
            config_dict = {}

        # If Cloudinary is available, sync images and data tables
        if IS_CLOUDINARY_CONFIGURED and upload_images:
            images = config_dict.get('images', [])
            updated_images = []
            for img in images:
                if isinstance(img, dict):
                    fn = img.get('filename')
                    # If not already on Cloudinary (no http url)
                    if fn and not img.get('url', '').startswith('http'):
                        local_fpath = os.path.join(uploads_dir, fn)
                        if os.path.exists(local_fpath):
                            print(f"      -> Uploading image to Cloudinary: {fn}...")
                            cloud_res = upload_local_file_to_cloudinary(local_fpath, folder="mechcal/reference_images", resource_type="image")
                            if cloud_res:
                                img['url'] = cloud_res['url']
                                img['public_id'] = cloud_res['public_id']
                                print(f"         Uploaded: {cloud_res['url']}")
                    updated_images.append(img)
                elif isinstance(img, str):
                    local_fpath = os.path.join(uploads_dir, img)
                    img_dict = {'filename': img, 'caption': ''}
                    if os.path.exists(local_fpath):
                        print(f"      -> Uploading image to Cloudinary: {img}...")
                        cloud_res = upload_local_file_to_cloudinary(local_fpath, folder="mechcal/reference_images", resource_type="image")
                        if cloud_res:
                            img_dict['url'] = cloud_res['url']
                            img_dict['public_id'] = cloud_res['public_id']
                    updated_images.append(img_dict)
            if updated_images:
                config_dict['images'] = updated_images

            # Check analysis table file
            analysis_fn = config_dict.get('analysis_file_path')
            if analysis_fn and not config_dict.get('analysis_file_url'):
                local_tbl_path = os.path.join(uploads_dir, analysis_fn)
                if os.path.exists(local_tbl_path):
                    print(f"      -> Uploading analysis table file: {analysis_fn}...")
                    cloud_res = upload_local_file_to_cloudinary(local_tbl_path, folder="mechcal/data_tables", resource_type="auto")
                    if cloud_res:
                        config_dict['analysis_file_url'] = cloud_res['url']
                        config_dict['analysis_file_public_id'] = cloud_res['public_id']

        final_config_str = json.dumps(config_dict)

        existing_calc = session.execute(
            text('SELECT id FROM calculator WHERE id = :id'),
            {'id': calc_id}
        ).first()

        if not existing_calc:
            session.execute(
                text('INSERT INTO calculator (id, title, config, created_at) VALUES (:id, :title, :config, :created_at)'),
                {'id': calc_id, 'title': title, 'config': final_config_str, 'created_at': created_at_val}
            )
            calc_migrated_count += 1
            print(f"      + Calculator '{title}' (ID: {calc_id}) inserted.")
        else:
            # Update config to preserve any updated Cloudinary URLs
            session.execute(
                text('UPDATE calculator SET title = :title, config = :config WHERE id = :id'),
                {'id': calc_id, 'title': title, 'config': final_config_str}
            )
            print(f"      = Calculator '{title}' (ID: {calc_id}) exists; config synchronized.")

    session.commit()
    print(f"      Total Calculators migrated/synced: {len(calcs)}")

    # 6. Migrate Calculation Results
    print("\n[4/4] Migrating Calculation Results...")
    sqlite_cur.execute('SELECT id, calculator_id, inputs, outputs, calculated_at FROM calculation_result')
    results = sqlite_cur.fetchall()
    results_migrated_count = 0

    for r in results:
        res_id = r['id']
        calc_id = r['calculator_id']
        calc_at_val = r['calculated_at']
        if isinstance(calc_at_val, str):
            try:
                calc_at_val = datetime.fromisoformat(calc_at_val)
            except Exception:
                calc_at_val = datetime.utcnow()

        existing_res = session.execute(
            text('SELECT id FROM calculation_result WHERE id = :id'),
            {'id': res_id}
        ).first()

        if not existing_res:
            session.execute(
                text('INSERT INTO calculation_result (id, calculator_id, inputs, outputs, calculated_at) VALUES (:id, :calculator_id, :inputs, :outputs, :calculated_at)'),
                {'id': res_id, 'calculator_id': calc_id, 'inputs': r['inputs'], 'outputs': r['outputs'], 'calculated_at': calc_at_val}
            )
            results_migrated_count += 1

    session.commit()
    print(f"      Total Calculation Results inserted: {results_migrated_count}/{len(results)}")

    # 7. Synchronize PostgreSQL sequences
    print("\n[*] Synchronizing PostgreSQL primary key sequences...")
    with engine.begin() as conn:
        conn.execute(text("SELECT setval(pg_get_serial_sequence('\"user\"', 'id'), coalesce((SELECT max(id) FROM \"user\"), 1));"))
        conn.execute(text("SELECT setval(pg_get_serial_sequence('calculator', 'id'), coalesce((SELECT max(id) FROM calculator), 1));"))
        conn.execute(text("SELECT setval(pg_get_serial_sequence('calculation_result', 'id'), coalesce((SELECT max(id) FROM calculation_result), 1));"))
    print("      PostgreSQL sequences synchronized successfully.")

    sqlite_conn.close()
    session.close()

    print("\n" + "=" * 70)
    print("  MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_migration(database_url=db_arg)
