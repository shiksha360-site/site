import json
import os
import shutil
from sdk import common, video_crawler
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, List


def gen_info():
    global session 
    session = video_crawler.prepare()

    # Basic setup
    env = Environment(
        loader=FileSystemLoader("templates/jinja2"),
        autoescape=select_autoescape()
    )

    env.trim_blocks = True
    env.lstrip_blocks = True

    shutil.rmtree("build", ignore_errors=True)
    pathlib.Path("build/keystone").mkdir(parents=True)

    boards_data = common.load_yaml("core/boards.yaml")
    langs = common.load_yaml("core/langs.yaml")
    sources = common.load_yaml("core/sources.yaml")
    subjects_data = common.load_yaml("core/subjects.yaml")

    boards_data = [board.lower() for board in boards_data]

    with open("build/keystone/sources.min.json", "w") as sources_fp:
        common.write_min_json(sources, sources_fp)

    with open("build/keystone/subjects.min.json", "w") as subjects_fp:
        common.write_min_json(subjects_data, subjects_fp)

    with open("build/keystone/boards.min.json", "w") as boards_fp:
        common.write_min_json(boards_data, boards_fp)

    with open("build/keystone/langs.min.json", "w") as langs_fp:
        common.write_min_json(langs, langs_fp)

    # Create grades
    grades: list = []
    tags: list = []
    grade_boards: Dict[int, List[str]] = {}

    walker = os.walk("grades")

    for dirpath, boards, _ in walker:
        # We want the subject jsons not the grades
        if dirpath == "grades":
            continue
        
        dir_split = dirpath.split("/")
        
        # Check if we are iterating over a grade. If dir_split is equal to 2: the folder is of the form grades/{GRADE}
        grade = dir_split[1]
        if grade.isdigit() and len(dir_split) == 2:
            grade = int(grade)

            grades.append(grade)
            grade_boards[grade] = []

            print(f"Analysing grade {grade} with boards {boards}")

            for board in boards:
                # Check if we are iterating over a supported board where boards is all supported boards as per boards.yaml
                if board.lower() not in boards_data:
                    print(f"WARNING: {board.upper()} not in core/boards.yaml ({boards})")
                    continue

                board = board.lower()
                grade_boards[grade].append(board.lower())
            
                print(f"Found board {board.upper()}")

                subject_list = []
                    
                board = board.lower()
                _, subjects, _ = next(walker)
                for subject in subjects:
                    if subject.lower() not in subjects_data.keys():
                        print(f"WARNING: {subject.lower()} not in core/subjects.yaml")
                        continue

                    print(f"Found subject {subject} in board {board.upper()}")

                    subject_list.append(subject.lower())

                    subject_dir = os.path.join(dirpath, board, subject)

                    chapter_listing: Dict[int, int] = {}
                    for chapter in os.scandir(subject_dir):
                        if not chapter.is_dir():
                            continue
                        print(f"Adding chapter {chapter.name}")

                        chapter_dir = os.path.join(subject_dir, chapter.name)

                        # Chapter handling begins here

                        chapter_info = common.load_yaml(os.path.join(chapter_dir, "info.yaml"))

                        try:
                            chapter_listing[int(chapter.name)] = chapter_info["name"]
                        except ValueError:
                            print(f"WARNING: Invalid chapter {chapter.name}")
                            continue

                        # Check chapter info and make fixes
                        if not chapter_info.get("primary-tag"):
                            if chapter_info.get("tags"):
                                chapter_info["primary-tag"] = chapter_info["tags"][0]
                            else:
                                chapter_info["tags"] = []
                                chapter_info["primary-tag"] = "untagged"

                        tags += chapter_info["tags"]

                        chapter_res = common.load_yaml(os.path.join(chapter_dir, "res.yaml"))

                        build_chapter_dir = chapter_dir.replace("grades", "build/grades", 1)
                        pathlib.Path(build_chapter_dir).mkdir(parents=True)

                        # Check chapter res and make fixes
                        subtopics: Dict[str, str] = {}
                        for subtopic in chapter_res.keys():
                            for key in chapter_res[subtopic].keys():
                                if not chapter_res[subtopic].get(key):
                                    chapter_res[subtopic][key] = []
                                
                                value = chapter_res[subtopic][key]

                                if value == "$name":
                                    chapter_res[subtopic][key] = chapter_info["name"]
                            
                                if isinstance(value, dict) and value.get("videos"):
                                    for i, video in enumerate(value["videos"]):
                                        if video.get("js-needed"):
                                            vdata = video_crawler.get_video_with_js(session, video["link"])
                                        else:
                                            vdata = video_crawler.get_video_bs4(video["link"])
                                        value["videos"][i] = vdata
                            
                            subtopic_name = chapter_res[subtopic]["name"]
                            subtopics[subtopic_name] = subtopic

                            # Make the subtopic file
                            with open(os.path.join(build_chapter_dir, f"res-{subtopic}.min.json"), "w") as fp:
                                common.write_min_json(chapter_res[subtopic], fp)
                            
                        chapter_info["subtopics"] = subtopics

                        # Write info
                        with open(os.path.join(build_chapter_dir, "info.min.json"), "w") as chapter_info_json:
                            common.write_min_json(chapter_info, chapter_info_json)

                    chapter_listing_path = os.path.join(subject_dir.replace("grades", "build/grades", 1), "chapter_list.json")
                    with open(chapter_listing_path, "w") as chapter_listing_fp:
                        common.write_min_json(chapter_listing, chapter_listing_fp)

                with open(os.path.join("build", dirpath, board, "subject_list.min.json"), "w") as subject_list_fp:  
                    common.write_min_json(subject_list, subject_list_fp)


        if common.debug_mode:
            print(dirpath, boards)

    # Add in grade info from recorded data
    with open("build/keystone/grade_info.min.json", "w") as grades_file:
        common.write_min_json({
                "grades": grades,
                "tags": tags,
                "grade_boards": grade_boards
            },
            grades_file)

    # Create keystone.min.json using jinja2 and others
    print("Compiling HTML")
    with open("build/keystone/html.min.json", "w") as keystone:
        grades_list = env.get_template("grades_list.jinja2")
        common.write_min_json({
            "grades_list": {
                "en": common.remove_ws(grades_list.render(grades=grades, grade_boards=grade_boards, lang="en")),
                "hi": common.remove_ws(grades_list.render(grades=grades, grade_boards=grade_boards, lang="hi"))
            }
        }, keystone)
