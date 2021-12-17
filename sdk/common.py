from typing import List
from ruamel.yaml import YAML, comments
import json
import sys
import os
import subprocess
import random
import threading
from aenum import Enum, IntEnum
import msgpack
import pathlib

debug_mode = os.environ.get("DEBUG", "0").lower() in ["1", "true"]

class Resource(Enum):
    _init_ = 'value __doc__'
    whiteboard = 0, "Lectures" # Magnet Brain etc.
    animated = 1, "Animated Videos" # Ex. Monocha. Animated Videos
    lab = 2, "Lab Videos" # Lab Video
    interactive = 3, "Interactive Experiments" # Truly interative experiments like PHeT
    class_note = 4, "Class notes" # Class Notes
    revision_note = 5, "Revision Notes" # Revision Notes
    mock_test = 6, "Take A Test" # Take a test
    real_world = 7, "Exploration" # Discovery (How's It Made/Mythbuster)
    problem_solving = 8, "Problem Solving" # Problem Solving

def create_resource_type_list() -> dict:
    resource_types = {}
    for r in list(Resource):
        resource_types[r.value] = {"doc": r.__doc__, "enum_name": r.name}
    return resource_types

def get_resource_by_name(name: str) -> Resource:
    """Given the resource name, return the enum itself"""
    return getattr(Resource, name)

def get_subject_name(grade, subject):
    try:
        subject = subject.value.lower()
    except Exception:
        subject = subject.lower()
    subjects = load_yaml("data/core/subjects.yaml")
    if grade < 9:
        subject = subjects[subject].get("alias", subject)
    return subject

# For Swagger
ResourceList = Enum('ResourceList', {res.name: res.name.replace("_", " ").title() for res in list(Resource)})

class YamlLoadCache():
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache = {}

    def _cache_key(self, filename: str, ruamel_type: str = "safe"):
        return f"{filename}-{ruamel_type}"

    def get(self, filename: str, ruamel_type: str = "safe"):
        return self.cache.get(self._cache_key(filename, ruamel_type))
    
    def set(self, filename: str, data: object, ruamel_type: str = "safe"):
        self.cache[self._cache_key(filename, ruamel_type)] = data

cache = YamlLoadCache()

def pformat(d) -> str:
    return json.dumps(d, indent=4)

def load_yaml(filename: str, version: float = 1.1, ruamel_type: str = "safe") -> dict:
    """NOTE: use_pyyaml has been removed"""
    filename = str(filename)
    cached = cache.get(filename, ruamel_type)
    if cached:
        return cached
    with open(filename) as file:
        # Set YAML Version
        contents = f"%YAML {version}\n---\n" + file.read()
        yaml = YAML(typ=ruamel_type)
        data = yaml.load(contents)
        if debug_mode:
            print(f"Opened YAML ({filename}): ", pformat(data))
        cache.set(filename, data, ruamel_type)
        return data

def dump_yaml(filename: str, data, ruamel_type: str = "safe"):
    if isinstance(data, comments.CommentedMap):
        ruamel_type = "rt"
    
    with open(str(filename), "w") as file:
        yaml = YAML(typ=ruamel_type)
        yaml.dump(data, file)
    
    threading.Thread(target=cache.clear).start()

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

def write_min(d: dict, fp, no_debug: bool = False):
    fn = pathlib.Path(fp.name)

    # Lynx is the file for use in production
    with fn.with_suffix(".lynx").open("wb") as fpb:
        msgpack.pack(d, fpb)

    if not no_debug:
        # Snowfall is the debug file
        with fn.with_suffix(".snowfall").open("w") as fpb:
            json.dump(d, fpb, indent=4)


def read_min(filename: str):
    """Reads data accounting for any format changes"""
    with open(str(filename).replace(".min.json", ".lynx"), "rb") as fpb:
        return msgpack.unpack(fpb, strict_map_key=False)

def remove_ws(s: str) -> str:
    return s.replace("\n", "").replace("  ", "").replace("\t", " ")

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

def restart():
    os.execv(sys.executable, ['python3.10'] + [sys.argv[0]])