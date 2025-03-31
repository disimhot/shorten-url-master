import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.models.models import Link, User

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/register", json={
        "username": "new_user",
        "email": "new_user@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert response.json()["message"] == "Welcome to the dark side, we have cookies"

    result = await db_session.execute(
        select(User).filter_by(username="new_user")
    )
    user = result.scalars().first()
    assert user is not None
    assert user.username == "new_user"
    assert user.email == "new_user@example.com"


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, db_session: AsyncSession):
    await client.post("/register", json={
        "username": "existing_user",
        "email": "existing_user@example.com",
        "password": "password123"
    })

    response = await client.post("/login", data={
        "username": "existing_user",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert response.json()["message"] == "Hi again in the dark side, we have cookies"


@pytest.mark.asyncio
async def test_get_current_user_info(client: AsyncClient, db_session: AsyncSession):
    await client.post("/register", json={
        "username": "current_user",
        "email": "current_user@example.com",
        "password": "password123"
    })
    login_response = await client.post("/login", data={
        "username": "current_user",
        "password": "password123"
    })
    access_token = login_response.cookies["access_token"]

    response = await client.get("/info", cookies={"access_token": access_token})
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["username"] == "current_user"
    assert user_info["email"] == "current_user@example.com"


@pytest.mark.asyncio
async def test_logout_user(client: AsyncClient):
    await client.post("/register", json={
        "username": "logout_user",
        "email": "logout_user@example.com",
        "password": "password123"
    })
    login_response = await client.post("/login", data={
        "username": "logout_user",
        "password": "password123"
    })
    access_token = login_response.cookies["access_token"]

    response = await client.post("/logout", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert response.json()["message"] == "Вы успешно вышли из системы"

    assert "access_token" not in response.cookies

@pytest.mark.asyncio
async def test_create_link(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/shorten", json={
        "original_url": "https://example.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "original_url" in data


@pytest.mark.asyncio
async def test_redirect_link(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/shorten", json={
        "original_url": "https://example.com"
    })
    data = response.json()
    short_code = data["short_code"]

    redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_delete_link(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/shorten", json={
        "original_url": "https://example.com"
    })
    data = response.json()
    short_code = data["short_code"]

    delete_response = await client.delete(f"/{short_code}")
    assert delete_response.status_code == 204

    check_response = await client.get(f"/{short_code}")
    assert check_response.status_code == 404


@pytest.mark.asyncio
async def test_update_link(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/shorten", json={
        "original_url": "https://example.com"
    })
    data = response.json()
    short_code = data["short_code"]
    new_code = "newalias"

    update_response = await client.put(f"/{short_code}", json={"new_code": new_code})
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Ссылка обновлена"

    redirect_response = await client.get(f"/{new_code}", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_get_link_stats(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/shorten", json={
        "original_url": "https://example.com"
    })
    data = response.json()
    short_code = data["short_code"]

    stats_response = await client.get(f"/stats/{short_code}")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats[0]["original_url"] == "https://example.com"
    assert stats[0]["clicks"] == 0
