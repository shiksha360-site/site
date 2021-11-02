from __future__ import annotations
from pydantic import BaseModel
from typing import Any, List, Optional, Dict
from enum import IntEnum, Enum
from sdk import common
from sdk.common import Resource

# For VSCode
if True is False:
    Resource.name # Just to make VSCode think resource is being accessed

class Grade(IntEnum):
    grade5 = 5
    grade6 = 6
    grade7 = 7
    grade8 = 8
    grade9 = 9
    grade10 = 10
    grade11 = 11
    grade12 = 12

class ResourceLang(Enum):
    en = "English"
    hi = "Hindi"

Board = Enum('Board', {
    k: k for k in (common.load_yaml("data/core/boards.yaml"))
})

Subject = Enum('Subject', {
    k: k.title() for k in (common.load_yaml("data/core/subjects.yaml").keys())
})

class GitOP(str, Enum):
    push = "push"
    pull = "pull"


class APIResponse(BaseModel):
    done: bool = True
    reason: Optional[str] = None

class Topic(BaseModel):
    name: Optional[str] = "$name"
    accept: Optional[List[str]] = []
    reject: Optional[List[str]] = []
    subtopics: Optional[Dict[str, Topic]] = {}

Topic.update_forward_refs()

class ChapterData(BaseModel):
    iname: str
    name: str
    grade: int
    board: str
    subject: str
    study_time: int
    topics: Dict[str, Topic]

class Chapter(APIResponse):
    chapters: List[ChapterData]

class ResourceMetadata(BaseModel):
    resource_metadata: Dict[str, Any] = {}