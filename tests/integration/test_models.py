from app.models import Item, db


def test_item_creation(app):
    with app.app_context():
        item = Item(name="test-item")
        db.session.add(item)
        db.session.commit()

        fetched = db.session.get(Item, item.id)
        assert fetched is not None
        assert fetched.name == "test-item"
        assert fetched.created_at is not None


def test_item_to_dict(app):
    with app.app_context():
        item = Item(name="dict-test")
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d["name"] == "dict-test"
        assert isinstance(d["id"], int)
        assert isinstance(d["created_at"], str)


def test_item_name_required(app):
    with app.app_context():
        import pytest
        from sqlalchemy.exc import IntegrityError
        db.session.add(Item())
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
