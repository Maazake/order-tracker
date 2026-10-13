import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import UserDB
from app.schemas import UserRole
from app.security import create_access_token, hash_password


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def _make_authenticated_client(db_session, role: UserRole) -> TestClient:
    user = UserDB(
        username=f"test-{role.value}", hashed_password=hash_password("123"), role=role
    )
    db_session.add(user)
    db_session.flush()

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    authed = TestClient(app)
    authed.headers.update({"Authorization": f"Bearer {token}"})
    return authed


@pytest.fixture
def admin_client(client, db_session):
    return _make_authenticated_client(db_session, UserRole.ADMIN)


@pytest.fixture
def operator_client(client, db_session):
    return _make_authenticated_client(db_session, UserRole.OPERATOR)


@pytest.fixture
def employee(admin_client):

    response = admin_client.post(
        "/employees", json={"name": "John Smith", "role": "Lathe Operator"}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def order(admin_client):

    response = admin_client.post("/orders", json={"element_name": "DRILL", "count": 15})
    assert response.status_code == 201
    return response.json()
