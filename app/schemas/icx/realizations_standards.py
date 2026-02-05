from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ICXRealizationsStandardsUpdateRequest(BaseModel):
    health_insurance: Optional[bool] = None
    expectation_settings: Optional[bool] = None
    visa_and_work_permit: Optional[bool] = None
    communication_10_days_before: Optional[bool] = None
    arrival_pickup: Optional[bool] = None
    accommodation: Optional[bool] = None

    ips: Optional[bool] = None
    ops: Optional[bool] = None
    pgs: Optional[bool] = None

    alignment_space: Optional[bool] = None
    first_day_of_work: Optional[bool] = None
    job_description: Optional[bool] = None
    working_hours: Optional[bool] = None
    duration: Optional[bool] = None
    opportunity_benefits: Optional[bool] = None
    value_driven_leadership_education: Optional[bool] = None

    communication_first_10_days: Optional[bool] = None
    communication_second_10_days: Optional[bool] = None
    communication_third_10_days: Optional[bool] = None
    communication_fourth_10_days: Optional[bool] = None

    departure_support: Optional[bool] = None
    debrief: Optional[bool] = None


class ICXRealizationsStandardsResponse(BaseModel):
    application_id: str

    health_insurance: bool
    expectation_settings: bool
    visa_and_work_permit: bool
    communication_10_days_before: bool
    arrival_pickup: bool
    accommodation: bool

    ips: bool
    ops: bool
    pgs: bool

    alignment_space: bool
    first_day_of_work: bool
    job_description: bool
    working_hours: bool
    duration: bool
    opportunity_benefits: bool
    value_driven_leadership_education: bool

    communication_first_10_days: bool
    communication_second_10_days: bool
    communication_third_10_days: bool
    communication_fourth_10_days: bool

    departure_support: bool
    debrief: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
