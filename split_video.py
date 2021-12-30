# split video by chapter and split by scene
# python split_video.py -f path/of/video.mp4 -c X -s
# split video by chapter only
# python split_video.py -f path/of/video.mp4 -c X

# for detecting scenes from video
# scenedetect -i video.mp4 detect-content split-video

import os
import re
import pprint
from os.path import basename
from subprocess import *
from optparse import OptionParser


def parse_chapters(filename):
    global m1
    chapters = []
    command = ["ffmpeg", '-i', filename]
    title = None
    chapter_match = None
    try:
        output = check_output(command, stderr=STDOUT, universal_newlines=True)
    except CalledProcessError as e:
        output = e.output

    num = 1
    for line in iter(output.splitlines()):
        x = re.match(r".*title.*: (.*)", line)
        print("x:")
        pprint.pprint(x)

        print("title:")
        pprint.pprint(title)

        if x is None:
            m1 = re.match(r".*Chapter #(\d+:\d+): start (\d+\.\d+), end (\d+\.\d+).*", line)
            title = None
        else:
            title = x.group(1)

        if m1 is not None:
            chapter_match = m1

        print("chapter_match:")
        pprint.pprint(chapter_match)

        if title is not None and chapter_match is not None:
            m = chapter_match
            pprint.pprint(title)
        else:
            m = None

        if m is not None:
            chapters.append({"name": repr(num) + " - " + title, "start": m.group(2), "end": m.group(3)})
            num += 1

    return chapters


def get_chapters(options):
    if not options.infile:
        parser.error('Video filename required')

    chapters = parse_chapters(options.infile)
    path, file = os.path.split(options.infile)
    newdir, ext = os.path.splitext(basename(options.infile))

    try:
        os.mkdir(path + "/" + newdir)
    except FileExistsError as err:
        print(err)

    for chap in chapters:
        chap['target'] = True
        chap['name'] = chap['name'].replace('/', ':').replace("'", "\'")
        print("start:" + chap['start'])
        chap['outfile'] = path + "/" + newdir + "/" + re.sub("[^-a-zA-Z0-9_.():' ]+", '', chap['name']) + ext
        chap['origfile'] = options.infile

        if options.chapter is not None:
            # it works if is "2 - CHAPTER_NAME" or "CHAPTER_NAME - 2"
            if ''.join(x for x in chap['name'] if x.isdigit()) == options.chapter:
                chap['target'] = True
                print("found target chapter", options.chapter)
                chap['outfile'] = path + "/" + newdir + "/" + options.chapter + ext
            else:
                chap['target'] = False
    return chapters


def convert_chapters(chapters):
    for chap in chapters:
        if chap['target']:
            print("start:" + chap['start'])
            print(chap)
            command = [
                "ffmpeg", '-i', chap['origfile'],
                '-vcodec', 'copy',
                '-acodec', 'copy',
                '-ss', chap['start'],
                '-to', chap['end'],
                chap['outfile']]
            print(command)
            try:
                check_output(command, stderr=STDOUT, universal_newlines=True)
            except CalledProcessError as e:
                raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))


def split_scenes(chapter):
    try:
        # split scenes with scenedetect
        cmd = ["scenedetect", "-i",
               chapter + ".mp4",
               "detect-content",
               "split-video"]
        print(cmd)
        os.chdir("video")

        ps = Popen(cmd, stdout=PIPE, universal_newlines=True)
        while True:
            res = ps.stdout.readline()
            if ps.poll() is not None:
                break
            if res:
                print(res.strip())

        # create list file for concat with ffmpeg if necessary
        for r in os.scandir():
            if r.is_file():
                with open("list.txt", "a+") as file:
                    file.write("file '" + r.path.replace(".\\", "") + "'\n")

    except CalledProcessError as e:
        raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))


if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [options] filename", version="%prog 1.0")
    parser.add_option("-f", "--file", dest="infile", help="Input File", metavar="FILE")
    parser.add_option("-c", "--chapter", dest="chapter", help="Chapter to fetch [int] or [0] to all", metavar="CHAP")
    parser.add_option("-s", "--split-scenes", action="store_true", dest="split", help="Split scenes on chosen chapter")
    (options, args) = parser.parse_args()

    chapters = get_chapters(options)
    convert_chapters(chapters)

    if options.split:
        split_scenes(options.chapter)
