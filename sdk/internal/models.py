from __future__ import annotations
from pydantic import BaseModel
from typing import ForwardRef, List, Optional, Dict
import uuid
from enum import IntEnum, Enum
from sdk import common

class Grade(IntEnum):
    grade6 = 6
    grade7 = 7
    grade8 = 8
    grade9 = 9
    grade10 = 10
    grade11 = 11
    grade12 = 12

Board = Enum('Board', {
    k: k for k in (common.load_yaml("data/core/boards.yaml"))
})

Subject = Enum('Subject', {
    k: k for k in (common.load_yaml("data/core/subjects.yaml").keys())
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
    subtopics: Optional[Topic] = None
    res: Optional[dict] = None

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