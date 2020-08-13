"""
A simple and stupid module for converting JSON into Python dataclasses
with annotated attributes.
"""
import json
import sys
from pathlib import Path

PREFACE = """\
import attr
import cattr

"""
POSTFACE = """
    @classmethod
    def instantiate(cls, obj):
        return cattr.structure(obj, cls)
"""
RETURN_LINES = ...
decorator = "@attr.dataclass"
annotation_types = set()


def normalize_type_name(name):
    return name.title().replace("_", "").rstrip("s")


def classify_dict(name, d):
    object_keys = []
    lines = [decorator] if decorator else []
    lines.append(f"class {name}:")
    for key, val in sorted(d.items()):
        if isinstance(val, (dict, list)):
            _type = normalize_type_name(key)
            is_obj_list = isinstance(val, list)
            if val:
                if is_obj_list and not isinstance(val[0], dict):
                    # Define as a list of built-in typed values
                    is_obj_list = False
                    _type = f"List[{type(val[0]).__name__}]"
                    annotation_types.add("List")
                else:
                    if is_obj_list:
                        # Ensure all keys are represented
                        aggregated_dict = {}
                        for val_dict in val:
                            aggregated_dict.update(val_dict)
                    else:
                        aggregated_dict = val
                    object_keys.append((_type, aggregated_dict))
            else:
                _type = "Any"
            if is_obj_list:
                _type = f"List[{_type}]"
                annotation_types.add("List")
        elif val is None:
            _type = "Optional[Any]"
            annotation_types.update(["Optional", "Any"])
        else:
            _type = type(val).__name__
        lines.append(f"    {key}: {_type}")
    for ok, obj in reversed(object_keys):
        lines[0:0] = classify_dict(ok, obj) + ["\n"]
    return lines


def generate_dataclasses(
    name="Root", infile=None, outfile=None, preface=PREFACE, postface=POSTFACE
):
    if infile is None:
        data = json.load(sys.stdin)
    else:
        infile_path = Path(infile).expanduser()
        if not infile_path.exists():
            sys.exit(f"Infile {infile} not found")
        with infile_path.open() as rf:
            data = json.load(rf)
    while isinstance(data, list):
        data = data[0]
    python_lines = preface.split("\n") if preface else []
    python_lines.extend(classify_dict(name, data))
    if preface and annotation_types:
        python_lines[0:0] = [
            f"from typing import {', '.join(sorted(annotation_types))}",
            "",
        ]
    if postface:
        python_lines.extend(postface.split("\n"))
    if outfile is RETURN_LINES:
        return python_lines
    elif outfile is None:
        sys.stdout.write("\n".join(python_lines))
    else:
        with Path(outfile).expanduser().open("w") as wf:
            wf.write("\n".join(python_lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d", "--decorator", help=f"class decorator (default: {decorator!r})"
    )
    parser.add_argument("name", nargs="?", help="top-level class name", default="Root")
    parser.add_argument(
        "infile", nargs="?", help="infile to read JSON from (default: stdin)"
    )
    parser.add_argument(
        "outfile", nargs="?", help="outfile to write Python to (default: stdout)"
    )
    args = parser.parse_args()
    if args.decorator is not None:
        if len(args.decorator) and not args.decorator.startswith("@"):
            decorator = f"@{args.decorator}"
        else:
            decorator = args.decorator
    generate_dataclasses(args.name, args.infile, args.outfile)
