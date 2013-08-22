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

# uncomment to debug
#import pudb; pu.db

usage_info = """Usage: bookrepo2epub.py  --output <outputfolder>  --name <name> | --help



Arguments:
    --output  folder where EPUB will be created or updated
    --name    name of content that will be displayed in epub
    --help    display this message

"""

_manifest_ids_ = []





def create_manifest_item(href, mediatype, attribs=None):
    '''creates a manifest/item object and returns it '''
    item = etree.Element('item')
    item.tail = '\n'
    i = 0
    item_id = 'ID-{num}'.format(num=i)
    while item_id in _manifest_ids_:
        i += 1
        item_id = 'ID-{num}'.format(num=i)

    _manifest_ids_.append(item_id)
    item.attrib['id'] = item_id
    item.attrib['href'] = href
    item.attrib['media-type'] = mediatype

    if attribs is not None:
        for k in attribs.keys():
            item.attrib[k] = attribs[k]

    return item


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
        nsmap={None:"http://www.idpf.org/2007/opf"},
        attrib={'version':'3.0', 'unique-identifier':'uid'})
    package.text = '\n'
    metadata = etree.XML('''
       <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:identifier id="uid">siyavula.com.dummy-book-repo.1.0</dc:identifier>
          <dc:title>Siyavula Education: {bookname}</dc:title>
          <dc:creator>Siyavula Education</dc:creator>
          <dc:language>en</dc:language>
          <meta property="dcterms:modified">{time}</meta>
       </metadata>'''.format(time = currenttime, bookname=docoptions['<name>']))

    manifest = etree.Element('manifest')
    manifest.text = '\n'

    # add the nav file that will be there
    navmanifestitem = create_manifest_item(r"xhtml/{name}/{name}.nav.html".format(name=docoptions['<name>']),
    "application/xhtml+xml", attribs={'properties':'nav'})
    manifest.append(navmanifestitem)

    spine = etree.Element('spine')
    spine.text = '\n'

    used_ids = []

    # loop through every htmlfile
    for num, hf in enumerate(htmlfiles):
        # read the file's contents and create etree object
        htmlobject = etree.HTML(open(hf, 'r').read())

        # add htmlfile to manifest
        # assume these files will be moved to a folder called xhtml/name in the
        # current folder
        rootdir = os.path.abspath(r"{epubpath}".format(epubpath=docoptions['<outputfolder>']))
        html_dest_dir = os.path.realpath(r"{epubname}/EPUB/xhtml/{name}/{filename}".format(name=docoptions['<name>'],
            filename=os.path.normpath(hf),
            epubname=docoptions['<outputfolder>']))

        manifestitem = create_manifest_item(r"xhtml/{name}/{filename}".format(name=docoptions['<name>'], filename=hf), "application/xhtml+xml")
        # insert html item to the start of the file
        manifest.insert(num, manifestitem)

        # add html to spine
        itemref = etree.Element('itemref')
        itemref.tail = '\n'
        itemref.attrib['idref'] = manifestitem.attrib['id']
        spine.append(itemref)

        
        # copy the html to that location
        if not os.path.exists(os.path.dirname(html_dest_dir)):
            os.makedirs(os.path.dirname(html_dest_dir))
        shutil.copy(hf, html_dest_dir)
      

        # create empty css and javsscript files if they are not there
        for link in htmlobject.findall('.//head/link'):
            cssfile = link.attrib['href']
            cssabspath = os.path.abspath(os.path.join(os.path.dirname(html_dest_dir), cssfile))
            cssrelpath = os.path.relpath(cssabspath, os.path.join(rootdir, 'EPUB'))

            if not os.path.exists(cssabspath):
                if not os.path.exists(os.path.dirname(cssabspath)):
                    os.makedirs(os.path.dirname(cssabspath))
                with open(cssabspath, 'w') as f:
                    f.write('\* CSS \*')

            # add to manifest if its not there already
            if not any(hr.attrib['href'] == cssrelpath for hr in manifest.findall('.//item')):
                manifestitem = create_manifest_item(cssrelpath, 'text/css')
                manifest.append(manifestitem)

        for script in htmlobject.findall('.//script'):
            linkfile = script.attrib['src']
            linkabspath = os.path.abspath(os.path.join(os.path.dirname(html_dest_dir), linkfile))
            linkrelpath = os.path.relpath(linkabspath, os.path.join(rootdir, 'EPUB'))

            if not os.path.exists(linkabspath):
                if not os.path.exists(os.path.dirname(linkabspath)):
                    os.makedirs(os.path.dirname(linkabspath))
                with open(linkabspath, 'w') as f:
                    f.write('\* Javascript \*')

            # add to manifest if its not there already
            if not any(hr.attrib['href'] == linkrelpath for hr in manifest.findall('.//item')):
                manifestitem = create_manifest_item(linkrelpath, 'application/javascript')
                manifest.append(manifestitem)


       
        # loop through every img and add it to the end of manifest
        for img in htmlobject.findall('.//img'):
            bookdir = os.path.abspath(os.path.join(docoptions['<outputfolder>']))
            img_current_dir = os.path.realpath(img.attrib['src'])
            img_current_path = os.path.realpath(os.path.join(os.path.dirname(hf), img.attrib['src']))
            img_dest_dir = os.path.join(bookdir, 'EPUB', 'xhtml', docoptions['<name>'], os.path.dirname(hf), os.path.dirname(img.attrib['src']))
            href = os.path.join('xhtml', docoptions['<name>'], os.path.dirname(hf), img.attrib.get('src'))
            # copy the image to that place
            if not os.path.exists(img_dest_dir):
                try:
                    os.makedirs(img_dest_dir)
                except OSError:
                    print "WARNING! Cannot create folder {folder}".format(folder=img_dest_dir)

            if not os.path.exists(img_current_path):
                print 'WARNING: ', img.attrib['src'],  "does not exist!"
            else:
                shutil.copy(img_current_path, img_dest_dir)
            
            manifestitem = create_manifest_item(r"{filename}".format(filename=href), mimetypes.guess_type(href)[0])
            manifest.append(manifestitem)
    
    package.append(metadata)
    package.append(manifest)
    package.append(spine)
    

    return package


def makenavfile(package, docoptions):
    '''Given package object, create the nav file and return as etree object'''
     
    html = etree.HTML('''<html xmlns:epub="http://www.idpf.org/2007/ops" xmlns="http://www.w3.org/1999/xhtml"</html>''')
    head = etree.Element('head')
    section = etree.Element('section')
    section.attrib['type'] = "toc"
    nav = etree.Element('nav')
    ol = etree.Element('ol')
    ol.tail = '\n'
    nav.append(ol)
    h1 = etree.Element('h1')
    h1.text = 'Table of Contents'
    h1.tail = '\n'

    for spineitem in package.findall('.//spine/itemref'):
        idref = spineitem.attrib['idref']
        #  find html file in packagefile with that id
        htmlitem = [item for item in package.findall('.//manifest/item') if item.attrib['id'] == idref]
        path = os.path.normpath('{outputfolder}/EPUB/{path}'.format(outputfolder=docoptions['<outputfolder>'],name=docoptions['<name>'], path=htmlitem[0].attrib['href']))
        
        # find title of html file content
        thishtml = etree.HTML(open(path, 'r').read())
        title = thishtml.find('.//head/title')
        if title is not None:
            # Take the first H1 as the title
            title = title.text
        else:
            # Else make it the filename with some mods
            title = path.split('/')[-1][0:-4].replace('-', ' ')
        li = etree.Element('li')
        li.tail = '\n'
        a = etree.Element('a')
        a.tail='\n'
        a.attrib['href'] = os.path.normpath(os.path.join('/'.join(htmlitem[0].attrib['href'].split('/')[2:])))
        a.text = title

        li.append(a)
        ol.append(li)


    # build the nav file
    html.append(head)
    html.tail = '\n'
    body = etree.Element('body')
    html.append(body)
    body.append(section)
    section.append(h1)
    section.tail = '\n'
    section.append(nav)
    nav.tail = '\n'

    return html


def make_new_epub_folder(options):
    '''given docopt's arguments dict: create an empty epub folder if it does not exist'''
    epubdir = os.path.abspath(os.path.join(os.curdir, options['<outputfolder>']))

    name = options['<name>'].replace(' ', '-')
    EPUBdir = os.path.join(epubdir, 'EPUB')
    METAdir = os.path.join(epubdir, 'META-INF')
    xhtmldir = os.path.join(EPUBdir, 'xhtml')
    namedir = os.path.join(xhtmldir, name)

    if not os.path.isdir(epubdir):
        os.makedirs(epubdir)
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
    metafolder = os.path.join(epubfolder, 'META-INF')

    if not os.path.exists(metafolder):
        os.makedirs(metafolder)
    containerpath = os.path.join(metafolder, "container.xml")
    if os.path.exists(containerpath):
        try:
            container = etree.parse(containerpath)
        except etree.XMLSyntaxError:
            container = etree.XML('<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>\n</rootfiles></container>')
    else:
        container = etree.XML('<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>\n</rootfiles></container>')

    packagefilepath = "EPUB/package-{name}.opf".format(name=docoptions['<name>'])
    current_rootfiles = [r.attrib['full-path'] for r in container.findall('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')]
    if packagefilepath not in current_rootfiles:
        rootfile = etree.Element('rootfile', attrib={'media-type':"application/oebps-package+xml", 'version':'1.0', 'full-path':packagefilepath})
        rootfile.tail = '\n'
        container.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfiles').append(rootfile)

    return container
    

if __name__ == "__main__":
    arguments = docopt(usage_info, sys.argv[1:])
    outputfolder = arguments['<outputfolder>']
    bookname = arguments['<name>']
    make_new_epub_folder(arguments)


    # find all the html files in the current folder
#   htmlfiles = os.listdir(os.curdir)
    htmlfiles = []
    for dirpath, folder, files in os.walk(os.curdir):
        for f in files:
            if f.endswith(('.html', '.xhtml')):
                htmlfiles.append(os.path.join(dirpath, f))


#   htmlfiles = [hf.strip() for hf in htmlfiles if hf.strip().endswith('html')]
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
    metafolder = os.path.join(epubfolder, 'META-INF')
    containerpath = os.path.join(metafolder, "container.xml")
    container = make_container(arguments)
    with open(containerpath, 'w') as f:
        f.write(etree.tostring(container, pretty_print=True))

    # write mimetype
    with open(os.path.join(epubfolder, 'mimetype'), 'w') as f:
        f.write('application/epub+zip')
        f.close()


