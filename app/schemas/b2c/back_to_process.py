from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict



class BackToProcessIn(BaseModel):
	expa_person_id: str



class BackToProcessOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	expa_person_id: str

	created_at: datetime
	full_name: str

	email: Optional[str] = None
	phone: Optional[str] = None

	expa_status: Optional[str] = None
	selected_programmes: Optional[str] = None

	home_lc_name: str
	home_mc_name: str
	home_lc_id: int
	home_mc_id: int

	inserted_at: datetime
	updated_at: datetime
