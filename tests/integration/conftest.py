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


@pytest.fixture(scope="session", autouse=True)
def create_tables(app):
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(app):
    yield
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        _db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()
