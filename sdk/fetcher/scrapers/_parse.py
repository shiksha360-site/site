from typing import Tuple, Optional

def get_subject(chapter_info: dict) -> Tuple[str, Optional[str], bool]:
    subject = chapter_info["subject"]
    grade = chapter_info["grade"]

    if grade > 8:
        return subject, None, False
    else:
        if subject in ("biology", "physics", "chemistry"):
            return subject, "science", True
        return subject, None, True