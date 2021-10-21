from ruamel.yaml import YAML
from yaml import load, Loader
import json
import sys
import os
import subprocess
import random

debug_mode = os.environ.get("DEBUG", "0").lower() in ["1", "true"]

def load_yaml(filename: str, version: float = 1.1, use_pyyaml: bool = False) -> dict:
    with open(str(filename)) as file:
        # Set YAML Version
        contents = f"%YAML {version}\n---\n" + file.read()
        if not use_pyyaml:
            yaml = YAML(typ="safe")
            data = yaml.load(contents)
        else:
            data = load(contents, Loader=Loader)
        if debug_mode:
            print(f"Opened YAML ({filename}): ", pformat(data))
        return data

def input_int(prompt: str, *, tries: int = 0, return_none: bool = False) -> int:
    try:
        return int(input(prompt))
    except ValueError:
        if tries >= 2:
            print("Too many tries!")
            if return_none:
                return None
            else:
                sys.exit(-1)
        print("Invalid input")
        return input_int(prompt, tries=tries+1)


def pformat(d) -> str:
    return json.dumps(d, indent=4)

def write_min_json(d: dict, fp):
    return fp.write(json.dumps(d, separators=(',', ':')))

def remove_ws(s: str) -> str:
    return s.replace("\n", "").replace("  ", "")

def fix_versions(s: str):
    new_version = random.randint(1, 9)
    with open(s) as old_index:
        index = old_index.read()
        
    with open(s, "w") as old_index:
        old_index.write(index.replace("?v=", f"?v={new_version}"))

def system(call, out, err):
    with subprocess.Popen(call, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ) as proc:
        cmd_out, cmd_err = proc.communicate()
        if not cmd_err:
            cmd_err = b""
        if not cmd_out:
            cmd_out = b""
        return out+cmd_out.decode("utf-8"), err+cmd_err.decode("utf-8")
