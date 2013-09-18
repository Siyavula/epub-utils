#!/usr/bin/env python

#
# Create an epub from html files or folders containing html files.
# 
# 

import sys
import os
import time
import mimetypes
import shutil

from lxml import etree
from docopt import docopt

from libepub import epub

usage_info = """Usage: epubmaker.py --output OUTPUT --name NAME FILE... | --help

Arguments:
    -o --output OUTPUT Folder into which to write epub
    -n --name NAME     Name to give the epub 
    -h --help          Print this help message

"""


if __name__ == "__main__":
    arguments = docopt(usage_info, sys.argv[1:])
    print arguments
    htmlfiles = []
    for F in arguments['FILE']:
        # If it is a folder
        if os.path.isdir(F):
            for dirpath, folder, files in os.walk(F):
                for f in files:
                    if f.endswith(('.html', '.xhtml')):
                        htmlfiles.append(os.path.join(dirpath, f))
        # if it is a file
        else:
            if F.endswith(('.html', '.xhtml')):
                htmlfiles.append(F)

    htmlfiles.sort()

    myEpub = epub.Epub(
        name=arguments['--name'], 
        outputfolder=arguments['--output'])

    myEpub.addhtml(htmlfiles)
    print(etree.tostring(myEpub.package, pretty_print=True))
