import gdown
import fitz
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter

class BaseEvaluationChunker:
    """
    Base class that defines the structure for our strategies.
    In the real version, this will handle fetching and parsing data.
    https://drive.google.com/file/d/1h1Yycg4xSECD259IPjBvDjBcpbKAOfNY/view?usp=sharing
    """
    def __init__(self):
        self. pdfUrl : str = "https://drive.google.com/file/d/1h1Yycg4xSECD259IPjBvDjBcpbKAOfNY/view?usp=sharing"
        self.fileName : str = "consumer_rights.pdf"

    def _fetch_and_parse_pdf(self) -> str:
        gdown.download(url = self.pdfUrl, output = self.fileName, fuzzy=True)
        print("Downloaded successfully!!")
        if not os.path.exists(self.fileName) or os.path.getsize(self.fileName) == 0:
            return "Error: Download failed, file does not exist or is empty."
        try:
            # Open the PDF file
            document = fitz.open(self.fileName)
        
            full_text = ""
            # Iterate through each page of the document
            for page_num in range(len(document)):
                page = document.load_page(page_num)
                full_text += page.get_text()
            
            return full_text
        except Exception as e:
            return f"An error occurred: {e}"

    def chunk(self, text: str) -> list[str]:
        """This method must be implemented by each new strategy."""
        raise NotImplementedError("You must implement the chunking logic in a subclass.")

    def start(self) -> list[str]:
        """The main entry point called by the API."""
        document_text = self._fetch_and_parse_pdf()
        chunks = self.chunk(document_text)
        return chunks

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

class NewRecursiveStrategy(BaseEvaluationChunker):
    def chunk(self, text: str) -> list[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=150,
            chunk_overlap=20,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        print("...")
        return chunks