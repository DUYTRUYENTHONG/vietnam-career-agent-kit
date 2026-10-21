from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.rendering import build_docx, preview_pdf


class PreviewTests(unittest.TestCase):
    def test_docx_has_no_inherited_title_or_paragraph_border(self):
        from zipfile import ZipFile
        from lxml import etree
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'cv.docx'
            build_docx({'name':'Fictional Candidate','headline':'Target role Analyst',
                'contacts':[],'section':'Capabilities','claims':['Classroom SQL project.']},path)
            with ZipFile(path) as archive:
                for part in ['word/styles.xml','word/document.xml']:
                    root=etree.fromstring(archive.read(part))
                    self.assertEqual([],root.xpath('//*[local-name()="pBdr"]'))

    def test_real_pdfium_pages_are_closed_without_assuming_context_manager_support(self):
        from pypdf import PdfWriter
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'test.pdf'
            writer=PdfWriter()
            for _ in range(2):writer.add_blank_page(width=595,height=842)
            with path.open('wb') as stream:writer.write(stream)
            preview_pdf(path,root,2)
            for page in [1,2]:
                with Image.open(root/f'page-{page:03}.png') as picture:
                    self.assertEqual((1190,1684),picture.size)
            path.unlink()  # Open native document handles must not prevent removal on Windows.
