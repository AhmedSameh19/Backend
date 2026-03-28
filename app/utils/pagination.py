import math
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel
from fastapi import Query

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    limit: int
    totalItems: int
    totalPages: int
    hasNextPage: bool
    hasPrevPage: bool

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta

def build_pagination_response(data: List[T], total: int, page: int, limit: int) -> PaginatedResponse[T]:
    """
    Builds the standardized paginated response envelope.
    """
    total_pages = math.ceil(total / limit) if limit > 0 else 0
    return PaginatedResponse(
        data=data,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            totalItems=total,
            totalPages=total_pages,
            hasNextPage=page < total_pages,
            hasPrevPage=page > 1
        )
    )

class PaginationParams:
    """
    FastAPI dependency for extracting standardized pagination parameters from query strings.
    Automatically enforces defaults and a maximum limit of 100.
    """
    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        sortBy: str = Query("created_at", description="Field to sort by"),
        sortOrder: str = Query("desc", description="asc or desc"),
        search: Optional[str] = Query(None, description="Global search keyword")
    ):
        self.page = page
        self.limit = limit
        self.skip = (page - 1) * limit
        self.sortBy = sortBy
        self.sortOrder = sortOrder
        self.search = search

