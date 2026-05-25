import pytest
from sqlalchemy.pool import NullPool
from app import create_app
from app.models import db as _db


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": NullPool}
    return application


@pytest.fixture(scope="session")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        print("\n[db teardown] starting")
        print("[db teardown] calling drop_all")
        _db.drop_all()
        print("[db teardown] drop_all done, calling dispose")
        _db.engine.dispose()
        print("[db teardown] dispose done")


@pytest.fixture(autouse=True)
def clean_tables(db):
    yield
    print("\n[clean_tables] starting teardown")
    print("[clean_tables] acquiring connection")
    with db.engine.connect() as conn:
        print("[clean_tables] got connection, deleting rows")
        for table in reversed(db.metadata.sorted_tables):
            print(f"[clean_tables] deleting from {table.name}")
            conn.execute(table.delete())
        print("[clean_tables] committing")
        conn.commit()
    print("[clean_tables] done")


@pytest.fixture()
def client(app):
    return app.test_client()
