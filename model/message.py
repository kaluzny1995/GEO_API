"""Response message models shared by the API endpoints."""

from pydantic import BaseModel, ConfigDict


class ResponseMessage(BaseModel):
    """Standard API response message.

    Attributes:
        title: Short message title.
        description: Detailed message description.
        code: HTTP status code.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "title": "Message title",
                "description": "Long description of message details.",
                "code": 200,
            }
        },
    )

    title: str
    description: str
    code: int
