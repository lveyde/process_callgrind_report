#!/usr/bin/python3

import argparse
import json
import os
import pathlib
import sys

AUTO_ANNOTATED_SOURCE = '-- Auto-annotated source:'
FILE_FUNCTION_HEADER = 'Ir      file:function'

def process_report(report_file_name):
    records = dict()
    files = dict()
    source_files_index = []
    source_files_annotations = []
    print(report_file_name)
    with open(report_file_name) as file:
        counter = 0
        file_counter = 0
        in_header = False
        in_annotation_section = False
        in_index_section = False
        for line in file:
            line = line.rstrip()
            if line == '-' * 80:
                in_header = not in_header
                if in_header:
                    counter = counter + 1
                    # print(f'section header begin {counter}')
                else:
                    # print(f'section header end {counter}')
                    pass
            else:
                if in_header:
                    if line.startswith(FILE_FUNCTION_HEADER):
                        in_index_section = True
                        print('file:function index')
                    elif line.startswith(AUTO_ANNOTATED_SOURCE):
                        in_annotation_section = True
                        in_index_section = False
                        file_counter = file_counter + 1
                        source_filename = os.path.abspath(line[len(AUTO_ANNOTATED_SOURCE)+1:])
                        source_files_annotations.append(source_filename)
                        if not records:
                            print('Wrong report format!')
                            print('Generate the report with:')
                            print('\tcallgrind_annotate --auto=yes --show-percs=no --context=0 callgrind.out.* > callgrind.annotated')
                            sys.exit(1)
                        for shared_object_path in records:
                            if source_filename in records[shared_object_path]:
                                break
                        shared_object_basename = os.path.basename(shared_object_path)
                        if shared_object_basename not in files.keys():
                            files[shared_object_basename] = open('report-' + shared_object_basename, 'w')
                        files[shared_object_basename].write('-' * 80 + '\n')
                        files[shared_object_basename].write(AUTO_ANNOTATED_SOURCE + ' ' + source_filename + '\n')
                        files[shared_object_basename].write('-' * 80 + '\n')
                        # if summarize_by_shared_object:
                        # annotation_filename = '@'.join()
                        # if annotation_file:
                        #     annotation_file.close()
                        # annotation_file = open("shared_object_specific_dir/")
                        # print(f'file {file_counter}: {os.path.basename(shared_object_name)}:{source_filename}')
                    else:
                        in_annotation_section = False
                        in_index_section = False
                else:
                    if in_index_section and len(line.lstrip()) > 0:
                        record = line.lstrip().split()
                        if len(record) > 3:
                            record[1] = record[1] + ' ' + record[2]
                            record[2] = record[3]
                        file_func = os.path.abspath(record[1]).split(':')
                        source_files_index.append(file_func[0])
                        if len(record) > 2:
                            shared_object_name = record[2][1:-1]
                        else:
                            shared_object_name = 'unknown'
                        if not shared_object_name in records.keys():
                            records[shared_object_name] = {}
                        if not file_func[0] in records[shared_object_name].keys():
                            records[shared_object_name][file_func[0]] = []
                        if len(file_func) > 1:
                            records[shared_object_name][file_func[0]].append(file_func[1])
                        else:
                            records[shared_object_name][file_func[0]].append("")
                    elif in_annotation_section:
                        if len(line.lstrip()) > 0:
                            files[shared_object_basename].write(line.lstrip() + '\n')
                        # print(f'{source_filename}: {line.lstrip()}')

    for file in files:
        files[file].close()
    print(json.dumps(records, indent=4, sort_keys=True))
    for shared_object_name in records:
        print(f'{shared_object_name}: {len(records[shared_object_name])} source code files.')
    if sorted(set(source_files_index)) != sorted(set(source_files_annotations)):
        print('Error: index doesn\'t match annotation sections:')
        print(f'Indexed files ({len(set(source_files_index))}): {sorted(set(source_files_index))}')
        print(f'Annotated files ({len(set(source_files_annotations))}): {sorted(set(source_files_annotations))}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='process_callgrind_report.py',
        description='callgrind report parser',
        epilog='process annotated callgrind reports'
    )
    parser.add_argument("filename", help="annotated callgrind report filename", type=pathlib.Path)
    args = parser.parse_args()
    if len(sys.argv) < 2:
        print("Usage: process_callgrind_report.py <report_file_name>")
        sys.exit(0)
    process_report(args.filename)