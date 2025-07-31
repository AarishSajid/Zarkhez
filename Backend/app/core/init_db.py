from app.core.database import Base, engine

def init_db():
    print("[INIT] Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("[INIT] Done! Database is ready.")

if __name__ == "__main__":
    init_db()
