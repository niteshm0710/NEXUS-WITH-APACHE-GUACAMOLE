import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Configure test environment variables BEFORE importing app
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["VMWARE_ENABLED"] = "false"
os.environ["GUACD_HOST"] = "127.0.0.1"
os.environ["GUACD_PORT"] = "4822"

from app.db import Base, get_db
from app.main import app
from app import models as m, security as sec

TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)
    with TestingSessionLocal() as db:
        admin_role = m.Role(name="admin")
        user_role = m.Role(name="user")
        db.add_all([admin_role, user_role])
        db.commit()

        # Admin user
        admin = m.User(
            email="admin@nexus.test",
            full_name="Admin Test",
            password_hash=sec.hash_password("admin-secure-password-123"),
            role_id=admin_role.id,
            is_active=True
        )
        # Standard user 1
        user1 = m.User(
            email="user1@nexus.test",
            full_name="User One",
            password_hash=sec.hash_password("user-secure-password-123"),
            role_id=user_role.id,
            is_active=True
        )
        # Standard user 2
        user2 = m.User(
            email="user2@nexus.test",
            full_name="User Two",
            password_hash=sec.hash_password("user-secure-password-123"),
            role_id=user_role.id,
            is_active=True
        )
        db.add_all([admin, user1, user2])
        db.commit()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture
def db():
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_headers(db):
    admin = db.query(m.User).filter_by(email="admin@nexus.test").first()
    token = sec.make_access(admin.id, "admin")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user1_headers(db):
    user = db.query(m.User).filter_by(email="user1@nexus.test").first()
    token = sec.make_access(user.id, "user")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user2_headers(db):
    user = db.query(m.User).filter_by(email="user2@nexus.test").first()
    token = sec.make_access(user.id, "user")
    return {"Authorization": f"Bearer {token}"}
