"""Job and entity states/enums."""
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELED = "CANCELED"


class AuthorType(str, Enum):
    """Message author type."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolType(str, Enum):
    """Tool type for generation."""

    TEXT_TO_IMAGE = "text_to_image"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    SPEAK = "speak"


class AttachmentKind(str, Enum):
    """Attachment kind."""

    IMAGE = "image"
    VIDEO = "video"
    OTHER = "other"


# Terminal job statuses
TERMINAL_STATUSES = {
    JobStatus.SUCCEEDED,
    JobStatus.FAILED,
    JobStatus.TIMEOUT,
    JobStatus.CANCELED,
}

