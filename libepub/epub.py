#
#   epub class
#

# Epub folder has the following structure;
#
#   .
#   ..
#   mimetype
#   EPUB/
#       package-{name}.opf
#       xhtml/
#           {name}/
#               htmlfile1.html
#               htmlfile2.html
#               ...
#               htmlfileN.html
#               images/
#       css/
#       js/
#               
#   META-INF/
#       container.xml
#

import os
import logging
import time
import mimetypes
import sys
import copy

from lxml import etree
import re
try:
    import tinycss
except ImportError:
    print "tinycss not found!"
    sys.exit(1)

try:
    import cssselect
except ImportError:
    print "cssselect not found!"
    sys.exit(1)

class Epub:
    ''' Wrapper class for representing an epub.'''
    def __init__(self, **kwargs):
        self.html_source_paths = []
        self.img_source_paths = []
        self._manifest_ids_ = []
        self.js_source_paths = []
        self.css_source_paths = []

        if 'outputfolder' in kwargs.keys():
            self.epub_output_folder = os.path.abspath(kwargs['outputfolder'])
        else:
            self.epub_output_folder = os.path.abspath(os.curdir)

        if 'name' in kwargs.keys():
            self.epubname = kwargs['name']

        if 'verbose' in kwargs.keys(): 
            self.verbose = kwargs['verbose']
        else:
            self.verbose = False
        
        # how deep must the TOC reach?
        if 'toc' in kwargs.keys():
            self.toc = kwargs['toc']

        return


    def addhtml(self, htmlfiles):
        '''Given a list containing the paths to html files, add them to the epub object.
        i.e. update the manifest file
        '''
        # add the paths of the  html files
        for htmlfile in htmlfiles:
            source_path = os.path.normpath(htmlfile)
            self.html_source_paths.append(source_path)
            images = self._find_images_in_html(htmlfile)
            for image in images: self.img_source_paths.append(image)
       
        self.update_package()
        self.update_spine()
        self.create_nav()
        self._find_js_css_in_html()


    def _find_images_in_html(self, htmlfile):
        '''Find all images in given html file and return a list with their abs path.
        Duplicates are not added.
        '''
        # read the html contents
        images = []
        HTML = etree.HTML(open(htmlfile, 'r').read())
        for img in HTML.findall('.//img'):
            src = os.path.normpath(os.path.join(htmlfile, img.attrib.get('src')))
            if src is not None:
                if r'http:' in src:
                    if self.verbose: logging.warn("Skipping http link to image" + src)
                else:
                    if src not in self.img_source_paths:
                        images.append(src)
                    else:
                        if self.verbose: logging.warn(" " + src + " already added to list of images, skipping")
        return images 

    def update_spine(self):
        '''Read the package object and update the spine. Default is the sorted order of the html files'''
        manifest = self.package.find('.//manifest')
        spine = self.package.find('.//spine')
        if spine is None:
            spine = etree.Element('spine')
            manifest.addnext(spine)
        else:
            # clear it so it can be remade
            spine.clear()
            
        htmlfiles = [(mi.attrib['href'], mi.attrib['id']) for mi in self.package.findall('.//manifest/item') if mi.attrib['media-type'] == 'application/xhtml+xml']
        htmlfiles.sort()
        for hf in htmlfiles:
            href = hf[0]
            hfid = hf[1]
            itemref = etree.Element('itemref')
            itemref.attrib['idref'] = hfid
            spine.append(itemref)


    def create_nav(self):
        '''Uses all the html files and creates a nav tree'''
        nav = etree.HTML('''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
        <head>
            <meta charset="utf-8"/>
            <title>Table of Contents</title><
        </head>
        <body>        
            <nav epub:type="toc" id="toc"></nav>
        </body>
    </html>''')

        # Read each spine entry, they contain references to ids in the manifest.
        spineitems = self.package.findall('.//spine/itemref')
        manifest = self.package.find('.//manifest')

        for si in spineitems:
            idref = si.attrib.get('idref')
            # find html file that corresponds to that ID.
            # this href points to where the file WILL be in the EPUB once written to disk
            html = [m for m in manifest if m.attrib.get('id') == idref][0]
            
            # find in self.html_source_paths the one that matches this one.
            srchtml = [h for h in self.html_source_paths if h in html.attrib.get('href')][0]

            ol = etree.Element('ol')

            # read the HTML file and extract the title
            #title = etree.HTML(open(srchtml, 'r').read()).find('.//h1').text
            htags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            toc_css_matches = []
            htmlcontent = etree.HTML(open(srchtml, 'r').read())
            # For each toc css selector spec'd for TOC.
            for css in self.toc.keys():
                # elements that match one of the css selectors in toc.
                selector = cssselect.parse(self.toc[css])
                xpath = cssselect.HTMLTranslator().selector_to_xpath(selector[0])
                compiled_selector = etree.XPath(xpath)
                matches = [e for e in compiled_selector(htmlcontent)]
                # Make a list of all elements that match
                for m in matches: toc_css_matches.append((m,css))

            # Make a list of matching elements, in document order.
            toc = []
            for element in htmlcontent.iter():
                for m in toc_css_matches:
                    if element in m:
                        toc.append((element, m[1]))

            # build nested <ol> for the toc
            # parse a text representation
            toc_str = []
            toc_html = []
            for t in toc:
                ol = etree.Element('ol')
                li = etree.Element('li')
                ol.append(li)
                li.append(t[0])
                toc_html.append((t[1], ol))
                toc_str.append('-'*(t[1]) + r"{text}".format(text = t[0].text))
            
            
            i = len(toc_html) - 1
            for entry in reversed(toc_html):
                level = entry[0]
                element = entry[1]
                element.tail=None

                if i > 0:
                    if level == toc_html[i-1][0]:
                        for li in element:
                            toc_html[i-1][1][0].append(li)

                    elif level > toc_html[i-1][0]:
                        li = toc_html[i-1][1][-1]
                        li.append(element)
                i -= 1


            print len(toc_html) 

            print '\n'.join(toc_str)
            print '----------------'
            for t in toc_html: print etree.tostring(t[1], pretty_print=True, method='html')
            print '----------------'
            #print etree.tostring(toc_html, pretty_print=True, method='html')
            print

            

        

        
        return



    def _find_js_css_in_html(self):
        '''Find the css and javascript files linked to in the html'''
        manifest = self.package.find('.//manifest')
        # list containing src already included, avoid duplicates
        included_src = []
        for hf in self.html_source_paths:
            HTML = etree.HTML(open(hf, 'r').read())
            for script in HTML.findall('.//script'):
                src = script.attrib.get('src')
                if src is not None:
                    relsrc = os.path.normpath(os.path.join('xhtml', self.epubname, os.path.dirname(hf), src))
                    if relsrc not in included_src:
                        included_src.append(relsrc)
                        scripttype = mimetypes.guess_type(src)[0]
                        manifestitem = self.create_manifest_item(relsrc, scripttype)
                        manifest.append(manifestitem)

            for link in HTML.findall('.//link'):
                src = link.attrib.get('href')
                if src is not None:
                    relsrc = os.path.normpath(os.path.join('xhtml', self.epubname, os.path.dirname(hf), src))
                    if relsrc not in included_src:
                        included_src.append(relsrc)
                        scripttype = mimetypes.guess_type(src)[0]
                        if scripttype == 'text/css':
                            css_resources = self._get_css_resources(os.path.normpath(os.path.join(os.path.dirname(hf), src)))
                            # Add css resources to the manifest
                            for cs in css_resources:
                                if cs not in included_src:
                                    included_src.append(cs)
                                    srctype = mimetypes.guess_type(cs)[0]
                                    manifestitem = self.create_manifest_item(cs, srctype)
                                    manifest.append(manifestitem)


                        manifestitem = self.create_manifest_item(relsrc, scripttype)
                        manifest.append(manifestitem)

    def _urls_from_css(self, css):
        parser = tinycss.make_parser()
        for r in parser.parse_stylesheet(css).rules:
            if hasattr(r, 'declarations'):
                for d in r.declarations:
                    for tok in d.value:
                        if tok.type == 'URI':
                            yield tok.value
    
    def _get_css_resources(self, css):
        '''find all urls in the css file, return a list'''
        urls = []
        try:
            csscontent = open(css, 'r').read()

            for url in self._urls_from_css(csscontent):
                urls.append(url)

            urls = [os.path.normpath(os.path.join(os.path.dirname(css), url)) for url in urls]

        except IOError:
            logging.error("Cannot open file: " + css)

        return urls


    def print_structure(self):
        '''Print a breakdown of the epub structure'''

        print("HTML files")
        for h in self.html_source_paths:
            print(h)

        print('')
        print("image files")
        for img in self.img_source_paths:
            print(img)


    def create_manifest_item(self, href, mediatype, attribs=None):
        '''creates a manifest/item object and returns it '''
        item = etree.Element('item')
        item.tail = '\n'
        i = 0
        item_id = 'ID-{num}'.format(num=i)
        while item_id in self._manifest_ids_:
            i += 1
            item_id = 'ID-{num}'.format(num=i)

        self._manifest_ids_.append(item_id)
        item.attrib['id'] = item_id
        item.attrib['href'] = href
        item.attrib['media-type'] = mediatype

        if attribs is not None:
            for k in attribs.keys():
                item.attrib[k] = attribs[k]

        return item

    
    def _create_package(self):
        '''creates an empty package xml tree'''
        package = etree.Element('package',
                nsmap={None:"http://www.idpf.org/2007/opf"},
                attrib={'version':'3.0', 'unique-identifier':'uid'})
        metadata = etree.XML(r'''<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:language>en</dc:language></metadata>''')

        manifest = etree.Element('manifest')

        package.append(metadata)
        package.append(manifest)

        self.package = package


    def update_package(self):
        '''Update the package xml tree'''

        # create the package object if it does not exist
        if not hasattr(self, 'package'):
            self._create_package()
       
        manifest = self.package.find('.//manifest')
        # add html files to manifest
        for htmlfile in self.html_source_paths:
            # href is where this file will live in EPUB
            href = os.path.join('xhtml', self.epubname, htmlfile)
            manifestitem = self.create_manifest_item(href, "application/xhtml+xml")
            manifest.append(manifestitem)

        # add images
        for img in self.img_source_paths:
            href = os.path.join('xhtml', self.epubname, img)
            imgtype = mimetypes.guess_type(href)[0]
            manifestitem = self.create_manifest_item(href, imgtype)
            manifest.append(manifestitem)

        return
