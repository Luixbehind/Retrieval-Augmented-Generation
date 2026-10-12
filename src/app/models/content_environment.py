from __future__ import annotations

from enum import Enum


class ContentEnvironmentEnum(str, Enum):
    EDIT = "EDIT"
    PUBLISHED = "PUBLISHED"
