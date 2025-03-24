from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from datetime import timedelta

from src.models.models import User
from src.auth import services
from src.database import get_db

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 3600
templates = Jinja2Templates(directory='src/templates/')


@router.post("/register")
async def register(username: str, email: str, password: str,
                   db: AsyncSession = Depends(get_db)):
    """
        Регистрация нового пользователя.

        :param username: Имя пользователя
        :param email: Электронная почта
        :param password: Пароль
        :return: Токен доступа
    """
    result = await db.execute(
        select(User).filter((User.username == username) | (User.email == email))
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже существует"
        )

    await services.create_user(db, username, email, password)

    access_token = services.create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    content = {"message": "Welcome to the dark side, we have cookies"}

    response = JSONResponse(content=content)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return response


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    """
        Аутентификация пользователя.

        :param form_data: Данные формы авторизации
        :return: Токен доступа
    """
    user = await services.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )

    access_token = services.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    content = {"message": "Hi again in the dark side, we have cookies"}

    response = JSONResponse(content=content)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return response


@router.get("/info")
async def get_current_user_info(db: AsyncSession = Depends(get_db), request: Request = Request):
    """
        Получение информации о текущем пользователе.

        :return: Информация о пользователе
    """
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не авторизован",
            )

        current_user = await services.get_current_user(db, token)

        user_info = {
            "username": current_user.username,
            "email": current_user.email,
        }
        return user_info
    except Exception as ee:
        return {"error": "Пользователь не авторизован"}

