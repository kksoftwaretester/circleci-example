import pytest
from app import create_app
from app.models import db as _db


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture(scope="session")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(db):
    yield
    with db.engine.connect() as conn:
        for table in reversed(db.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture()
def client(app):
    return app.test_client()
