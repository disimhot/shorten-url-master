from passlib.context import CryptContext

from jose import jwt, JWTError
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from datetime import timedelta, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.models.models import User
from src.config import SECRET_KEY


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY: str = SECRET_KEY
ALGORITHM: str = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_password_hash(password: str) -> str:
    """Хеширует пароль.

    Args:
        password (str): Пароль для хеширования.

    Returns:
        str: Хешированный пароль.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли пароль его хешу.
    Args:
        plain_password (str): Пароль для проверки.
        hashed_password (str): Хешированный пароль.

    Returns:
        bool: True, если пароль соответствует хешу, False в противном случае.
     """
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(session: AsyncSession, username: str, email: str, password: str) -> User:
    """Создает нового пользователя

    Args:
        db (Session): Сессия базы данных.
        username (str): Имя пользователя.
        email (str): Электронная почта пользователя.
        password (str): Пароль пользователя.

    Returns:
        User: Созданный пользователь.
    """
    hashed_password = get_password_hash(password)
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "role": "user"  # По умолчанию роль 'user'
    }

    # Выполняем INSERT-запрос
    statement = insert(User).values(**user_data)
    await session.execute(statement)
    await session.commit()


async def authenticate_user(session: AsyncSession,username: str, password: str) -> Union[User, None]:
    """
        Аутентифицирует пользователя

        Args:
            session (Session): Сессия базы данных.
            username (str): Имя пользователя.
            password (str): Пароль пользователя.

        Returns:
            User: Аутентифицированный пользователь.
    """
    result = await session.execute(select(User).filter_by(username=username))
    user = result.scalars().first()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
        Создает JWT-токен.

        Args:
            data (dict): Данные для токена.
            expires_delta (timedelta): Время истечения токена.

        Returns:
            str: JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Union[str, None]:
    """Декодирует JWT-токен."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(session: AsyncSession, token: str = Depends(oauth2_scheme)) -> User:
    """
    Получает текущего пользователя по токену

    Args:
        token (str, optional): JWT-токен
        session (Session): Сессия базы данных
    Returns:
        User: Текущий пользователь.
        """
    username = decode_access_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    query = select(User).where(User.username == username)
    result = await session.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
