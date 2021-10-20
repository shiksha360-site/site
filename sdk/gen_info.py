import json
import os
import shutil
from sdk import common, video_crawler
from sdk.fetcher import scrape, scrape_cache_clear
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, List, Set
from copy import deepcopy

from sdk.fetcher.yt import Youtube


def gen_info(yt: Youtube, selenium_scrape: bool = False):
    if selenium_scrape:
        session = video_crawler.prepare()
    else:
        session = None

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
    grades: set = set()
    grade_boards: Dict[int, Set[str]] = {}
    subject_list: Dict[int, Set[str]] = {}

    for path in pathlib.Path("grades").rglob("*/*/*"):
        if path.is_file():
            continue

        if len(path.parts) != 4:
            continue

        print(path)

        _, grade, board, subject = path.parts

        try:
            grade = int(grade)
        except ValueError:
            print(f"WARNING: Grade {grade} is invalid!")
        
        board = board.lower()
        subject = subject.lower()

        if board not in boards_data:
            print(f"WARNING: {board.upper()} not in core/boards.yaml ({boards_data})")
            continue
            
        if subject not in subjects_data.keys():
            print(f"WARNING: {subject.lower()} not in core/subjects.yaml")
            continue

        grades.add(grade)
        if not grade_boards.get(grade):
            grade_boards[grade] = set()
        
        grade_boards[grade].add(board.lower())
            
        print(f"Found board {board.upper()}")

        if not subject_list.get(grade):
            subject_list[grade] = set()
        
        subject_list[grade].add(subject)


        print(f"Found subject {subject} in board {board.upper()} of grade {grade}")

        chapter_listing: Dict[int, int] = {}

        for chapter in path.iterdir():
            if not chapter.is_dir():
                continue
            
            print(f"Adding chapter {chapter.name}")

            # Chapter handling begins here
            chapter_info = common.load_yaml(chapter / "info.yaml")

            chapter_info["subject"] = subject
            chapter_info["grade"] = grade
            chapter_info["board"] = board


            try:
                chapter_listing[int(chapter.name)] = chapter_info["name"]
            except ValueError:
                print(f"WARNING: Invalid chapter {chapter.name}")
                continue

            chapter_res = common.load_yaml(chapter / "extres.yaml")

            build_chapter_dir = pathlib.Path(str(chapter).replace("grades", "build/grades", 1))
            build_chapter_dir.mkdir(parents=True)

            # Parse all the topics
            for topic in chapter_info["topics"]:
                chapter_info["topics"], chapter_res = parse_topic(yt, chapter_info, chapter_res, build_chapter_dir, session, topic)
                                                
            # Write info
            with (build_chapter_dir / "info.min.json").open("w") as chapter_info_json:
                common.write_min_json(chapter_info, chapter_info_json)
            
            scrape_cache_clear()
        
        with open(os.path.join("build", "grades", str(grade), board, subject, "chapter_list.min.json"), "w") as chapter_listing_fp:
            common.write_min_json(chapter_listing, chapter_listing_fp)

        with open(os.path.join("build", "grades", str(grade), board, "subject_list.min.json"), "w") as subject_list_fp:  
            common.write_min_json(list(subject_list[grade]), subject_list_fp)

    grades: list = list(grades)
    grades.sort()

    grade_boards = {k: list(v) for k, v in grade_boards.items()}

    # Add in grade info from recorded data
    with open("build/keystone/grade_info.min.json", "w") as grades_file:
        common.write_min_json({
                "grades": grades,
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


def parse_topic(yt: Youtube, chapter_info, chapter_res, build_chapter_dir, session, topic):
    # Fix and add proper reject stuff
    if chapter_info["topics"][topic].get("reject") is None:
        chapter_info["topics"][topic]["reject"] = []

    if chapter_info["topics"][topic].get("accept") is None:
        chapter_info["topics"][topic]["accept"] = []

    if chapter_info["topics"][topic].get("subtopics") is None:
        chapter_info["topics"][topic]["subtopics"] = {}

    if chapter_info["topics"][topic].get("name", "$name") == "$name":
        chapter_info["topics"][topic]["name"] = chapter_info["name"]

    os.chdir("..")
    scrape(yt, chapter_info, topic)
    os.chdir("data")

    # Check chapter res and make fixes
    for subtopic in chapter_res.keys():
        # Ensure all None keys are made empty lists
        for key in chapter_res[subtopic].keys():
            if not chapter_res[subtopic].get(key):
                chapter_res[subtopic][key] = []
                        
            value = chapter_res[subtopic][key]
                    
            if isinstance(value, list):
                # Go through list of all videos and scrape the site for title
                for i, video in enumerate(value):
                    if not isinstance(video, dict):
                        continue

                    if video.get("js-needed"):
                        vdata = video_crawler.get_video_with_js(session, video["link"])
                    else:
                        vdata = video_crawler.get_video_bs4(video["link"])
                    value[i] = vdata
                    
        # Make the subtopic file
        with (build_chapter_dir / f"res-{subtopic}.min.json").open("w") as fp:
            common.write_min_json(chapter_res[subtopic], fp)
    
    return chapter_info["topics"], chapter_res