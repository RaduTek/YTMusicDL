import os
import json

out_dir = "tests/results"


def set_out_dir(dir: str):
    global out_dir
    try:
        os.mkdir(dir)
        out_dir = dir
    except OSError as error:
        print(error)


def get_json(data):
    return json.dumps(data, indent=4)


def print_json(data):
    print(get_json(data))


def write_json(data, file: str):
    file = os.path.join(out_dir, file)
    with open(file, "w") as f:
        f.write(get_json(data))
