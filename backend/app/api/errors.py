"""API error handling."""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    """Base API error."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
        self.code = code


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": str(exc.detail)},
    )

