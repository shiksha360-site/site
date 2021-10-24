import shutil
from fastapi import FastAPI, APIRouter, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi_restful.openapi import simplify_operation_ids
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError, ValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sdk.fetcher.yt.api import Youtube
from .models import Chapter, Grade, Board, Subject, GitOP, ResourceMetadata
import asyncpg
from lynxfall.utils.fastapi import api_success, api_error
from sdk.create_new import create_new
from .cfg import API_VERSION
from sdk.api_common.error import WebError
from sdk.api_common.request_handler import KalanRequestHandler
from ruamel.yaml import YAML
from sdk import common, gen_info, compilestatic
from pathlib import Path
import os
import contextlib
from io import StringIO
from typing import Dict, List
from copy import deepcopy
import orjson
import uuid
import functools

key_data = common.load_yaml("data/core/internal_api.yaml")

nsc_regex ="^(?![0-9.-])(?!.*[0-9.-]$)(?!.*\d-)(?!.*-\d)[a-zA-Z0-9-]+$" # To reject all special characters other than numbers and hyphens


app = FastAPI(
    openapi_url="/openapi",
    docs_url=None, # We use custom swagger
    title=key_data["title"],
    description=key_data["description"],
    version="1.0",
)

@app.get("/", include_in_schema=False)
@app.get("/internal", include_in_schema=False)
async def custom_swagger_ui_html(beta: bool = False):
    """Internal Admin Tool"""
    if beta:
        return RedirectResponse("/swagger-ui/beta.html")
    return RedirectResponse("/swagger-ui/index.html")

# Mount custom swagger
app.mount("/swagger-ui", StaticFiles(directory="sdk/api_common/swagger_ui/4"), name="swagger-ui")

router = APIRouter(
    tags=["Internal"]
)

@app.on_event("startup")
async def on_startup():
    app.state.db = await asyncpg.create_pool()
    app.state.ipc_up = True # We use lots of code from Fates List, so we need to set these to True
    app.state.first_run = True
    app.state.gunicorn = False
    app.state.is_internal = True

# Setup exception handling
@app.exception_handler(403)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
@app.exception_handler(500)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)
@app.exception_handler(StarletteHTTPException)
async def _fl_error_handler(request, exc):
    return await WebError.error_handler(request, exc, log=True)

# Add request handler
app.add_middleware(
    KalanRequestHandler, 
    exc_handler=WebError.error_handler,
    api_ver=API_VERSION
)


# Actual endpoints
@router.put("/subjects")
def add_or_edit_subject(
    subject_name_friendly: str = Query(
        ...,
        description="Friendly name for the subject that is user-visible"
    ),
    subject_name_internal: str = Query(
        ...,
        description="Internal subject name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible",
        minlength=2,
        regex=nsc_regex # To reject all special characters other than numbers and hyphens
    ),
    description: str = Query(
        ...,
        description="Description for the subject. This is just there in case we want it in the future (and so we can be more like Khan Academy in design)"
    ),
    image: str = Query(
        ...,
        description="Image for the subject. This is just there in case we want it in the future (and so we can be more like Khan Academy in design)"
    ),
    alias: str = Query(
        None, 
        description="(Internal Tool Only) Alias for the subject for grade 10 and below. Example is science for biology/physics/chemistry. This is present due to current limitations in swagger. Leave blank to not alias. Only used in internal tool",
    ),
    supported_grades: List[Grade] = Query(
        ...,
        description="What grades this subject supports"
    )
):
    """**NOTE** A restart is needed for some changes to take effect"""
    subjects = common.load_yaml("data/core/subjects.yaml", ruamel_type="rt")
    subjects[subject_name_internal] = {
        "name": subject_name_friendly,
        "desc": description,
        "image": image,
        "alias": alias,
        "supported-grades": [a.value for a in supported_grades]
    }
    common.dump_yaml("data/core/subjects.yaml", subjects)
    return api_success(reason="You will need to restart the webserver for the new subjects to be populated!")

    
@router.post("/chapters")
def new_chapter(
    grade: Grade, 
    board: Board, 
    subject: Subject, 
    name: str = Query(..., description="Name of the chapter"),
    iname: str = Query(
        ..., 
        description="Internal chapter name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible\n\n**Do not reuse the same internal name more than once**",
        minlength=2,
        regex=nsc_regex
    )
):
    """
    Creates a new chapter in the syllabus
    """
    rc, ctx = create_new(grade=grade.value, board=board.value.lower(), subject=subject.value.lower(), name=name, iname=iname)
    if rc:
        return api_error(rc)
    return api_success(ctx=ctx)

@router.patch("/chapter/props")
def edit_chapter_props(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,
    name: str = Query(None, description="Name of the chapter"),
    study_time: int = Query(None, description="Study time of the chapter")
):
    """Edits the chapter properties (currently only name and study time)"""
    info_yaml = Path("data/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / str(chapter) / "info.yaml"
    if not info_yaml.exists():
        return api_error("Chapter does not exist!", status_code=404)
    data = common.load_yaml(info_yaml, ruamel_type="rt")
    if name:
        data["name"] = name
    if study_time:
        data["study-time"] = study_time
    common.dump_yaml(info_yaml, data)
    return api_success()

@router.get("/chapters", response_model=Chapter)
def get_chapters(grade: int = None, board: str = None, subject: str = None, chapter: int = None, parse_full: bool = False):
    chapters = []
    for path in Path("data/grades").rglob("*/*/*"):
        if not path.name.endswith("info.yaml"):
            continue
        _, _, _grade, _board, _subject, _chapter, _ = path.parts
        if grade and grade != _grade:
            continue
        elif board and _board != board:
            continue
        elif subject and _subject != board:
            continue
        elif chapter and _chapter != chapter:
            continue
        data = common.load_yaml(path, ruamel_type="rt")

        data["subject"] = _subject
        data["grade"] = _grade
        data["board"] = _board
        try:
            data["study_time"] = data["study-time"]
            del data["study-time"]
        except Exception:
            pass

        if parse_full:
            # Parse all the topics
            for topic in data["topics"]:
                data["topics"], _ = gen_info.parse_topic(None, data, topic)

        chapters.append(data)

    return {"chapters": chapters}

@router.put("/topics")
def add_or_edit_topic(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,
    position: int = Query(
        -1,
        description="Position of the topic. Changing this will change the position of the topi. Set -1 for end. 0 is first position"
    ),
    topic_name_friendly: str = Query(
        ..., 
        description="The user-visible/friendly name for the topic. Use `$name` if you wish for the topic name to be the name of the chapter itself",
    ),
    topic_name_internal: str = Query(
        ...,
        description="Internal topic name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible",
        minlength=2,
        regex=nsc_regex # To reject all special characters other than numbers and hyphens
    ),
    subtopic_parent: str = Query(
        None,
        description="Put the parent topic's internal topic name (topic_name_internal) if you wish to make a subtopic of a topic"
    ),
    accept_tags: List[str] = Query(
        None,
        description="Accept tags in scraper"
    ),
    reject_tags: List[str] = Query(
        None,
        description="Reject tags in scraper"
    )
):
    """
    Creates or updates an existing topic
    
    This also handles initially creating the topic/subtopic in the database as well as in the YAML

    **NOTE** This does not handle adding videos to a topic. Use /topics/videos for that
    """
    info_yaml = Path("data/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / str(chapter) / "info.yaml"
    if not info_yaml.exists():
        return api_error("Chapter does not exist!", status_code=404)
    data = common.load_yaml(info_yaml, ruamel_type="rt")

    ext = {
        "name": topic_name_friendly,
        "accept": accept_tags,
        "reject": reject_tags,
        "subtopics": None
    }

    if not subtopic_parent:
        if data["topics"].get(topic_name_internal):
            bak = data["topics"][topic_name_internal]["subtopics"]
        else:
            bak = None
        if position > -1:
            data["topics"].insert(position, topic_name_internal, ext)
        else:
            data["topics"][topic_name_internal] = ext
        data["topics"][topic_name_internal]["subtopics"] = bak
    else:
        if not data["topics"].get(subtopic_parent):
            return api_error("Parent topic does not exist!")
        if not data["topics"][subtopic_parent]["subtopics"]:
            data["topics"][subtopic_parent]["subtopics"] = {}
        if position > -1:
            data["topics"][subtopic_parent]["subtopics"].insert(position, topic_name_internal, ext)
        else:
            data["topics"][subtopic_parent]["subtopics"][topic_name_internal] = ext
    
    common.dump_yaml(info_yaml, data)
    return api_success(count=len(data["topics"].values()), mc_analyze=len(data["topics"].get("main", {}).get("subtopics", {}).values()), force_200=True)

@router.patch("/topics/position")
def change_topic_position(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,
    position: int = Query(
        -1,
        description="Position of the topic. Changing this will change the position of the topic. Set -1 for end. 0 is first position"
    ),
    topic_name_internal: str = Query(
        ...,
        description="Internal topic name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible",
        minlength=2,
        regex=nsc_regex # To reject all special characters other than numbers and hyphens
    ),
    subtopic_parent: str = Query(
        None,
        description="Put the parent topic's internal topic name (topic_name_internal) if you wish to make a subtopic of a topic"
    ),
):
    info_yaml = Path("data/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / str(chapter) / "info.yaml"
    if not info_yaml.exists():
        return api_error("Chapter does not exist!", status_code=404)
    data = common.load_yaml(info_yaml, ruamel_type="rt")

    if not subtopic_parent:
        if not data["topics"].get(topic_name_internal):
            return api_error("Topic does not exist!")
        bak = deepcopy(data["topics"][topic_name_internal])
        del data["topics"][topic_name_internal]
        if position > -1:
            data["topics"].insert(position, topic_name_internal, bak)
        else:
            data["topics"][topic_name_internal] = bak
    else:
        if not data["topics"].get(subtopic_parent):
            return api_error("Parent topic does not exist!")
        if not data["topics"][subtopic_parent].get("subtopics", {}).get(topic_name_internal):
            return api_error("This topic does not have this subtopic!")
        bak = deepcopy(data["topics"][subtopic_parent]["subtopics"][topic_name_internal])
        del data["topics"][subtopic_parent]["subtopics"][topic_name_internal]
        if position > -1:
            data["topics"][subtopic_parent]["subtopics"].insert(position, topic_name_internal, bak)
        else:
            data["topics"][subtopic_parent]["subtopics"][topic_name_internal] = bak
    
    common.dump_yaml(info_yaml, data)
    return api_success()


@router.put("/topics/resources")
async def new_resource(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,
    resource_metadata: ResourceMetadata,
    topic_name_internal: str = Query(
        ...,
        description="Internal topic name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible",
        minlength=2,
        regex=nsc_regex # To reject all special characters other than numbers and hyphens
    ),
    subtopic_parent: str = Query(
        "",
        description="Put the parent topic's internal topic name (topic_name_internal) if you wish to make a subtopic of a topic"
    ),
    resource_type: common.ResourceList = Query(
        ...,
        description="Resource type"
    ),
    resource_title: str = Query(
        None,
        description="**Optional for videos on youtube as those are gotten using the youtube api if no resource title is provided**\n\nThe title of the resource. On youtube videos, this is the name of the video by default *unless* overriden"
    ),
    resource_url: str = Query(
        ...,
        description="Resource URL"
    ),
    resource_description: str = Query(
        None,
        description="Optional description for the resource"
    ),
    resource_author: str = Query(
        None,
        description="**Optional for videos on youtube as those are gotten using the youtube api if no resource author is provided**.\n\nThe author of the resource"
    )
):
    """Create a new video or edits an existing video"""
    resource_metadata = resource_metadata.resource_metadata
    repaired = False
    info_yaml = Path("data/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / str(chapter) / "info.yaml"
    if not info_yaml.exists():
        return api_error("Chapter does not exist!", status_code=404)
    
    chapter_listing = Path("data/build/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / "chapter_list.lynx"

    if not chapter_listing.exists():
        return api_error("You must perform atleast one data build before doing this")

    chapter_listing_json = common.read_min(chapter_listing)
    
    print(chapter_listing_json)

    chapter_iname = chapter_listing_json[chapter]["iname"]

    resource_type = common.get_resource_by_name(resource_type.name)

    if subtopic_parent:
        sql = "SELECT resource_id AS id, resource_metadata FROM topic_resources WHERE chapter_iname = $1 AND topic_iname = $2 AND subtopic_parent = $3 AND resource_url = $4",
    else:
        sql = "SELECT resource_id AS id, resource_metadata FROM topic_resources WHERE chapter_iname = $1 AND topic_iname = $2 AND subtopic_parent != $3 AND resource_url = $4",

    check = await app.state.db.fetch(
        "SELECT resource_id AS id, resource_metadata FROM topic_resources WHERE chapter_iname = $1 AND topic_iname = $2 AND subtopic_parent = $3 AND resource_url = $4",
        chapter_iname,
        topic_name_internal,
        subtopic_parent,
        resource_url
    )
    print(check)
    if check and len(check) > 1:
        # Corrupt resource alert
        repaired = True
        id = check[0]["id"] # Remove all but first resource
        await app.state.db.execute(
            "DELETE FROM topic_resources WHERE chapter_iname = $1 AND topic_iname = $2 AND subtopic_parent = $3 AND resource_url = $4",
            chapter_iname,
            topic_name_internal,
            subtopic_parent,
            resource_url
        )
        res_meta = orjson.loads(check[0]["resource_metadata"])
    elif check and len(check) == 1:
        # Delete old preserving metadata
        id = check[0]["id"]
        await app.state.db.execute(
            "DELETE FROM topic_resources WHERE chapter_iname = $1 AND topic_iname = $2 AND subtopic_parent = $3 AND resource_url = $4",
            chapter_iname,
            topic_name_internal,
            subtopic_parent,
            resource_url
        )
        res_meta = orjson.loads(check[0]["resource_metadata"])
    else:
        res_meta = {}
        id = str(uuid.uuid4())
    
    if "youtube.com" in resource_url and "?v=" in resource_url:
        video_id = resource_url.split("?v=")[1].split("&")[0] # Extract video id
        yt = Youtube()
        video = yt.get_video(video_id)
        for video_item in video.loop():
            resource_title = resource_title or video_item["snippet"]["title"]
            resource_author = resource_author or video_item["snippet"]["channelTitle"]
            res_meta["yt_video_url"] = video_id
            if not resource_metadata.get("view_count"):
                res_meta["view_count"] = int(video_item["statistics"]["viewCount"])
    
    res_meta |= resource_metadata
    
    if not resource_author:
        return api_error("You must set resource_author")
    elif not resource_title:
        return api_error("You must set resource_title")

    id = await app.state.db.fetchval(
        """INSERT INTO topic_resources (grade, board, subject, chapter_num, chapter_iname, topic_iname, subtopic_parent,
        resource_type, resource_title, resource_description, resource_url, resource_author, resource_metadata, resource_id) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) RETURNING resource_id""",
        int(grade.value),
        board.value.lower(),
        subject.value.lower(),
        chapter,
        chapter_iname,
        topic_name_internal,
        subtopic_parent,
        resource_type.value,
        resource_title,
        resource_description,
        resource_url,
        resource_author,
        orjson.dumps(res_meta).decode("utf-8"),
        id
    )

    return api_success(repaired=repaired, id=str(id), force_200=True)


@router.delete("/topics/resources")
async def delete_resource(
    resource_id: uuid.UUID = Query(
        None,
        description="The resource id to delete from (if you wish to use a resource id to delete a resource"
    ),
    resource_url: str = Query(
        None,
        description="Resource URL to delete based on"
    )
):
    """Deletes a resource based on the resource id"""
    if resource_id:
        await app.state.db.execute("DELETE FROM topic_resources WHERE resource_id = $1", resource_id)
    if resource_url:
        await app.state.db.execute("DELETE FROM topic_resources WHERE resource_url = $1", resource_url)
    return api_success()


@router.post("/data/build")
async def build_data():
    """
    Warning: May hang the server
    
    This will build the data needed for the client to run
    """
    yt = Youtube()
    out = StringIO()
    err = StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        await gen_info.gen_info(app.state.db, yt)

    out.seek(0)
    err.seek(0)

    return HTMLResponse(f"{out.read()}\n\nErrors:\n{err.read()}")

@router.post("/compilestatic")
def compile_static():
    """Warning: May hang the server"""
    out = StringIO()
    err = StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        compilestatic.staticfiles_compile()

    out.seek(0)
    err.seek(0)
    
    return HTMLResponse(f"{out.read()}\n\nErrors:\n{err.read()}")

@router.post("/git")
def git(commitmsg: str = "Some fixes to improve stability", op: GitOP = GitOP.push):
    """Warning: May hang the server"""

    def push(out, err):
        out, err = common.system("git add -v .", out, err)
        out, err = common.system(f"git commit -m '{commitmsg}'", out, err)
        out, err = common.system("git push", out, err)
        return out, err
    
    def pull(out, err):
        out, err = common.system("git pull -v", out, err)
        return out, err    

    if op == GitOP.push:
        f = push
    else:
        f = pull

    out, err = "", ""

    out, err = f(out, err)
    os.chdir("data")
    out, err = f(out, err)
    
    return HTMLResponse(f"{out}\n{err}")

@router.delete("/chapters")
async def delete_chapter(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,  
):
    chapter_dir = Path("data/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / str(chapter)
    if not chapter_dir.exists():
        return api_error("Chapter does not exist!", status_code=404)

    chapter_listing = Path("data/build/grades") / str(grade.value) / board.value.lower() / subject.value.lower() / "chapter_list.lynx"

    if not chapter_listing.exists():
        return api_error("You must perform atleast one data build before doing this")

    chapter_listing_json = common.read_min(chapter_listing)
    
    print(chapter_listing_json)

    chapter_iname = chapter_listing_json[chapter]["iname"]

    shutil.rmtree(str(chapter_dir))
    await app.state.db.execute(
        "DELETE FROM topic_resources WHERE chapter_iname = $1",
        chapter_iname
    )

@router.post("/reboot")
def reboot():
    """**NOTE** This will not return anything"""
    common.restart()


app.include_router(router)

simplify_operation_ids(app)