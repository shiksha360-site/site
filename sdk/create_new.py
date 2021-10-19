import os
import shutil
from pathlib import Path
import sys
from sdk import common

def create_new():
    boards = common.load_yaml("core/boards.yaml")
    subjects = common.load_yaml("core/subjects.yaml")

    # Create the grade
    grade = common.input_int("Enter grade? ")

    if grade > 12 or grade <= 0:
        print("Invalid grade")
        sys.exit(-1)

    grade_path = f"grades/{grade}"

    if not os.path.exists("grades"):
        os.mkdir("grades")

    if not os.path.exists(grade_path):
        os.mkdir(grade_path)

    board = input("Enter board? ")

    if board.upper() not in boards:
        print("Board not in core/boards.yaml!")
        sys.exit(-1)

    board_path = f"{grade_path}/{board.lower()}"

    if not os.path.exists(board_path):
        os.mkdir(board_path)

    subject = input("Enter subject name? ")

    if subject.lower() not in subjects.keys():
        print("Subject not in core/subjects.yaml!")
        sys.exit(-1)  

    subject_path = f"{board_path}/{subject.lower()}"

    if not os.path.exists(subject_path):
        os.mkdir(subject_path)

    chapters = [int(chapter) for chapter in os.listdir(subject_path)]

    if chapters:
        chapters.sort()
        next_chapter = chapters[-1] + 1
    else:
        next_chapter = 1

    chapter_path = f"{subject_path}/{next_chapter}"

    os.mkdir(chapter_path)

    shutil.copyfile("templates/chapter_info.yaml", f"{chapter_path}/info.yaml")
    shutil.copyfile("templates/chapter_extresources.yaml", f"{chapter_path}/extres.yaml")

    with Path(f"{chapter_path}/info.yaml").open("a") as info:
        info.write(f"\nsubject: {subject.lower()}\ngrade: {grade}\nboard: {board.lower()}")