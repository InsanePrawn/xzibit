#!/usr/bin/env python
import os
from datetime import datetime
import argparse

COMMON_DICT_PREFIX='|COMMON|'
VARIANT_DICT_PREFIX='|VARIANT|'

debug = True
config_folder = ''
base_path = os.path.dirname(os.path.realpath(__file__))
variant_suffixes = ['cfg-public', 'cfg-private']
common_suffix = 'cfg-common'


def log(s, is_debug = False):
    global debug
    msg = str(s)
    if is_debug:
        if debug:
            msg = 'DEBUG: ' + msg
        else:
            return
    print(str(datetime.now().strftime("%H:%M:%S")) + ": " + msg)


def join_paths(base, suffix):
    '''
    calculates an absolute path from a [possibly relative] input and base
    example: cleanly_join_paths('/bin/test/help','/mnt/abs/../abs/123')
    returns /mnt/abs/123
    NO CHECKS FOR EXISTENCE ARE PERFORMED!
    :param base: the path to start from
    :param suffix: the path target, can be relative or absolute
    :return: a redundancy-free, absolute path.
    '''
    return os.path.abspath(os.path.relpath(suffix, base))


def files_in_folder(prefix, base_dir, path_currently='', depth=0, max_depth=250):
    results = {}
    with os.scandir(base_dir + '/' + path_currently) as dir:
        log('working on ' + path_currently, True)
        for entry in dir:
            if not entry.name.startswith('.'):
                entry_path = os.path.join(path_currently,entry.name)
                if entry.is_dir():
                    if depth < max_depth:
                        results.update(files_in_folder(prefix, base_dir, path_currently=entry_path, depth=depth+1))
                    else:
                        log(entry_path + ' ignored due to max recursion depth, sorry :/')
                elif entry.name.endswith('yaml'):
                    log('file found: ' + entry_path, True)
                    complete_path = os.path.join(base_dir,entry_path)
                    results[entry_path] = complete_path
                    results[prefix+entry_path] = complete_path
    return results


def load_lines(file):
    try:
        lines = open(file,'r').readlines()
        return lines
    except Exception as err:
        log("Couldn't output file %s: %s" % (file, err))
        return None


def replace_inline(line, files):
    result = ''
    sub_lines = line.split('\n')
    if len(sub_lines) > 1:
        return '\n'.join([replace_inline(sub_line, files) for sub_line in sub_lines])
    while '{{{' in line and '}}}' in line:
        placeholder_end = line.find('}}}')
        placeholder_start = line.rfind('{{{',0,placeholder_end)
        # add stuff before the placeholder to the result string
        result += line[:placeholder_start]
        file_name = line[placeholder_start+3:placeholder_end]
        log('Replacing stuff!\nline: %s\nstart: %i\nend: %i\nbefore placeholder: %s\nplaceholder: %s\nfile_name: %s\nafter placeholder: %s\n'
            % (line, placeholder_start, placeholder_end, line[:placeholder_start], line[placeholder_start:placeholder_end+3], file_name, line[placeholder_end+3:]), True)
        # add placeholder-replacement to result
        file = build_config(file_name, files)
        if file is not None:
            result += file
        else:
            result = line[placeholder_start:placeholder_end+3]
        # shift placeholder and stuff before it away
        line = line[placeholder_end+3:]
    # line has been cleansed of includes
    result += line
    return result


def build_config(file_name, files):
    result = ''
    file_lines = load_lines(files[file_name])
    if file_lines is None:
        return None
    for file_line in file_lines:
        result += replace_inline(file_line, files)

    return result

parser = argparse.ArgumentParser()
# TODO parse arguments

common_path = join_paths(base_path, common_suffix)
variant_paths = {variant: join_paths(base_path, variant) for variant in variant_suffixes}

# create a dictionary of simple file names and their absolute paths. in general, variant files shadow common ones
# both variant and common files additionally have a separate dictionary entry as '|VARIANT|filename.myaml'
# we scan the common files once and then use copies of this data as the foundation for each variant.
# the order makes sure that the shadowing works!!!
common_files = files_in_folder(COMMON_DICT_PREFIX, os.path.join(common_path,config_folder))
variant_files = {}
variant_outputs = {}
for variant, variant_path in variant_paths.items():
    output = []
    log('working on ' + variant, True)
    files = common_files.copy()
    files.update(files_in_folder(VARIANT_DICT_PREFIX, os.path.join(variant_path,config_folder)))
    variant_files[variant] = files
    log(files, True)
    # we need some sort of entry point
    if 'configuration.myaml' not in files:
        log("configuration.myaml not found, skipping %s :/" % variant)
        continue
    output = [build_config('configuration.myaml',files)]
    log('config finished?!\n--------------\n'+'\m'.join(output),True)
    variant_outputs[variant] = output