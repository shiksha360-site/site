from typing import List, Optional

def get_subject(chapter_info: dict) -> List[str, Optional[str]]:
    subject = chapter_info["subject"]
    grade = chapter_info["grade"]

    if grade > 8:
        return subject, None
    else:
        if subject in ("biology", "physics", "chemistry"):
            return subject, "science"
        return subject, None