from typing import Generic, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class ErrorInfo(BaseModel):
    code: str
    message: str
    detail: Optional[dict] = None


class ApiResponse(GenericModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorInfo] = None
