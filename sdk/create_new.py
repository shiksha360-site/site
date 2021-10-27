import os
import shutil
from pathlib import Path
import sys
from sdk import common
import uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape

def create_new(grade: int, board: str, subject: str, name: str, iname: str):
    boards = common.load_yaml("data/core/boards.yaml")
    subjects = common.load_yaml("data/core/subjects.yaml")

    # Create the grade
    if grade > 12 or grade <= 0:
        return "Invalid grade", None

    grade_path = Path(f"data/grades/{grade}")

    if board.upper() not in boards:
        return "Board not in core/boards.yaml!", None

    if subject.lower() not in subjects.keys():
        return "Subject not in core/subjects.yaml!", None

    # Check and handle alias and supported-grades
    if grade not in subjects.get("supported-grades", [grade]):
        return "Grade not supported by subject", None
    
    if grade < 9:
        print(subjects)
        subject = subjects[subject].get("alias", subject) or subject

    # Actual creation
    subject_path = grade_path / board.lower() / subject.lower()

    try:
        chapters = [int(chapter.name) for chapter in subject_path.iterdir()]
    except (FileNotFoundError, ValueError):
        chapters = []

    if chapters:
        chapters.sort()
        next_chapter = chapters[-1] + 1
    else:
        next_chapter = 1

    chapter_path = subject_path / str(next_chapter)

    chapter_path.mkdir(exist_ok=True, parents=True)

    # Basic setup of jinja2
    env = Environment(
        loader=FileSystemLoader("data/templates/yaml"),
        autoescape=select_autoescape(),
    )
    env.globals = {"uuid_gen": lambda: str(uuid.uuid4())}


    info = env.get_template("chapter_info.yaml")

    data = info.render(
        iname=iname,
        name=name
    )

    with (chapter_path / "info.yaml").open("w") as info:
        info.write(data)

    return None, {"chapter": next_chapter, "iname": iname}