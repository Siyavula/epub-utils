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

from lxml import etree

class Epub:
    ''' Wrapper class for representing an epub.'''
    def __init__(self, **kwargs):
        self.html_source_paths = []
        self.img_source_paths = []
        self._manifest_ids_ = []

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
        # add the absolute paths of the  html files
        for htmlfile in htmlfiles:
            source_path = os.path.normpath(htmlfile)
            self.html_source_paths.append(source_path)
            images = self._find_images_in_html(htmlfile)
            for image in images: self.img_source_paths.append(image)
        
        self.update_package()

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
                if src not in self.img_source_paths:
                    images.append(src)
                else:
                    logging.warn(" " + src + " already added to list of images, skipping")
        return images 


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


        return
