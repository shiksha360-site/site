import os
import shutil
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, List, Set
from copy import deepcopy
from sdk import common
from sdk.fetcher import scrape, scrape_cache_clear
import asyncpg
import orjson

from sdk.fetcher.yt import Youtube

if os.environ.get("HTTP_SCRAPE_MODE"):
    from sdk import video_crawler

async def gen_info(db: asyncpg.Pool, yt: Youtube):
    os.chdir("data")
    if os.environ.get("HTTP_SCRAPE_MODE"):
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

    with open("build/keystone/sources.lynx", "wb") as sources_fp:
        common.write_min(sources, sources_fp)

    with open("build/keystone/subjects.lynx", "wb") as subjects_fp:
        common.write_min(subjects_data, subjects_fp)

    with open("build/keystone/boards.lynx", "wb") as boards_fp:
        common.write_min(boards_data, boards_fp)

    with open("build/keystone/langs.lynx", "wb") as langs_fp:
        common.write_min(langs, langs_fp)

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
            chapter_info = common.load_yaml(chapter / "info.yaml", ruamel_type="rt")

            chapter_info["subject"] = subject
            chapter_info["grade"] = grade
            chapter_info["board"] = board

            try:
                chapter_listing[int(chapter.name)] = {"name": chapter_info["name"], "iname": chapter_info["iname"]}
            except ValueError:
                print(f"WARNING: Invalid chapter {chapter.name}")
                continue

            build_chapter_dir = pathlib.Path(str(chapter).replace("grades", "build/grades", 1))
            build_chapter_dir.mkdir(parents=True)

            # Parse all the topics
            for topic in chapter_info["topics"]:
                chapter_info["topics"], resources = await parse_topic(db, yt, chapter_info, topic)

                with (build_chapter_dir / f"resources-{topic}.lynx").open("w") as res_json:
                    common.write_min(resources, res_json)

            # Write info
            with (build_chapter_dir / "info.lynx").open("w") as chapter_info_json:
                common.write_min(chapter_info, chapter_info_json)
            
            scrape_cache_clear()
        
        with open(os.path.join("build", "grades", str(grade), board, subject, "chapter_list.lynx"), "w") as chapter_listing_fp:
            common.write_min(chapter_listing, chapter_listing_fp)

        with open(os.path.join("build", "grades", str(grade), board, "subject_list.lynx"), "w") as subject_list_fp:  
            common.write_min(list(subject_list[grade]), subject_list_fp)

    grades: list = list(grades)
    grades.sort()

    grade_boards = {k: list(v) for k, v in grade_boards.items()}

    # Add in grade info from recorded data
    with open("build/keystone/grade_info.lynx", "w") as grades_file:
        common.write_min({
                "grades": grades,
                "grade_boards": grade_boards
        },
        grades_file)

    # Create keystone.lynx using jinja2 and others
    print("Compiling HTML")
    with open("build/keystone/html.lynx", "w") as keystone:
        grades_list = env.get_template("grades_list.jinja2")
        common.write_min({
            "grades_list": {
                "en": common.remove_ws(grades_list.render(grades=grades, grade_boards=grade_boards, lang="en")),
                "hi": common.remove_ws(grades_list.render(grades=grades, grade_boards=grade_boards, lang="hi"))
            }
        }, keystone)
    
    if os.getcwd().endswith("data"):
        os.chdir("..")


async def parse_topic(db: asyncpg.Pool, yt: Youtube, chapter_info: dict, topic: str):
    # Fix and add proper reject stuff
    if chapter_info["topics"][topic].get("reject") is None:
        chapter_info["topics"][topic]["reject"] = []

    if chapter_info["topics"][topic].get("accept") is None:
        chapter_info["topics"][topic]["accept"] = []

    if chapter_info["topics"][topic].get("subtopics") is None:
        chapter_info["topics"][topic]["subtopics"] = {}

    if chapter_info["topics"][topic].get("name", "$name") == "$name":
        chapter_info["topics"][topic]["name"] = chapter_info["name"]
    
    async def resource_parse(topic, subtopic_parent):
        def sort_by_view_count(d):
            return d["view_count"]

        sql = "SELECT resource_title, resource_type, resource_id, resource_author, resource_metadata, resource_description FROM topic_resources WHERE grade = $1 AND board = $2 AND subject = $3 AND chapter_iname = $4 AND topic_iname = $5"

        args = [chapter_info["grade"], chapter_info["board"], chapter_info["subject"], chapter_info["iname"], topic]

        if subtopic_parent:
            sql += " AND subtopic_parent = $6"
            args.append(subtopic_parent)
        else:
            sql += " AND NOT subtopic_parent <> ''"

        sql += " AND disabled = false ORDER BY resource_metadata['view_count']"

        resources = await db.fetch(sql, *args)
        print(f"Parsing resource {resources} for topic {topic} and subtopic_parent {subtopic_parent}")

        dat = []

        taken_pos = {}
        for i, res in enumerate(resources):
            dat.append(dict(res))
            dat[-1]["resource_id"] = str(dat[-1]["resource_id"])
            dat[-1]["resource_metadata"] = orjson.loads(dat[-1]["resource_metadata"])

            pos = dat[-1]["resource_metadata"].get("override_pos", i)

            # 0, 1, 2, 3, 4, 5, 6, 7, 8 O-> 6, 9, 10

            if pos in taken_pos.keys():
                # Swap bad element and current element
                bad_element = taken_pos[pos]
                dat[bad_element]["pos"] = i
                dat[i]["pos"] = bad_element
                print(f"WARNING: Resource with ID {dat[-1]['resource_id']} has invalid pos {pos} that is taken ({taken_pos}). Swapping elements {bad_element} and element {i}")
                pos = i
            else:
                dat[-1]["pos"] = pos

            taken_pos[pos] = i

                
        dat = sorted(dat, key=lambda x: x["resource_metadata"].get("view_count", 0), reverse=True)
        
        return dat
    
    resources = {}

    resources["_main"] = await resource_parse(topic, None)

    for subtopic in deepcopy(chapter_info["topics"][topic]["subtopics"]):
        resources[subtopic] = await resource_parse(subtopic, topic)

    if yt:
        os.chdir("..")
        scrape(yt, chapter_info, topic)
        os.chdir("data")

    return chapter_info["topics"], resources