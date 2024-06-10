#!/usr/bin/python3

# Copyright (C) 2024 Lev Veyde <lev@redhat.com> <lveyde@gmail.com>

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import argparse
import json
import os
import pathlib
import sys

__version__ = "1.1.0"

AUTO_ANNOTATED_SOURCE = "-- Auto-annotated source:"
FILE_FUNCTION_HEADER = "Ir      file:function"


def process_report(report_file_name):
    records = dict()
    files = dict()
    source_files_index = []
    source_files_annotations = []
    print(f"Processing {report_file_name}...")
    with open(report_file_name) as file:
        counter = 0
        file_counter = 0
        in_header = False
        in_annotation_section = False
        in_index_section = False
        for line in file:
            line = line.rstrip()
            if line == "-" * 80:
                in_header = not in_header
                if in_header:
                    counter = counter + 1
            else:
                if in_header:
                    if line.startswith(FILE_FUNCTION_HEADER):
                        in_index_section = True
                    elif line.startswith(AUTO_ANNOTATED_SOURCE):
                        in_annotation_section = True
                        in_index_section = False
                        file_counter = file_counter + 1
                        source_filename = os.path.abspath(
                            line[len(AUTO_ANNOTATED_SOURCE) + 1 :]
                        )
                        source_files_annotations.append(source_filename)
                        if not records:
                            print("Wrong report format!")
                            print("Generate the report with:")
                            print(
                                "\tcallgrind_annotate --auto=yes --show-percs=no --context=0 callgrind.out.* > callgrind.annotated"
                            )
                            sys.exit(1)
                        for shared_object_path in records:
                            if source_filename in records[shared_object_path]:
                                break
                        shared_object_basename = os.path.basename(shared_object_path)
                        if shared_object_basename not in files.keys():
                            files[shared_object_basename] = open(
                                "report-" + shared_object_basename, "w"
                            )
                        files[shared_object_basename].write("-" * 80 + "\n")
                        files[shared_object_basename].write(
                            AUTO_ANNOTATED_SOURCE + " " + source_filename + "\n"
                        )
                        files[shared_object_basename].write("-" * 80 + "\n")
                    else:
                        in_annotation_section = False
                        in_index_section = False
                else:
                    if in_index_section and len(line.lstrip()) > 0:
                        record = line.lstrip().split()
                        if len(record) > 3:
                            record[1] = record[1] + " " + record[2]
                            record[2] = record[3]
                        file_func = os.path.abspath(record[1]).split(":")
                        source_files_index.append(file_func[0])
                        if len(record) > 2:
                            shared_object_name = record[2][1:-1]
                        else:
                            shared_object_name = "unknown"
                        if not shared_object_name in records.keys():
                            records[shared_object_name] = {}
                        if not file_func[0] in records[shared_object_name].keys():
                            records[shared_object_name][file_func[0]] = []
                        if len(file_func) > 1:
                            records[shared_object_name][file_func[0]].append(
                                file_func[1]
                            )
                        else:
                            records[shared_object_name][file_func[0]].append("")
                    elif in_annotation_section:
                        if len(line.lstrip()) > 0:
                            files[shared_object_basename].write(line.lstrip() + "\n")

    for file in files:
        files[file].close()
    func_list = []
    func_count = {}
    functions = {}
    for dso in records:
        for file in records[dso]:
            for func in records[dso][file]:
                func_list.append(func)
                if func in functions:
                    if not dso in functions[func].keys():
                        functions[func][dso] = [file]
                    else:
                        functions[func][dso].append(file)
                else:
                    functions[func] = {dso: [file]}
                if not dso in func_count:
                    func_count[dso] = 0
                func_count[dso] += 1
    report = {}
    report["DSOs"] = records
    report["functions"] = functions
    report["Statistics"] = {
        "section count": counter,
        "index file count": len(source_files_index),
        "index file count (unique)": len(set(source_files_index)),
        "annotations file count": len(source_files_annotations),
        "annotations file count (unique)": len(set(source_files_annotations)),
        "total function count": len(func_list),
        "total function count (unique)": len(set(functions)),
        "file count": {},
        "function count": {},
    }
    for shared_object_name in records:
        report["Statistics"]["file count"][shared_object_name] = len(
            records[shared_object_name]
        )
        report["Statistics"]["function count"][shared_object_name] = func_count[
            shared_object_name
        ]

    with open("report.json", "w") as reportJson:
        reportJson.write(json.dumps(report, indent=4, sort_keys=True))

    if sorted(set(source_files_index)) != sorted(set(source_files_annotations)):
        print("Error: index doesn't match annotation sections:")
        print(
            f"Indexed files ({len(set(source_files_index))}): {sorted(set(source_files_index))}"
        )
        print(
            f"Annotated files ({len(set(source_files_annotations))}): {sorted(set(source_files_annotations))}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="process_callgrind_report.py",
        description="callgrind report parser",
        epilog="process annotated callgrind reports",
    )
    parser.add_argument(
        "filename", help="annotated callgrind report filename", type=pathlib.Path
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )
    args = parser.parse_args()
    if len(sys.argv) < 2:
        print("Usage: process_callgrind_report.py <report_file_name>")
        sys.exit(0)
    process_report(args.filename)
