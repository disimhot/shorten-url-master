from datetime import datetime, timedelta
import asyncio
from celery import shared_task, Celery
from sqlalchemy.future import select

from src.models.models import Link, LinkArchive
from src.database import async_session

celery = Celery(
    "tasks",
    broker="redis://172.17.155.105:6379/0",
    backend="redis://172.17.155.105:6379/0",
)

@shared_task
def delete_unused_links(days: int):
    """
    Celery-таска для удаления неиспользуемых ссылок.
    """
    print(f"Запущена таска: delete_unused_links({days})")
    asyncio.run(delete_old_links(days))  # Запускаем async-функцию

async def delete_old_links(days: int):
    """
    Асинхронная функция для удаления старых ссылок.
    """
    async with async_session() as session:  # Создаем сессию
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await session.execute(select(Link).filter(Link.last_used_at < cutoff_date))
        links_to_delete = result.scalars().all()

        if links_to_delete:
            print(f"Найдено {len(links_to_delete)} неиспользуемых ссылок")

            for link in links_to_delete:
                link_archive = LinkArchive(
                    short_code=link.short_code,
                    original_url=link.original_url,
                    deleted_at=datetime.now(),
                    reason="Неиспользуемая ссылка"
                )
                session.add(link_archive)

            for link in links_to_delete:
                await session.delete(link)

            await session.commit()

        print("Удаление завершено.")
