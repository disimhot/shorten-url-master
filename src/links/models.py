from pydantic import BaseModel
from typing import Optional
from datetime import datetime
class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = datetime.now()
