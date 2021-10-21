from fastapi import FastAPI, Request, APIRouter, Query
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError, ValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

from sdk.fetcher.yt.api import Youtube
from .models import Chapter, Grade, Board, Subject
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
import subprocess

app = FastAPI(docs_url="/internal")

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
    rc, ctx = create_new(grade=grade, board=board, subject=subject, name=name)
    if rc:
        return api_error(rc)
    return api_success(ctx=ctx)

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

@router.post("/data/build")
def build_data(selenium_scrape: bool):
    """
    Warning: May hang the server
    
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

@router.post("/push")
def push_src(commitmsg: str = "Some fixes to improve stability"):
    """Warning: May hang the server"""

    def system(call, out, err):
        with subprocess.Popen(call, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ) as proc:
            cmd_out, cmd_err = proc.communicate()
            if not cmd_err:
                cmd_err = b""
            if not cmd_out:
                cmd_out = b""
            return out+cmd_out.decode("utf-8"), err+cmd_err.decode("utf-8")

    def push(out, err):
        out, err = system("git add -v .", out, err)
        out, err = system(f"git commit -m '{commitmsg}'", out, err)
        out, err = system("git push", out, err)
        return out, err

    out, err = "", ""

    out, err = push(out, err)
    os.chdir("data")
    out, err = push(out, err)
    
    return HTMLResponse(f"{out}\n\nErrors:\n{err}")   


app.include_router(router)