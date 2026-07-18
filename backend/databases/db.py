from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
import sys
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass

print('db base', id(Base))

def init_db():  
    from . import models
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("pgvector extension ready.")
    except Exception as exc:
        print(f"pgvector extension unavailable, continuing without it: {exc}")

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_schema()"))
        print(result.fetchone())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()