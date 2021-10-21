from __future__ import annotations
from pydantic import BaseModel
from typing import ForwardRef, List, Optional, Dict
import uuid
from enum import IntEnum, Enum

class Grade(IntEnum):
    grade6 = 6
    grade7 = 7
    grade8 = 8
    grade9 = 9
    grade10 = 10
    grade11 = 11
    grade12 = 12

class Board(str, Enum):
    cbse = "cbse"

class Subject(str, Enum):
    biology = "biology"
    physics = "physics"
    chemistry = "chemistry"
    math = "math"
    english = "english"

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
    id: uuid.UUID
    name: str
    grade: int
    board: str
    subject: str
    study_time: int
    topics: Dict[str, Topic]

class Chapter(APIResponse):
    chapters: List[ChapterData]