import os
from typing import Dict, List, Tuple, Optional

def get_subject(chapter_info: dict) -> Tuple[str, Optional[str], bool]:
    subject = chapter_info["subject"]
    grade = chapter_info["grade"]

    if grade > 8:
        return subject, None, False
    else:
        if subject in ("biology", "physics", "chemistry"):
            return subject, "science", True
        return subject, None, True

def print_kwmap(kwmap: List[str]):
    print([(title, k["weight"]) for title, k in [a for a in kwmap]])

def create_kwlist(chapter_info: dict, subtopic: str):
    weight = 2 if subtopic == "key" else 3
    keywords = {tag: weight for tag in chapter_info["topics"][subtopic]["accept"]}
    reject =  [tag for tag in chapter_info["topics"][subtopic]["reject"]]
    return keywords, reject