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

class epub:
    ''' Wrapper class for representing an epub.'''
    def __init__(self):
        self.container = []
        self.manifest = []
        self.epubversion = '3.0'

        return

    

class container:
    '''class to represent the container file'''
    def __init__(self, name=''):
        '''Initialise the container file with the name of the new module inside the epub.'''
        self.rootfiles = []
        self.rootfiles.append("EPUB/package-{name}.opf".format(name=name))


    def __str__(self):
        
        rootfiletemplate = r'<rootfile full-path="{rootfilepath}" media-type="application/oebps-package+xml"/>'
        rootfiles_as_xml = '\n'.join([rootfiles_as_xml.format(path=rf) for rf in self.rootfiles])

        template = r'''<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
   <rootfiles>
      {rootfiles}
   </rootfiles>
</container>
'''.format(rootfiles=rootfiles_as_xml)

        return template
