import sys
from subprocess import Popen, DEVNULL
import os
import re
from pathlib import Path
from getpass import getpass
import shutil
from typing import Any, Dict
from sdk import common
from jinja2 import Environment, FileSystemLoader, select_autoescape
import uuid

def staticfiles_compile():
    """Compiles all labelled static files"""
    env = Environment(
        loader=FileSystemLoader("assets/src/templates"),
        autoescape=select_autoescape(),
    )
    env.globals = {"uuid_gen": lambda: str(uuid.uuid4())}

    for src_file in Path("assets/src").rglob("*.js"):
        common.fix_versions(str(src_file))
        out_file = str(src_file).replace(".js", ".min.js").replace("src/", "prod/").replace("js/", "")
        print(f"{src_file} -> {out_file}")
        cmd = [
            "google-closure-compiler", 
            "--js", str(src_file), 
            "--js_output_file", out_file
        ]
            
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
        
    for src_file in Path("assets/src").rglob("*.scss"):
        out_file = str(src_file).replace(".scss", ".min.css").replace("src/", "prod/").replace("css/", "")
        print(f"{src_file} -> {out_file}")
        cmd = [
            "sass",
            "--style=compressed",
            str(src_file),
            out_file
        ]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
        
    for src_file in Path("assets/src").rglob("*.jinja2"):
        if str(src_file).split("/")[-1].startswith("_"):
            continue
        out_file = str(src_file).replace(".jinja2", ".html").replace("src/", "").replace("templates/", "")
        print(f"{src_file} -> {out_file}")
        template = env.get_template(str(src_file).split("/")[-1])
        with open(out_file, "w") as output:
            output.write(template.render())

    for img in Path("assets/src/img").rglob("*"):
        ext = str(img).split(".")[-1]
        out = str(img).replace("src/img/", "prod/").replace(f".{ext}", ".webp")
        print(f"{img} -> {out}")
            
        if ext == "webp":
            shutil.copy2(str(img), out)
        else:
            cmd = [
                "cwebp",
                "-quiet",
                "-q", "75",
                str(img),
                "-o",
                out
            ]

            with Popen(cmd, env=os.environ) as proc:
                proc.wait()
    
    common.fix_versions("assets/index.html")
