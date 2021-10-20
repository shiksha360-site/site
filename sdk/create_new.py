import os
import shutil
from pathlib import Path
import sys
from sdk import common
import uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape

def create_new():
    boards = common.load_yaml("core/boards.yaml")
    subjects = common.load_yaml("core/subjects.yaml")

    # Create the grade
    grade = common.input_int("Enter grade? ")

    if grade > 12 or grade <= 0:
        print("Invalid grade")
        sys.exit(-1)

    grade_path = Path(f"grades/{grade}")

    board = input("Enter board? ")

    if board.upper() not in boards:
        print("Board not in core/boards.yaml!")
        sys.exit(-1)

    subject = input("Enter subject name? ")

    if subject.lower() not in subjects.keys():
        print("Subject not in core/subjects.yaml!")
        sys.exit(-1)  

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
        loader=FileSystemLoader("templates/yaml"),
        autoescape=select_autoescape()
    )

    info = env.get_template("chapter_info.yaml")

    data = info.render(
        id=str(uuid.uuid4()),
        name=name
    )

    with (chapter_path / "info.yaml").open("w") as info:
        info.write(data)

    shutil.copyfile("templates/yaml/chapter_extresources.yaml", f"{chapter_path}/extres.yaml")