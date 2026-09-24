from backend.parsing.extractor import DocumentTextExtractor, ExtractedDocument


class OCRExtractor(DocumentTextExtractor):
    """
    OCR extension point for text extraction from images or scanned PDFs.
    This is currently a stub for a P1 extension.
    
    A full implementation would use libraries like Tesseract or AWS Textract to
    extract text from images, keeping track of page numbers and bounding boxes.
    """

    def __init__(self) -> None:
        pass

    def extract(self, file_path: str) -> ExtractedDocument:
        """
        Extracts text using OCR.
        
        Args:
            file_path: The path to the file to process.
            
        Returns:
            ExtractedDocument containing the parsed text.
            
        Raises:
            NotImplementedError: Always raised as this is a stub.
        """
        raise NotImplementedError('OCR extraction is a P1 extension point. See docs/ARCHITECTURE.md for the integration path.')

    def supports(self, file_path: str) -> bool:
        """
        Checks if this extractor supports the given file format.
        
        Args:
            file_path: The path to the file.
            
        Returns:
            bool: Always False for the stub.
        """
        return False

class OCRAvailability:
    """Utility class to check for OCR support."""

    @staticmethod
    def is_available() -> bool:
        """
        Checks if OCR capabilities are available on the system.
        
        Returns:
            bool: Always False for the stub.
        """
        return False
