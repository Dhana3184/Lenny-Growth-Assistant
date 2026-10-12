from backend.database import Base, engine, check_database_connection
from backend import models  # Register the database models


def initialize_database():
    check_database_connection()
    Base.metadata.create_all(bind=engine)

    print("PostgreSQL connection successful.")
    print("Database tables are ready:")

    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    initialize_database()