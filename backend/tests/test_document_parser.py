import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from document_parser import (
    extract_document_text,
    extract_text_from_pdf,
    extract_text_from_docx,
    DocumentExtractionError
)

class TestDocumentParser(unittest.TestCase):

    @patch('document_parser.pdfplumber.open')
    def test_simple_pdf_extraction(self, mock_pdf_open):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF text content"
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        text = extract_document_text(b"fake_pdf_bytes", "test.pdf")
        self.assertEqual(text, "PDF text content")

    @patch('document_parser.pdfplumber.open')
    def test_multipage_pdf_extraction(self, mock_pdf_open):
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        text = extract_document_text(b"fake_pdf_bytes", "test.pdf")
        self.assertEqual(text, "Page 1\n\nPage 2")

    @patch('document_parser.pdfplumber.open')
    def test_empty_pdf_extraction(self, mock_pdf_open):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        with self.assertRaises(DocumentExtractionError) as ctx:
            extract_document_text(b"fake_pdf_bytes", "test.pdf")
        self.assertIn("No extractable text found", str(ctx.exception))

    @patch('document_parser.docx.Document')
    def test_simple_docx_extraction(self, mock_docx_doc):
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "Para 1"
        mock_para2 = MagicMock()
        mock_para2.text = "Para 2"
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.tables = []
        mock_docx_doc.return_value = mock_doc

        text = extract_document_text(b"fake_docx_bytes", "test.docx")
        self.assertEqual(text, "Para 1\n\nPara 2")

    @patch('document_parser.docx.Document')
    def test_empty_docx_extraction(self, mock_docx_doc):
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        mock_docx_doc.return_value = mock_doc

        with self.assertRaises(DocumentExtractionError):
            extract_document_text(b"fake_docx_bytes", "test.docx")

    def test_unsupported_extension(self):
        with self.assertRaises(DocumentExtractionError) as ctx:
            extract_document_text(b"data", "test.txt")
        self.assertIn("Unsupported file type", str(ctx.exception))

    def test_empty_file_bytes(self):
        with self.assertRaises(DocumentExtractionError):
            extract_document_text(b"", "test.pdf")

if __name__ == '__main__':
    unittest.main()
