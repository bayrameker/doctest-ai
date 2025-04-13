from main import app
from app import db
from models import TestScenarioSet
from sqlalchemy import text

def run_migration():
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE test_scenario_sets ADD COLUMN IF NOT EXISTS parser_used VARCHAR(50)'))
            conn.commit()
            print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()