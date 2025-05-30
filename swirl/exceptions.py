class  RagError(Exception):
    """Exception raised for errors related to RAG."""
    def __init__(self, message="Error with RAG"):
        self.message = message
        super().__init__(self.message)
