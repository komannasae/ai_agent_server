from typing import List, Optional
from pydantic import BaseModel


class PlanCreateRequest(BaseModel):
    user_id: int
    start_date: str
    end_date: str
    companion: Optional[str] = "혼자"
    theme: Optional[List[str]] = ["관광지"]
    user_message: Optional[str] = ""