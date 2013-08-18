#!/usr/bin/env python

#
# Turn a Siyavula cnxmlplus.html book repo into an epub file.
# Assume each cnxmlplus file has been converted to html,
# and contains a chapter

import sys
import os
import time
import mimetypes
import shutil

from lxml import etree
from docopt import docopt

usage_info = """Usage: bookrepo2epub.py  --output <outputfolder>  --name <name> | --help



Arguments:
    --output  folder where EPUB will be created or updated
    --name    name of content that will be displayed in epub
    --help    display this message

"""



def makepackage(htmlfiles, docoptions):
    '''Make a package.opf file given a list of html files

    docoptions: arguments dict from docopt

    package.opf looks like:
    
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
   <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:identifier id="uid">siyavula.com.physics.1.0</dc:identifier>
      <dc:title>Siyavula Education: Everything Physics</dc:title>
      <dc:creator>Siyavula Education</dc:creator>
      <dc:language>en</dc:language>
      <meta property="dcterms:modified">2012-02-27T16:38:35Z</meta>
   </metadata>
   <manifest>
    <item href="path" id="blah" media-type="blahblah"/> for each file, image and nav file in epub, each with unique id.
    </manifest>
    <spine>
     <itemref idref="blah"/> 
    </spine>
    </package>
    
    '''

    currenttime = time.asctime(time.gmtime()) + " GMT"

    package = etree.Element('package',
        nsmap={'xmlns':"http://www.idpf.org/2007/opf"},
        attrib={'version':'3.0', 'unique-identifer':'uid'})
    package.text = '\n'
    metadata = etree.XML('''
       <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:identifier id="uid">siyavula.com.dummy-book-repo.1.0</dc:identifier>
          <dc:title>Siyavula Education: Dummy Book</dc:title>
          <dc:creator>Siyavula Education</dc:creator>
          <dc:language>en</dc:language>
          <meta property="dcterms:modified">{time}</meta>
       </metadata>'''.format(time = currenttime))

    manifest = etree.Element('manifest')
    manifest.text = '\n'

    # add the nav file that will be there

    navmanifestitem = etree.Element('item')
    navmanifestitem.attrib['id'] = "nav"
    navmanifestitem.attrib['href'] = r"xhtml/{name}/{name}.nav.html".format(name=docoptions['<name>'])
    navmanifestitem.attrib['media-type'] = "application/xhtml+xml"
    navmanifestitem.attrib['properties'] = "nav"
    navmanifestitem.tail = '\n'

    manifest.append(navmanifestitem)

    spine = etree.Element('spine')
    spine.text = '\n'

    # loop through every htmlfile
    for num, hf in enumerate(htmlfiles):
        # read the file's contents and create etree object
        htmlobject = etree.HTML(open(hf, 'r').read())

        # add htmlfile to manifest
        # assume these files will be moved to a folder called xhtml/name in the
        # current folder
        html_dest_dir = r"{epubname}/EPUB/xhtml/{name}/{filename}".format(name=docoptions['<name>'],
            filename=hf,
            epubname=docoptions['<outputfolder>'])
        manifestitem = etree.Element('item')
        manifestitem.attrib['id'] = "chapter-{num}".format(num=num)
        manifestitem.attrib['href'] = r"xhtml/{name}/{filename}".format(name=docoptions['<name>'],
            filename=hf)

        manifestitem.attrib['media-type'] = "application/xhtml+xml"
        manifestitem.tail = '\n'

        # insert html item to the start of the file
        manifest.insert(num, manifestitem)

        # add html to spine
        itemref = etree.Element('itemref')
        itemref.tail = '\n'
        itemref.attrib['idref'] = manifestitem.attrib['id']
        spine.append(itemref)

        # copy the html to that location
        shutil.copy(hf, html_dest_dir)

        # loop through every img and add it to the end of manifest
        for img in htmlobject.findall('.//img'):

            bookdir = '/'.join(html_dest_dir.split('/')[2:-1])
            href = os.path.join(bookdir, img.attrib.get('src'))
            # copy the image to that place
            newdir = '/'.join(href.split('/')[0:-1])
            if not os.path.exists(newdir):
                os.makedirs(newdir)

            if not os.path.exists(img.attrib['src']):
                print 'WARNING: ', img.attrib['src'],  "does not exist!"
            else:
                shutil.copy(img.attrib['src'], href)
            
            manifestitem = etree.Element('item')
            manifestitem.attrib['id'] = "{filename}".format(filename = href.split('/')[-1].strip())
            manifestitem.attrib['href'] = r"{filename}".format(filename=href)
            manifestitem.attrib['media-type'] = mimetypes.guess_type(href)[0]
            manifestitem.tail = '\n'
            manifest.append(manifestitem)

    
    package.append(metadata)
    package.append(manifest)
    package.append(spine)

    return package


def makenavfile(package, docoptions):
    '''Given package object, create the nav file and return as etree object'''
     
    html = etree.Element('html')
    head = etree.Element('head')
    body = etree.Element('body')
    nav = etree.Element('nav')
    ol = etree.Element('ol')
    nav.append(ol)
    h1 = etree.Element('h1')
    h1.text = 'Table of Contents'
    h1.tail = '\n'

    for spineitem in package.findall('.//spine/itemref'):
        idref = spineitem.attrib['idref']
        #  find html file in packagefile with that id
        htmlitem = [item for item in package.findall('.//manifest/item') if item.attrib['id'] == idref]
        path = '{outputfolder}/EPUB/{path}'.format(outputfolder=docoptions['<outputfolder>'],name=docoptions['<name>'], path=htmlitem[0].attrib['href'])
        
        # find title of html file content
        thishtml = etree.HTML(open(path, 'r').read())
        title = thishtml.find('.//h1')
        if title is not None:
            # Take the first H1 as the title
            title = title.text
        else:
            # Else make it the filename with some mods
            title = path.split('/')[-1][0:-4].replace('-', ' ')
        li = etree.Element('li')
        a = etree.Element('a')
        a.attrib['href'] = path.split('/')[-1]
        a.text = title

        li.append(a)
        ol.append(li)


    # build the nav file
    html.append(head)
    html.append(body)
    body.append(h1)
    html.append(nav)

    return html


def make_new_epub_folder(options):
    '''given docopt's arguments dict: create an empty epub folder if it does not exist'''
    epubdir = options['<outputfolder>']

    name = options['<name>'].replace(' ', '-').lower()
    EPUBdir = os.path.join(epubdir, 'EPUB')
    METAdir = os.path.join(epubdir, 'META-INF')
    xhtmldir = os.path.join(EPUBdir, 'xhtml')
    namedir = os.path.join(xhtmldir, name)

    if not os.path.isdir(epubdir):
        os.mkdir(epubdir)
    if not os.path.isdir(EPUBdir):
        os.mkdir(EPUBdir)
    if not os.path.isdir(METAdir):
        os.mkdir(METAdir)
    if not os.path.isdir(xhtmldir):
        os.mkdir(xhtmldir)
    if not os.path.isdir(namedir):
        os.mkdir(namedir)

    return True


def make_container(docoptions):
    epubfolder = docoptions['<outputfolder>']
    metafolder = os.path.join(epubfolder, 'META')

    if not os.path.exists(metafolder):
        os.makedirs(metafolder)
    containerpath = os.path.join(metafolder, "container.xml")
    if os.path.exists(containerpath):
        try:
            container = etree.parse(containerpath)
        except etree.XMLSyntaxError:
            container = etree.XML('<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles></rootfiles></container>')
    else:
        container = etree.XML('<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles></rootfiles></container>')

    packagefilepath = "EPUB/{name}.opf".format(name=docoptions['<name>'])
    current_rootfiles = [r.attrib['full-path'] for r in container.findall('.//rootfile')]

    if packagefilepath not in current_rootfiles:
        rootfile = etree.Element('rootfile', attrib={'media-type':"application/oebps-package+xml", 'version':'1.0', 'full-path':packagefilepath})
        container.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfiles').append(rootfile)

    return container
    

if __name__ == "__main__":
    arguments = docopt(usage_info, sys.argv[1:])
    outputfolder = arguments['<outputfolder>']
    bookname = arguments['<name>']
    make_new_epub_folder(arguments)


    # find all the html files in the current folder
    htmlfiles = os.listdir(os.curdir)
    htmlfiles = [hf.strip() for hf in htmlfiles if hf.strip().endswith('.html')]
    htmlfiles.sort()

    # make the package and nav files
    package = makepackage(htmlfiles, arguments)
    navhtml = makenavfile(package, arguments)

    # write them to the correct folders
    package_dest = os.path.join(outputfolder, "EPUB", "package-{bookname}.opf".format(bookname=bookname))
    with open(package_dest , 'w') as f:
        f.write(r'<?xml version="1.0" encoding="UTF-8"?>')
        f.write(etree.tostring(package, pretty_print=True))
    
    nav_dest = os.path.join(outputfolder, "EPUB", "xhtml", "{bookname}".format(bookname=bookname),"{bookname}.nav.html".format(bookname=bookname) )
    with open(nav_dest , 'w') as f:
        f.write(r'<?xml version="1.0" encoding="UTF-8"?>')
        f.write(etree.tostring(navhtml, pretty_print=True))
     
    epubfolder = arguments['<outputfolder>']
    metafolder = os.path.join(epubfolder, 'META')
    containerpath = os.path.join(metafolder, "container.xml")
    container = make_container(arguments)
    with open(containerpath, 'w') as f:
        f.write(etree.tostring(container, pretty_print=True))

