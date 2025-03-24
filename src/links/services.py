from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update

from datetime import datetime

from fastapi import HTTPException, status

from src.models.models import Link


async def create_link_in_db(
        session: AsyncSession,
        original_url: str,
        short_code: str,
        custom_alias: str,
        created_at: datetime,
        expires_at: datetime,
        user_id: int = None
) -> Link:
    """
    Функция для создания ссылки в базе данных

    Arguments:
    - session: Сессия для работы с базой данных
    - username: Имя пользователя
    - original_url: Оригинальный URL
    - short_code: Короткий код
    - custom_alias: Кастомный alias
    - expires_at: Дата и время истечения срока действия ссылки
    """

    # Формируем данные для создания новой ссылки
    link_data = {
        "original_url": original_url,
        "short_code": short_code,
        "custom_alias": custom_alias,
        "created_at": created_at,
        "last_used_at": None,
        "clicks": 0,  # Начальное значение количества переходов
        "expires_at": expires_at,
        "user_id": user_id
    }
    statement = insert(Link).values(**link_data)

    await session.execute(statement)
    await session.commit()

    return Link(**link_data)


async def update_link_stat_in_db(
        session: AsyncSession,
        short_code: str,
        last_used_at: datetime,
        clicks: int):
    """
    Обновление записи с сокращенной ссылкой.
    :param session: сессия базы данных
    :param short_code: короткая ссылка для поиска
    :param last_used_at: новое время последнего использования
    :param clicks: новое количество кликов
    """
    new_link = update(Link).where(Link.short_code == short_code).values(
        clicks=clicks,
        last_used_at=last_used_at
    )

    await session.execute(new_link)
    await session.commit()


def add_half_year() -> datetime:
    """
    Функция для добавления полугода к дате

    Arguments:
    - date: Дата

    Returns:
    - Дата и время после добавления полугода
    """
    current_datetime = datetime.now()
    new_month = current_datetime.month + 6
    if new_month > 12:
        new_year = current_datetime.year + new_month // 12
        new_month = new_month % 12
    else:
        new_year = current_datetime.year
    return current_datetime.replace(year=new_year, month=new_month)


async def update_link_in_db(session: AsyncSession, current_link: Link, new_code: str):
    """
    Обновление short_code в базе данных.
    :param db: Сессия базы данных
    :param current_link: Существующая ссылка, которую нужно обновить
    :param new_code: Новый код
    """
    try:
        new_link = (
            update(Link)
            .where(Link.id == current_link.id)
            .values(short_code=new_code, custom_alias=new_code)
        )
        await session.execute(new_link)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))