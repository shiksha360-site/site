from fastapi import FastAPI, Request, APIRouter, Query
from fastapi_restful.openapi import simplify_operation_ids
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError, ValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

from sdk.fetcher.yt.api import Youtube
from .models import Chapter, Grade, Board, Subject, GitOP
import asyncpg
from lynxfall.utils.fastapi import api_success, api_error
from sdk.create_new import create_new
from .cfg import API_VERSION
from .error import WebError
from .request_handler import KalanRequestHandler
from ruamel.yaml import YAML
from sdk import common, gen_info, compilestatic
from pathlib import Path
import os
import contextlib
from io import StringIO
from typing import List

key_data = common.load_yaml("data/core/internal_api.yaml")

app = FastAPI(
    docs_url="/internal",
    description=key_data["description"]
)

router = APIRouter(
    prefix=f"/api/v{API_VERSION}/internal",
    tags=["Internal"]
)

@app.on_event("startup")
async def on_startup():
    app.state.db = await asyncpg.create_pool(database="kalam")
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
    exc_handler=WebError.error_handler
)


@router.get("/ping")
def ping():
    return api_success()

@router.post("/chapters")
def new_chapter(
    grade: Grade, 
    board: Board, 
    subject: Subject, 
    name: str = Query(..., description="Name of the chapter")
):
    """
    Creates a new chapter in the syllabus
    """
    rc, ctx = create_new(grade=grade.value, board=board.value, subject=subject.value, name=name)
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
    info_yaml = Path("data/grades") / str(grade.value) / board.value / subject.value / str(chapter) / "info.yaml"
    if not info_yaml.exists():
        return api_error("Chapter does not exist!", status_code=404)
    data = common.load_yaml(info_yaml, ruamel_type="rt")
    if name:
        data["name"] = name
    if study_time:
        data["study-time"] = study_time
    common.dump_yaml(info_yaml, data)

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
        data = common.load_yaml(path)

        data["subject"] = _subject
        data["grade"] = _grade
        data["board"] = _board
        try:
            data["study_time"] = data["study-time"]
            del data["study-time"]
        except Exception:
            pass

        if parse_full and app.state.is_internal:
            res = common.load_yaml(str(path).replace("info.yaml", "extres.yaml"))
            # Parse all the topics
            for topic in data["topics"]:
                data["topics"], res = gen_info.parse_topic(None, data, res, None, None, topic, pretend=True)
            data["topics"]["res"] = res

        chapters.append(data)

    return {"chapters": chapters}

@router.put("/topics")
def add_or_edit_topic(
    grade: Grade, 
    board: Board, 
    subject: Subject,
    chapter: int,
    topic_name_friendly: str = Query(
        ..., 
        description="The user-visible/friendly name for the topic. Use `$name` if you wish for the topic name to be the name of the chapter itself",
    ),
    topic_name_internal: str = Query(
        ...,
        description="Internal topic name. This must not have spaces, numbers or any special character other than hyphens and is not user-visible",
        minlength=2,
        regex="^(?![0-9.-])(?!.*[0-9.-]$)(?!.*\d-)(?!.*-\d)[a-zA-Z0-9-]+$" # To reject all special characters other than numbers and hyphens
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
    info_yaml = Path("data/grades") / str(grade.value) / board.value / subject.value / str(chapter) / "info.yaml"
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
        data["topics"][topic_name_internal] = ext
        data["topics"][topic_name_internal]["subtopics"] = bak
    else:
        if not data["topics"].get(subtopic_parent):
            return api_error("Parent topic does not exist!")
        if not data["topics"][subtopic_parent]["subtopics"]:
            data["topics"][subtopic_parent]["subtopics"] = {}
        data["topics"][subtopic_parent]["subtopics"][topic_name_internal] = ext
        data["topics"][subtopic_parent]["subtopics"][topic_name_internal]
    
    common.dump_yaml(info_yaml, data)
    return api_success(count=len(data["topics"].values()), mc_analyze=len(data["topics"].get("main", {}).get("subtopics", {}).values()), force_200=True)

@router.post("/topics/videos")
def new_video():
    """Use /video_json_creator to create the Video JSON"""
    ...

@router.post("/data/build")
def build_data(selenium_scrape: bool):
    """
    Warning: May hang the server
    e
    This will build the data needed for the client to run
    """
    yt = Youtube()
    os.chdir("data")
    out = StringIO()
    err = StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        gen_info.gen_info(yt, selenium_scrape=selenium_scrape)

    out.seek(0)
    err.seek(0)

    os.chdir("..")

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
    os.chdir("..")
    
    return HTMLResponse(f"{out}\n{err}")

app.include_router(router)

simplify_operation_ids(app)