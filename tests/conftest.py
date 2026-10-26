import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.llm import get_llm_client
from app.main import app
from app.models import UserDB
from app.schemas import UserRole
from app.security import create_access_token, hash_password
from tests.fakes import FakeBlock, FakeClient, FakeResponse


@pytest.fixture
def db_session():
    if "test" not in settings.database_url:
        pytest.exit("Database's URL does not connect to test DB.")

    engine = create_engine(
        settings.database_url,
    )

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def fake_llm():
    fake_block = FakeBlock(type="text", text="fake summary")
    fake_response = FakeResponse(content=[fake_block], stop_reason="end_turn")
    fake = FakeClient(fake_response)

    app.dependency_overrides[get_llm_client] = lambda: fake

    yield fake

    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture(scope="session")
def password_hash_value():
    return hash_password("123")


def _make_authenticated_client(
    db_session, role: UserRole, hashed_password: str
) -> TestClient:
    user = UserDB(
        username=f"test-{role.value}", hashed_password=hashed_password, role=role
    )
    db_session.add(user)
    db_session.flush()

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    authed = TestClient(app)
    authed.headers.update({"Authorization": f"Bearer {token}"})
    return authed


@pytest.fixture
def admin_client(client, db_session, password_hash_value):
    return _make_authenticated_client(db_session, UserRole.ADMIN, password_hash_value)


@pytest.fixture
def operator_client(client, db_session, password_hash_value):
    return _make_authenticated_client(
        db_session, UserRole.OPERATOR, password_hash_value
    )


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
