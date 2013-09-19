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

from lxml import etree
import re
import tinycss

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
                    logging.warn("Skipping http link to image" + src)
                else:
                    if src not in self.img_source_paths:
                        images.append(src)
                    else:
                        logging.warn(" " + src + " already added to list of images, skipping")
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
