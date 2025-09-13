class BaseEvaluationChunker:
    """
    Base class that defines the structure for our strategies.
    In the real version, this will handle fetching and parsing data.
    """
    def _fetch_and_parse_pdf(self) -> str:
        """
        [PLACEHOLDER] In the future, this will get data from S3.
        For now, it just returns a simple string.
        """
        print("Base class: Fetching mock data...")
        return "This is a dummy document for testing the pipeline."

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
        
        # This method ignores the input text and just returns a fixed list.
        return [
            "This is a dummy chunk 1.",
            "This is another dummy chunk from the placeholder strategy.",
            "The pipeline test is successful if you receive this data."
        ]