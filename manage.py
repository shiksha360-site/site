import sys
sys.pycache_prefix = "data/pycache"

from subprocess import Popen, DEVNULL
import os
import re
from pathlib import Path
from getpass import getpass
import shutil
from typing import Any, Dict
import click
from sdk import create_new, gen_info, common

@click.group()
def app():
    """Main cli entrypoint"""
    ...

@click.group()
def data():
    """Data compiling and building"""
    ...

@app.command("compilestatic")
def staticfiles_compile():
    """Compiles all labelled static files"""
    for src_file in Path("assets/src").rglob("*.js"):
        common.fix_versions(str(src_file))
        out_file = str(src_file).replace(".js", ".min.js").replace("src/", "prod/").replace("js/", "")
        click.echo(f"{src_file} -> {out_file}")
        cmd = [
            "google-closure-compiler", 
            "--js", str(src_file), 
            "--js_output_file", out_file
        ]
            
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
        
    for src_file in Path("assets/src").rglob("*.scss"):
        out_file = str(src_file).replace(".scss", ".min.css").replace("src/", "prod/").replace("css/", "")
        click.echo(f"{src_file} -> {out_file}")
        cmd = [
            "sass",
            "--style=compressed",
            str(src_file),
            out_file
        ]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

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
    
@data.command("add")
def data_new():
    """Creates a subject and/or a chapter in a subject"""
    os.chdir("data")
    create_new.create_new()

@data.command("build")
def data_build():
    """This compile all the chapter yaml files in data into *.min.json's for the site"""
    os.chdir("data")
    gen_info.gen_info()

@app.command("push")
@click.option('--commitmsg', default="Commit", help='Commit message')
def git_push_all(commitmsg):
    """Push in all submodules"""
    def push():
        os.system("git add -v .")
        os.system(f"git commit -m {commitmsg}")
        os.system("git push")

    push()
    os.chdir("data")
    push()

app.add_command(data)
if __name__ == "__main__":
    app()
