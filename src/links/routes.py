from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_cache.decorator import cache
from celery.result import AsyncResult

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

from datetime import datetime

from src.links.models import LinkCreate
from src.models.models import Link
from src.database import get_db
from src.utils import generate_short_code
from src.auth.services import get_current_user
from src.tasks.tasks import delete_unused_links
from src.links.services import create_link_in_db, add_half_year, update_link_stat_in_db, \
    update_link_in_db

router = APIRouter()


@router.post("/shorten")
async def create_link(
        link_data: LinkCreate,
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """
        Создание коротких ссылок.
        Принимает JSON с полями:
        :param original_url: URL для сокращения,
        :param custom_alias: Необязательное поле - для сокращения URL с указанием собственного
        алиаса,
        :param expires_at: Необязательное поле - для указания даты и времени истечения срока
        действия ссылки.

        Если custom_alias указан, то он проверяется на уникальность.
        Если custom_alias не указан, то генерируется случайный код.
        Если custom_alias уже занят, возвращается ошибка.

        :return: JSON с полями:
            :param short_code: Короткий код,
            :param original_url: Оригинальный URL
"""
    try:
        if link_data.custom_alias:
            result = await db.execute(select(Link).filter_by(custom_alias=link_data.custom_alias))
            existing_link = result.scalars().first()
            if existing_link:
                raise HTTPException(status_code=400, detail="Такой алиас уже занят")

        short_code = link_data.custom_alias or generate_short_code()
        token = request.cookies.get("access_token")
        current_user = await get_current_user(db, token)
        expires_at = link_data.expires_at or add_half_year()
        if current_user:
            user_id = current_user.id

        new_link = await create_link_in_db(
            session=db,
            original_url=link_data.original_url,
            short_code=short_code,
            custom_alias=short_code,
            created_at=datetime.now(),
            expires_at=expires_at,
            user_id=user_id
        )
        content = {
            "short_code": new_link.short_code,
            "original_url": link_data.original_url
        }
        return JSONResponse(content=content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{short_code}")
async def redirect_to_original_url(short_code: str, db: AsyncSession = Depends(get_db)):
    """
        Переход по сокращенной ссылке на оригинальный URL.
        :param short_code:
        :return: Редирект на оригинальный URL
    """
    try:
        result = await db.execute(select(Link).filter_by(short_code=short_code))
        current_link = result.scalars().first()

        if not current_link:
            raise HTTPException(status_code=404, detail="Ссылка не найдена")

        await update_link_stat_in_db(db, short_code, datetime.now(), current_link.clicks + 1)

        original_url = current_link.original_url
        if not original_url.startswith("http://") and not original_url.startswith("https://"):
            original_url = "https://" + original_url

        return RedirectResponse(url=original_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{short_code}")
async def delete_link(short_code: str, db: Session = Depends(get_db), request: Request = Request):
    """
        Удаляет связь сокращенной ссылки с БД.
        :param short_code: Короткий код ссылки
        :return: HTTP 204 No Content
    """
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не авторизован"
            )
        current_user = await get_current_user(db, token)
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не авторизован"
            )
        result = await db.execute(select(Link).filter_by(short_code=short_code))
        current_link = result.scalars().first()

        if not current_link:
            raise HTTPException(status_code=404, detail="Ссылка не найдена")

        await db.delete(current_link)
        await db.commit()
        return JSONResponse(status_code=204, content={})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{short_code}")
async def update_link(
        short_code: str,
        new_code: str = None,
        request: Request = Request,
        db: AsyncSession = Depends(get_db),
):
    """
    Обновляет связь сокращенной ссылки с БД.
    :param short_code: Короткий код ссылки
    :param new_code: Новый короткий код
    :return: Статус обновления
    """
    try:
        if not new_code:
            raise HTTPException(status_code=400, detail="Новый короткий код не указан")

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не авторизован"
            )

        current_user = await get_current_user(db, token)
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Пользователь не авторизован"
            )

        result = await db.execute(select(Link).filter_by(short_code=short_code))
        current_link = result.scalars().first()

        if not current_link:
            raise HTTPException(status_code=404, detail="Ссылка не найдена")

        await update_link_in_db(db, current_link, new_code)

        return JSONResponse(status_code=200, content={"message": "Ссылка обновлена"})

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{short_code}/stats")
@cache(expire=1200)  # Кэшируем результат на 1200 секунд (20 минут)
async def get_link_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    """
    Получение статистики для сокращенной ссылки.
    :param short_code: Короткий код ссылки
    :return: Информация о ссылке
    """
    try:
        result = await db.execute(select(Link).filter_by(short_code=short_code))
        link = result.scalars().first()

        if not link:
            raise HTTPException(status_code=404, detail="Ссылка не найдена")

        content = {
            "original_url": link.original_url,
            "created_at": str(link.created_at),
            "clicks": link.clicks,
            "last_used_at": str(link.last_used_at)
        }

        return JSONResponse(status_code=200, content=content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{original_url}")
async def search_link(original_url: str, db: AsyncSession = Depends(get_db)):
    """
    Поиск ссылок по URL.
    :param original_url: Оригинальный URL, по которому ищем ссылку.
    :param db: Сессия базы данных.
    :return: JSON-ответ с информацией о найденных ссылках.
    """
    try:
        result = await db.execute(select(Link).filter_by(original_url=original_url))
        links = result.scalars().all()

        if not links:
            raise HTTPException(status_code=404, detail="Ссылки не найдена")

        return JSONResponse(status_code=200, content=[
            {
                "short_code": link.short_code,
                "original_url": link.original_url,
                "created_at": str(link.created_at),
                "clicks": link.clicks,
                "last_used_at": str(link.last_used_at)
            }
            for link in links
        ])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-unused-links")
async def delete_unused_links_handler(days: int, db: AsyncSession = Depends(get_db)):
    """
    API для удаления ссылок, которые не использовались N дней.
    :param days: Количество дней, после которых ссылки считаются неиспользуемыми
    :return: Статус задачи
    """
    try:
        task = delete_unused_links.delay(days)
        return JSONResponse(
            status_code=200,
            content={
                "task_id": task.id,
                "status": "task started"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Получение статуса выполнения задачи.
    :param task_id: ID задачи, полученный при отправке задачи
    :return: Статус задачи
    """
    task_result = AsyncResult(task_id)
    return JSONResponse(status_code=200, content={"status": task_result.status})