import gdown
import fitz

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
        gdown.download(url = self.pdfUrl, output = self.fileName)
        print("Downloaded successfully!!")
        try:
            # Open the PDF file
            document = fitz.open(self.fileName)
        
            full_text = ""
            # Iterate through each page of the document
            for page_num in range(len(document)):
                page = document.load_page(page_num)
                full_text += page.get_text()
            
            chunks = full_text.split('\n\n')
            cleaned_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            return cleaned_chunks
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
    """
    A minimal strategy that returns a fixed list of dummy chunks.
    Use this to test that the pipeline runs from end to end.
    """
    def chunk(self, text: str) -> list[str]:
        
        print("PlaceholderStrategy: Returning a hardcoded list of dummy chunks...")
        print(text)
        # This method ignores the input text and just returns a fixed list.
        return [
            "This is a dummy chunk 1.",
            "This is another dummy chunk from the placeholder strategy.",
            "The pipeline test is successful if you receive this data."
        ]