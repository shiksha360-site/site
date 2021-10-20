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
    keywords = {tag: 2 for tag in chapter_info["tags"]["accept"] if chapter_info["tags"]["accept"]}
    reject =  [tag for tag in chapter_info["tags"]["reject"]]
    if chapter_info["subtopic-tags"].get(subtopic):
        keywords.update({tag: 3 for tag in chapter_info["subtopic-tags"][subtopic]["accept"]})
        reject += [tag for tag in chapter_info["subtopic-tags"][subtopic]["reject"]]
    return keywords, reject