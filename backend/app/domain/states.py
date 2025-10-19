"""Job and entity states/enums."""
from enum import Enum


class AuthorType(str, Enum):
    """Message author type."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AttachmentKind(str, Enum):
    """Attachment kind."""

    IMAGE = "image"
    VIDEO = "video"
    OTHER = "other"


