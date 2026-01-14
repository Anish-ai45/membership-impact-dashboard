"""
PDF RAG Agent - Extracts text from PDF and provides RAG retrieval
"""
import os
import re
import faiss
import numpy as np
from vertexai.language_models import TextEmbeddingModel
from typing import List

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

class PDFRAGAgent:
    """Agent that extracts text from PDF and provides RAG retrieval"""
    
    def __init__(self, config, pdf_path: str = None):
        self.config = config
        if pdf_path is None:
            pdf_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Membership_Impact_Rulebook_v3_Aligned_to_BigQuery.pdf')
        self.pdf_path = pdf_path
        
        self.index_path = os.path.join(os.path.dirname(__file__), '.pdf_rag_index', 'index.faiss')
        self.chunks_path = os.path.join(os.path.dirname(__file__), '.pdf_rag_index', 'chunks.npy')
        
        # Initialize embedding model
        try:
            self.embedding_model = TextEmbeddingModel.from_pretrained("gemini-embedding-001")
        except:
            self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
        # Load or build index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            self.chunks = np.load(self.chunks_path, allow_pickle=True)
        else:
            self.build_index()
    
    def extract_text_from_pdf(self) -> str:
        """Extract text from PDF file"""
        if PdfReader is None:
            raise ImportError("pypdf or PyPDF2 is required. Install with: pip install pypdf")
        
        text = ""
        try:
            reader = PdfReader(self.pdf_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {e}")
        
        return text
    
    def build_index(self):
        """Build FAISS index from PDF text"""
        print("Building PDF RAG index...")
        
        # Extract text from PDF
        content = self.extract_text_from_pdf()
        
        # Chunk the text (by paragraphs and headings)
        # Split by double newlines (paragraphs) and headings
        chunks = re.split(r'(?=\n\n|\n#)', content)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) > 50]
        
        if not chunks:
            # Fallback: split by sentences if no paragraphs found
            sentences = re.split(r'(?<=[.!?])\s+', content)
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                current_chunk += sentence + " "
                if len(current_chunk) > 500:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        print(f"Created {len(chunks)} chunks from PDF")
        
        # Create directory if needed
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Embed chunks
        embeddings = []
        for i, chunk in enumerate(chunks):
            try:
                embedding = self.embedding_model.get_embeddings([chunk])[0].values
                embeddings.append(embedding)
            except Exception as e:
                print(f"Error embedding chunk {i}: {e}")
                continue
        
        if not embeddings:
            raise Exception("No embeddings created from PDF")
        
        embeddings = np.array(embeddings, dtype=np.float32)
        embeddings = np.ascontiguousarray(embeddings)
        
        # Build FAISS index
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        # Save index and chunks
        faiss.write_index(self.index, self.index_path)
        np.save(self.chunks_path, np.array(chunks, dtype=object))
        self.chunks = chunks
        
        print(f"PDF RAG index built with {len(chunks)} chunks")
    
    def retrieve(self, query: str, top_k: int = 4) -> List[str]:
        """Retrieve relevant chunks from PDF based on query"""
        if not hasattr(self, 'index') or not hasattr(self, 'chunks'):
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                self.chunks = np.load(self.chunks_path, allow_pickle=True)
            else:
                self.build_index()
        
        # Embed query
        query_embedding = self.embedding_model.get_embeddings([query])[0].values
        query_embedding = np.array([query_embedding], dtype=np.float32)
        query_embedding = np.ascontiguousarray(query_embedding)
        faiss.normalize_L2(query_embedding)
        
        # Search
        distances, indices = self.index.search(query_embedding, top_k)
        results = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]
        
        return results
