from datetime import datetime, timedelta
import asyncio
from celery import Celery
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from src.models.models import Link, LinkArchive
from src.database import async_session


celery = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

@celery.task
def delete_unused_links(days: int):
    """
    Celery-таска для удаления неиспользуемых ссылок.
    """
    print(f"Запущена таска: delete_unused_links({days})")
    asyncio.run(delete_old_links(days))

async def delete_old_links(days: int):
    async with async_session() as session:
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await session.execute(select(Link).filter(Link.last_used_at < cutoff_date))
        links_to_delete = result.scalars().all()
        print('links_to_delete', links_to_delete)

        if links_to_delete:
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
