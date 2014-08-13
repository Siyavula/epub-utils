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
import shutil
import errno

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


def mkdir_p(path):
    ''' mkdir -p functionality
    from http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    '''
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class resource:

    '''Container object for manifest resources'''

    def __init__(self, src):
        self.src = src
        self.destination = None

        self.clean_src()

    def __eq__(self, other):
        return (self.src == other.src)

    def clean_src(self):
        '''cleans the src'''

        # clean out any newline characters in the src string
        self.src = self.src.replace('\n', '')


class resources:

    '''container and methods to keep track of resources'''

    def __init__(self):
        self._ids = []
        self.resources = []

    def add(self, resource):
        '''adds a resource to the container and gives it a unique ID. Won't add duplicate resources'''
        i = 0
        if resource not in self.resources:
            resource_id = "ID-{num}".format(num=i)
            while resource_id in self._ids:
                i += 1
                resource_id = "ID-{num}".format(num=i)

            self._ids.append(resource_id)
            resource._id = resource_id
            self.resources.append(resource)


class Epub:

    ''' Wrapper class for representing an epub.'''

    def __init__(self, **kwargs):
        self._manifest_ids_ = []
        self.resources = resources()

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

        if 'css' in kwargs.keys():
            # add a css file to each html file
            self.extra_css = kwargs['css']
        else:
            self.extra_css = None

        if 'mathjax' in kwargs.keys():
            self.MathJax = True
        else:
            self.MathJax = False

        # how deep must the TOC reach?
        if 'toc' in kwargs.keys():
            self.toc = kwargs['toc']

        return

    def addhtml(self, htmlfiles):
        '''Given a list containing the paths to html files, add them to the epub object.
        i.e. update the manifest file
        '''
        # parse and add the content of the  html files as etree objects
        for htmlfile in htmlfiles:
            source_path = os.path.normpath(htmlfile)
            content = etree.HTML(open(source_path, 'r').read())

            # Add Mathjax if the flag is set
            if self.MathJax == True:
                content = self.add_mathjax_to_html(content)

            # add any extra css here.
            if self.extra_css is not None:
                css_rel_path = os.path.relpath(os.path.dirname(
                    os.path.abspath(self.extra_css)), os.path.dirname(os.path.abspath(source_path)))
                css_rel_path = os.path.join(css_rel_path, self.extra_css)
                css = etree.XML(
                    '<link rel="stylesheet" type="text/css" href="{stylesheet}"/>'.format(stylesheet=css_rel_path))
                head = content.find('.//head')
                head.append(css)

            thisresource = resource(source_path)
            thisresource.HTMLObject = content
            self.resources.add(thisresource)
            images = self._find_images_in_html(thisresource)

            for image in images:
                imgresource = resource(image)
                self.resources.add(imgresource)

        self._find_js_css_in_html()
        self.update_package()
        self.update_spine()
        self.create_nav()

    def _find_images_in_html(self, htmlfile):
        '''Find all images in given html file and return a list with their abs path.
        Duplicates are not added.
        '''
        # read the html contents
        images = []
        HTML = htmlfile.HTMLObject
        for img in HTML.findall('.//img'):
            src = os.path.normpath(
                os.path.join(os.path.dirname(htmlfile.src), img.attrib.get('src')))
            if src is not None:
                if r'http:' in src:
                    if self.verbose:
                        logging.warn("Skipping http link to image" + src)
                else:
                    imgresource = resource(src)
                    if imgresource not in self.resources.resources:
                        self.resources.add(imgresource)
                        images.append(src)
                    else:
                        if self.verbose:
                            logging.warn(
                                " " + src + " already added to list of images, skipping")
        return images

    def update_spine(self):
        '''Read the package object and update the spine. Default is the sorted order of the html files'''
        manifest = self.package.find('.//manifest')
        spine = self.package.find('.//spine')
        if spine is None:
            spine = etree.Element('spine')
            spine.attrib['toc'] = 'ncx'
            manifest.addnext(spine)
        else:
            # clear it so it can be remade
            spine.clear()

        htmlfiles = [(mi.attrib['href'], mi.attrib['id']) for mi in self.package.findall(
            './/manifest/item') if mi.attrib['media-type'] in ['application/xhtml+xml', 'text/html']]
#       htmlfiles.sort()
        for hf in htmlfiles:
            href = hf[0]
            hfid = hf[1]
            itemref = etree.Element('itemref')
            itemref.attrib['idref'] = hfid
            spine.append(itemref)

    def create_nav(self):
        '''Uses all the html files and creates a nav tree'''
        self.nav = etree.HTML('''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <meta charset="utf-8"></meta>
</head>
<body>        
    <nav epub:type="toc" id="toc"></nav>
</body>
</html>''')

        # Read each spine entry, they contain references to ids in the
        # manifest.
        spineitems = self.package.findall('.//spine/itemref')
        manifest = self.package.find('.//manifest')

        for si in spineitems:
            idref = si.attrib.get('idref')
            # find html file that corresponds to that ID.
            # this href points to where the file WILL be in the EPUB once
            # written to disk
            html = [m for m in manifest if m.attrib.get('id') == idref][0]

            # find in self.html_source_paths the one that matches this one.
            srcres = [
                res for res in self.resources.resources if res.src in html.get('href')][0]
            srchtml = [
                res.src for res in self.resources.resources if res.src in html.get('href')][0]
            # the index of the html source code in self.html_source
            htmlcontent = srcres.HTMLObject
            # find the resource that has this id
            thisresource = self.resources.resources[
                self.resources._ids.index(idref)]
            thisresource.content = htmlcontent
            # read the HTML file and extract the title
            toc_css_matches = []
            # For each toc css selector spec'd for TOC.
            for css in self.toc.keys():
                # elements that match one of the css selectors in toc.
                selector = cssselect.parse(self.toc[css])
                xpath = cssselect.HTMLTranslator().selector_to_xpath(
                    selector[0])
                compiled_selector = etree.XPath(xpath)
                matches = [e for e in compiled_selector(htmlcontent)]
                # Make a list of all elements that match
                for m in matches:
                    toc_css_matches.append((m, css))

            # Make a list of matching elements, in document order.
            toc = []
            toc_ids = []
            Id = 0
            for element in htmlcontent.iter():
                for m in toc_css_matches:
                    if element in m:
                        # create some unique IDs for the toc elements if they
                        # don't have them
                        if element.attrib.get('id') is None:
                            element_id = "toc-id-{Id}".format(Id=Id)
                            while element_id in toc_ids:
                                Id += 1
                                element_id = "toc-id-{Id}".format(Id=Id)
                            element.attrib['id'] = element_id
                        else:
                            element_id = element.attrib.get('id')

                        toc_ids.append(element_id)
                        toc.append((element, m[1], element_id))

            # build nested <ol> for the toc
            toc_str = []
            toc_html = []
            for t in toc:
                li = etree.Element('li')
                text = ''.join([tt for tt in t[0].itertext()])
                a = etree.Element('a')
                a.text = text
                a.attrib['href'] = srchtml + '#{Id}'.format(Id=t[2])
                li.append(a)
                toc_html.append((t[1], li))
                titletext = "".join(
                    [ttt for ttt in t[0].itertext()]).encode('utf-8')
                toc_str.append('-' * (t[1]) + r"{text}".format(text=titletext))

            # move forward through the list and put <li> in <ol> if previous
            # one has different level
            level = 0
            for i, entry in enumerate(toc_html):
                if entry[0] != level:
                    level = entry[0]
                    ol = etree.Element('ol')
                    ol.append(entry[1])
                    toc_html[i] = (level, ol)

            # while there are any <li> in the list, add them to
            li_in_list = any([t[1].tag == 'li' for t in toc_html])
            while li_in_list:
                for i, t in enumerate(toc_html):
                    level = t[0]
                    el = t[1]
                    if i > 0:
                        if el.tag == 'li':
                            if toc_html[i - 1][1].tag == 'ol':
                                if level == toc_html[i - 1][0]:
                                    toc_html[i - 1][1].append(el)
                                    del toc_html[i]

                li_in_list = any([t[1].tag == 'li' for t in toc_html])

            # go through the list in reverse and add same level li together
            while len(toc_html) > 1:
                i = len(toc_html) - 1
                for entry in reversed(toc_html):
                    level = entry[0]
                    if i > 0:
                        # add similar levels together
                        if level == toc_html[i - 1][0]:
                            ol = toc_html[i - 1][1]
                            for li in entry[1]:
                                ol.append(li)
                            del toc_html[i]

                        # if the next level is lower, add this <ol> to the last
                        # <li> of the next
                        if level > toc_html[i - 1][0]:
                            toc_html[i - 1][1][-1].append(toc_html[i][1])
                            del toc_html[i]
                    i -= 1

            # finally merge similar <ol> together.
            toc_html = toc_html[0][1]
            ol = etree.Element('ol')
            ol.append(toc_html)
            toc_html = ol

            # add a toplevel ordered list
            navelement = self.nav.find('.//nav')
            navelement.append(ol)

        while any([o.tag == o.getnext().tag for o in self.nav.findall('.//ol') if o.getnext() is not None]):
            for ol in self.nav.findall('.//ol'):
                if ol.getnext() is not None:
                    # if two <ol> items are siblings
                    if ol.getnext().tag == 'ol':
                        for li in ol.getnext():
                            ol.append(li)
                        if len(ol.getnext()) == 0:
                            ol.getparent().remove(ol.getnext())

        # remove top-level ol. Prob a bug but it seems consistent.
        firstol = self.nav.find('.//ol')
        secondol = firstol.find('.//ol')
        firstol.addnext(secondol)
        firstol.getparent().remove(firstol)

        # add nav to package file.
        navpath = os.path.normpath(os.path.join(
            'xhtml', self.epubname, "{name}.nav.xhtml".format(name=self.epubname)))
        manifestitem = self.create_manifest_item(
            navpath, "application/xhtml+xml")
        manifestitem.attrib['properties'] = 'nav'
        manifestitem.attrib['id'] = 'nav'
        manifest = self.package.find('.//manifest')
        manifest.append(manifestitem)

        self.create_ncx()

        return

    def _remove_and_add_mathjax_script(self, html):
        ''' given etree Element, removes the script element that calls mathjax'''
        remove = []
        for script in html.findall('.//script'):
            if 'MathJax.js' in script.attrib['src']:
                remove.append(script)
        for r in remove:
            r.getparent().remove(r)

        # add a new script element for where mathjax lives.
        head = html.find('.//head')
        script = etree.fromstring(
            r'<script type="text/javascript" src="mathjax/MathJax.js?config=TeX-AMS-MML_HTMLorMML"> </script>')
        head.append(script)

        return html

    def add_mathjax_to_html(self, html):
        '''Adds MathJax this given html etree element and to the manifest if it is not there yet.'''
        mathjax_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'resources', 'mathjax'))
        use_local_mathjax = False

        # check if mathjax exists in the current folder
        if os.path.exists('mathjax'):
            logging.warning(" MathJax found in current folder, using that")
            mathjax_path = os.path.abspath(os.path.join(os.curdir, 'mathjax'))
            use_local_mathjax = True

        for dirpath, dirname, filename in os.walk(mathjax_path):
            for f in filename:
                src = os.path.join(dirpath, f)
                # html contains link to mathjax, remove it
                html = self._remove_and_add_mathjax_script(html)

                # want to copy all the mathjax files to the OPS folder
                # i.e. OPS/mathjax

                OPS_path = os.path.join(self.epub_output_folder, 'OPS')
                destination = os.path.join(
                    OPS_path, os.path.relpath(src, os.path.join(mathjax_path, '..')))
                # add file to manifest
                this_resource = resource(
                    os.path.relpath(src, os.path.join(mathjax_path, '..')))
                self.resources.add(this_resource)

                # must copy to the current folder, if it does not exist
                if use_local_mathjax == False:
                    #   copy mathjax to current folder.
                    local_dest = os.path.relpath(
                        src, os.path.join(mathjax_path, '..'))
                    mkdir_p(os.path.dirname(local_dest))
                    shutil.copy(src, local_dest)

        return html

    def _xhtmlNavtoNCXNav(self, element):
        '''Convert xhtml toc element to NCX nav element. Recurses through children'''
        # each <ol> contains 1 or more <li> and each <li> contains <a> and zero
        # or 1 <ol>

        navPoint = etree.fromstring(
            r'''<navPoint><navLabel><text/></navLabel><content/></navPoint>''')
        labeltext = navPoint.find('navLabel/text')
        content = navPoint.find('content')

        # create unique id for ncx navPoint elements
        i = 0
        navid = "navpoint-id-{num}".format(num=str(i))
        while navid in self.ncx_ids:
            i += 1
            navid = "navpoint-id-{num}".format(num=str(i))
        self.ncx_ids.append(navid)
        navPoint.attrib['id'] = navid

        for li in element.findall('li'):
            a = li.find('a')
            labeltext.text = a.text
            content.attrib['src'] = os.path.join(
                'xhtml', self.epubname, a.attrib['href'])
            # weird hack to stop elements from overwriting parent values. Not
            # sure why it works. O_o
            navPoint = copy.deepcopy(navPoint)
            # Recurse through children
            for ol in li.findall('ol'):
                navPoint.append(self._xhtmlNavtoNCXNav(ol))

        return navPoint

    def create_ncx(self):
        '''if the self.nav is created, also create the ncx file'''
        self.ncx_ids = []
        navmap = etree.Element("navMap")
        navOl = [ol for ol in self.nav.findall('.//body/nav/ol')]
        navpoints = [self._xhtmlNavtoNCXNav(ol) for ol in navOl]

        for np in navpoints:
            navmap.append(np)

        ncx_XML = r'''<?xml version="1.0"?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
          "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">

        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
           <head>
               <meta name="dtb:uid" content="www.siyavula.com.epubmaker.{name}"/>
               <meta name="dtb:depth" content="3"/>
               <meta name="dtb:totalPageCount" content="0"/>
               <meta name="dtb:maxPageNumber" content="0"/>
           </head>
           <docTitle>
               <text>Document Title</text>
           </docTitle>
         {navmap}
        </ncx>'''.format(navmap=etree.tostring(navmap, pretty_print=True), name=self.epubname)

        self.ncx = etree.fromstring(ncx_XML)

        # add ncx file to manifest
        manifestitem = self.create_manifest_item(
            'toc.ncx', 'application/x-dtbncx+xml')
        manifestitem.attrib['id'] = 'ncx'
        manifest = self.package.find('.//manifest')
        manifest.append(manifestitem)

    def _find_js_css_in_html(self):
        '''Find the css and javascript files linked to in the html'''
        # list containing src already included, avoid duplicates
        included_src = []
        for res in self.resources.resources:
            hf = res.src
            if (hf.endswith('.html')) or (hf.endswith('.xhtml')):

                HTML = res.HTMLObject

                for script in HTML.findall('.//script'):
                    src = script.attrib.get('src')
                    if src is not None:
                        relsrc = os.path.normpath(
                            os.path.join(os.path.dirname(hf), src))

                        if relsrc not in included_src:
                            included_src.append(relsrc)
                            scripttype = mimetypes.guess_type(src)[0]
                            jsresource = resource(relsrc)
                            self.resources.add(jsresource)

                for link in HTML.findall('.//link'):
                    src = link.attrib.get('href')
                    if src is not None:
                        relsrc = os.path.normpath(
                            os.path.join(os.path.dirname(hf), src))
                        cssresource = resource(relsrc)
                        self.resources.add(cssresource)

                        if relsrc not in included_src:
                            included_src.append(relsrc)
                            scripttype = mimetypes.guess_type(src)[0]
                            if scripttype == 'text/css':
                                css_resources = self._get_css_resources(
                                    os.path.normpath(os.path.join(os.path.dirname(hf), src)))
                                # Add css resources to the manifest
                                for cs in css_resources:
                                    cssresource = resource(cs)
                                    self.resources.add(cssresource)
                                    if cs not in included_src:
                                        cspath = os.path.normpath(
                                            os.path.join(cs))
                                        included_src.append(cspath)
                                        srctype = mimetypes.guess_type(cs)[0]
#                                       manifestitem = self.create_manifest_item(cspath, srctype)
#                                       manifest.append(manifestitem)

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

            urls = [
                os.path.normpath(os.path.join(os.path.dirname(css), url)) for url in urls]

        except IOError:
            logging.error("Cannot open file: " + css)

        return urls

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
        y, m, d, h, minute, s, t1, t2, t3 = time.localtime()
        dcmetatime = etree.fromstring(
            r'<meta property="dcterms:modified">{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z</meta>'.format(y, m, d, h, minute, s))
        package = etree.Element('package',
                                nsmap={None: "http://www.idpf.org/2007/opf"},
                                attrib={'version': '3.0', 'unique-identifier': 'uid'})
        metadata = etree.XML(r'''<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="uid">www.siyavula.com.epubmaker.{name}</dc:identifier>
        <dc:title>{name}</dc:title>
        <dc:language>en</dc:language>
        </metadata>'''.format(name=self.epubname))
        metadata.append(dcmetatime)

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

        # run through self.resources.resources and add everything to manifest
        for res in self.resources.resources:
            if '?' in res.src:
                res.src = res.src[0:res.src.index('?')]
            srctype = mimetypes.guess_type(res.src)[0]

            # can't always guess it.
            if srctype is None:
                if res.src.endswith('.eot'):
                    srctype = "application/vnd.ms-fontobject"
                elif (res.src.endswith('.ttf')) or (res.src.endswith('.otf')):
                    srctype = "application/octet-stream"
                elif res.src.endswith('.woff'):
                    srctype = "application/font-woff"
                else:
                    print "Cannot guess mimetype for ", res.src
                    print "Exiting..."
                    sys.exit(1)
            if srctype == "text/html":
                srctype = "application/xhtml+xml"

            destination = os.path.join('xhtml', self.epubname, res.src)
            res.destination = os.path.abspath(
                os.path.join(self.epub_output_folder, 'OPS', destination))
            manifestitem = self.create_manifest_item(destination, srctype)
            if 'html' in srctype:
                # add the properties="scripted" if mathjax is enabled.
                if (self.MathJax):
                    if not manifestitem.attrib.get('properties'):
                        manifestitem.attrib['properties'] = 'scripted'


            manifest.append(manifestitem)

        return

    def write(self):
        '''Write the unzipped epub to the output folder'''
        for r in self.resources.resources:
            if not os.path.exists(r.src):
                if self.verbose:
                    logging.error(
                        "{src} not found! Removing from manifest".format(src=r.src))

                # remove this resource from the manifest, this may cause other
                # trouble tho...
                for item in self.package.findall('.//manifest/item'):
                    if r.src in item.attrib['href']:
                        item.getparent().remove(item)
                        break

            # it does exist, copy it to its new location
            else:
                # check if folder exists
                if not os.path.exists(os.path.dirname(r.destination)):
                    print "Creating folder ", os.path.dirname(r.destination)
                    os.makedirs(os.path.dirname(r.destination))

                # check if resource has the .content attribute
                if hasattr(r, 'content'):
                    # write the content to that destination
                    with open(r.destination, 'w') as f:
                        if r.destination.endswith('html'):
                            f.write(etree.tostring(r.content, pretty_print=True, method='xml').replace(
                                r'<html>', r'<html xmlns="http://www.w3.org/1999/xhtml">'))
                else:
                    # copy file there
                    shutil.copy(r.src, r.destination)

        # write the nav file
        navfile_dest = os.path.abspath(os.path.join(
            self.epub_output_folder, 'OPS', 'xhtml', self.epubname, '{name}.nav.xhtml'.format(name=self.epubname)))
        with open(navfile_dest, 'w') as nf:
            nf.write(etree.tostring(self.nav, pretty_print=True, method="xml"))

        # write the ncx file
        with open(os.path.join(self.epub_output_folder, 'OPS', 'toc.ncx'), 'w') as f:
            f.write(etree.tostring(self.ncx, pretty_print=True, method='xml'))

        # now write the package file
        packagefile_dest = os.path.abspath(os.path.join(
            self.epub_output_folder, 'OPS', "{name}-package.opf".format(name=self.epubname)))
        with open(packagefile_dest, 'w') as pf:
            pf.write(etree.tostring(self.package, pretty_print=True,
                                    method='xml', encoding='utf-8', xml_declaration=True))

        # create the mimetype file
        mimetype_dest = os.path.abspath(
            os.path.join(self.epub_output_folder, 'mimetype'))
        with open(mimetype_dest, 'w') as mf:
            mf.write("application/epub+zip")

        # create the META-INF folder
        if not os.path.exists(os.path.abspath(os.path.join(self.epub_output_folder, 'META-INF'))):
            os.makedirs(
                os.path.abspath(os.path.join(self.epub_output_folder, 'META-INF')))

        # write the container file
        container_dest = os.path.abspath(
            os.path.join(self.epub_output_folder, 'META-INF', 'container.xml'))

        container = etree.XML(
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles>\n</rootfiles></container>')
        packagefilepath = "OPS/{name}-package.opf".format(name=self.epubname)

        rootfile = etree.Element('rootfile', attrib={
                                 'media-type': "application/oebps-package+xml", 'full-path': packagefilepath})
        container.find(
            './/{urn:oasis:names:tc:opendocument:xmlns:container}rootfiles').append(rootfile)

        with open(container_dest, 'w') as cf:
            cf.write(etree.tostring(container, pretty_print=True,
                                    method='xml', encoding='utf-8', xml_declaration=True))
