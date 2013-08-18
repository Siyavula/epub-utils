#!/usr/bin/env python

#
# Turn a Siyavula cnxmlplus.html book repo into an epub file.
# Assume each cnxmlplus file has been converted to html,
# and contains a chapter

import sys
import os
import time
import mimetypes

from lxml import etree

def makepackage(htmlfiles):
    '''Make a package.opf file given a list of html files
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

    spine = etree.Element('spine')
    spine.text = '\n'


    # loop through every htmlfile
    for num, hf in enumerate(htmlfiles):
        # read the file's contents and create etree object
        htmlobject = etree.HTML(open(hf, 'r').read())


        # add htmlfile to manifest
        # assume these files will be moved to a folder called xhtml in the
        # current folder
        manifestitem = etree.Element('item')
        manifestitem.attrib['id'] = "chapter-{num}".format(num=num)
        manifestitem.attrib['href'] = r"xhtml/{filename}".format(filename=hf)
        manifestitem.attrib['media-type'] = "application/xhtml+xml"
        manifestitem.tail = '\n'

        # insert html item to the start of the file
        manifest.insert(num, manifestitem)

        # add html to spine
        itemref = etree.Element('itemref')
        itemref.tail = '\n'
        itemref.attrib['idref'] = manifestitem.attrib['id']
        spine.append(itemref)

        # loop through every img and add it to the end of manifest
        for img in htmlobject.findall('.//img'):
            href = 'xhtml/' + img.attrib.get('src')

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


def makenavfile(package):
    '''Given package object, create the nav file and return as etree object'''
    
    html = etree.Element('html')
    head = etree.Element('head')
    body = etree.Element('body')
    nav = etree.Element('nav')
    h1 = etree.Element('h1')
    h1.text = 'Table of Contents'
    h1.tail = '\n'

    for spineitem in package.findall('.//spine/itemref'):
        idref = spineitem.attrib['idref']
        #  find html file in packagefile with that id
        htmlitem = [item for item in package.findall('.//manifest/item') if item.attrib['id'] == idref]
        path = htmlitem[0].attrib['href']
        
        # find title of html file content



    # build the nav file
    html.append(head)
    html.append(body)
    nav.append(h1)
    html.append(nav)

    return html

if __name__ == "__main__":
    
    htmlfiles = os.listdir(os.curdir)
    htmlfiles = [hf.strip() for hf in htmlfiles if hf.strip().endswith('.html')]
    htmlfiles.sort()

    package = makepackage(htmlfiles)
    
    print r'<?xml version="1.0" encoding="UTF-8"?>'
    print etree.tostring(package)

    navhtml = makenavfile(package)
    print etree.tostring(navhtml)
