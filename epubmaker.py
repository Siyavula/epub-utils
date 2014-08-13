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

try:
    from lxml import etree
except ImportError:
    print "lxml not found!"
    sys.exit(1)

try:
    from docopt import docopt
except ImportError:
    print "docopt not found!"
    sys.exit(1)

from libepub import epub



usage_info = """Usage: epubmaker.py --output OUTPUT --name NAME [--css=CSS] [--MathJax] FILE... | --help

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

#   htmlfiles.sort()
    print arguments['--css']
    print arguments['--MathJax']
    myEpub = epub.Epub(
        name=arguments['--name'], 
        outputfolder=arguments['--output'],
        toc={
#           1: 'h1',
#           2: 'h2',
#           3: 'h3'
# for siyavula workbooks. TODO fix this crap
            1:'body > div.section > h1.title',
            2:'div.section > div.section > h2.title',
            3:'div.section > div.section > div.section > h3.title'
            },
        css=arguments['--css'],
        mathjax=arguments['--MathJax'],
        verbose=True)

    myEpub.addhtml(htmlfiles)
    myEpub.write()

