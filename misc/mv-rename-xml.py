import os
import sys

from lxml import etree
import shutil
#
# given a cnxmlplus file, copy it to output folder, copy their linked images to an ./images folder
# rename images and links to something unique.







if __name__ == "__main__":

    inputpath, outputpath = sys.argv[1:]

    xml = etree.XML(open(inputpath, 'r').read())

    # make the output folder if it does not exist
    if not os.path.exists(os.path.dirname(outputpath)):
        os.makedirs(os.path.dirname(outputpath))

    outputname = os.path.splitext(os.path.split(outputpath)[-1])[0] + '-'
    imagefolderpath = os.path.join(os.path.dirname(os.path.dirname(outputpath)), 'images')

    if not os.path.exists(imagefolderpath):
        os.makedirs(imagefolderpath)

    for img in xml.findall('.//image'):
        src = img.attrib.get('src')
        src_element = img.find('src')
        if src_element is not None:
            if src == src_element.text.strip():
                img.remove(src_element)
            else:
                print "WARNING duplicate img src", src, src_element.text


        imgsrc = os.path.join(os.path.dirname(inputpath), src)
        imgdest = os.path.join(os.path.dirname(outputpath), imagefolderpath, outputname + src)
        if not os.path.exists(os.path.dirname(imgdest)):
            os.makedirs(os.path.dirname(imgdest))
        shutil.copy(imgsrc, imgdest)
        img.attrib['src'] = 'images/' + outputname + src


    with open(outputpath, 'w') as f:
        f.write(etree.tostring(xml, pretty_print=True, method='xml'))
