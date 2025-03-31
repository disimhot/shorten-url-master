import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.database import get_db
from src.models.models import Base
from main import app

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

async def override_get_db() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="function")
async def client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(app=app, base_url="http://localhost:9999") as ac:
        yield ac
