import os
import shutil
from pathlib import Path
import sys
from sdk import common
import uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape

def create_new(grade: int = None, board: str = None, subject: str = None):
    boards = common.load_yaml("data/core/boards.yaml")
    subjects = common.load_yaml("data/core/subjects.yaml")

    # Create the grade
    if not grade:
        grade = common.input_int("Enter grade? ")

    if grade > 12 or grade <= 0:
        return "Invalid grade"

    grade_path = Path(f"data/grades/{grade}")

    if not board:
        board = input("Enter board? ")

    if board.upper() not in boards:
        return "Board not in core/boards.yaml!"

    if not subject:
        subject = input("Enter subject name? ")

    if subject.lower() not in subjects.keys():
        return "Subject not in core/subjects.yaml!"

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

    name = input("Enter the chapter name: ")

    chapter_path.mkdir(exist_ok=True, parents=True)

    # Basic setup of jinja2
    env = Environment(
        loader=FileSystemLoader("data/templates/yaml"),
        autoescape=select_autoescape()
    )

    info = env.get_template("chapter_info.yaml")

    data = info.render(
        id=str(uuid.uuid4()),
        name=name
    )

    with (chapter_path / "info.yaml").open("w") as info:
        info.write(data)

    shutil.copyfile("data/templates/yaml/chapter_extresources.yaml", f"{chapter_path}/extres.yaml")