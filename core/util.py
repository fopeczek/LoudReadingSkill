from pathlib import Path
import json


def create_and_load_file(file_name: Path, default_content):
    try:
        with open(file_name, "r") as fr:
            try:
                return json.load(fr)
            except json.JSONDecodeError:
                with open(file_name, "w") as fw:
                    jsonobj = json.dumps(default_content, indent=4)
                    fw.write(jsonobj)
    except FileNotFoundError:
        with open(file_name, "w") as fw:
            jsonobj = json.dumps(default_content, indent=4)
            fw.write(jsonobj)
    return default_content


def just_letters(s: str) -> str:
    return " ".join(s.lower().translate(str.maketrans("", "", "!?.,;:-")).split())
