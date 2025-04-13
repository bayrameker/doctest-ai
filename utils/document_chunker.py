"""
Smart document chunker module for processing large documents efficiently.
This module provides utilities to split large documents into manageable chunks
while preserving the semantic meaning and structure.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for chunking
DEFAULT_CHUNK_SIZE = 5000  # Default characters per chunk
DEFAULT_CHUNK_OVERLAP = 200  # Default overlap between chunks
MAX_TOKENS_PER_CHUNK = 4000  # Maximum tokens per chunk (for AI models)

class DocumentChunker:
    """
    Smart document chunker that preserves document structure and semantic meaning
    when splitting large documents for processing.
    """
    
    def __init__(self, 
                 chunk_size: int = DEFAULT_CHUNK_SIZE, 
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
                 respect_sections: bool = True,
                 respect_paragraphs: bool = True):
        """
        Initialize the document chunker with custom parameters.
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            respect_sections: Whether to try to keep sections together
            respect_paragraphs: Whether to try to keep paragraphs together
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sections = respect_sections
        self.respect_paragraphs = respect_paragraphs
        logger.info(f"Initialized DocumentChunker with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count based on character count (rough estimate).
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 4 characters per token for most languages
        return len(text) // 4
    
    def identify_sections(self, text: str) -> List[Tuple[int, int, int]]:
        """
        Identify section boundaries in the document.
        
        Args:
            text: Document text
            
        Returns:
            List of (start_index, end_index, section_level) tuples
        """
        # Pattern for section headers (detects headings of different levels)
        section_patterns = [
            # Markdown headings
            r"#{1,6}\s+.+?(?:\n|$)",
            # Numbered sections (like 1.2.3)
            r"^\d+(\.\d+)*\s+.+?(?:\n|$)",
            # Headings with underlines
            r"^.+?\n[=\-]+(?:\n|$)",
            # Capitalized headings
            r"^[A-Z][A-Z\s]+:?(?:\n|$)"
        ]
        
        sections = []
        for pattern in section_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                level = 1  # Default level
                # Determine heading level by the number of # for markdown
                if match.group().startswith('#'):
                    level = match.group().count('#')
                # Add section boundary (start, end, level)
                sections.append((match.start(), match.end(), level))
        
        # Sort sections by start position
        return sorted(sections, key=lambda x: x[0])
    
    def identify_paragraphs(self, text: str) -> List[Tuple[int, int]]:
        """
        Identify paragraph boundaries in the document.
        
        Args:
            text: Document text
            
        Returns:
            List of (start_index, end_index) tuples
        """
        paragraphs = []
        
        # Define paragraph as text separated by one or more blank lines
        paragraph_pattern = r"(?<=\n\n|\n\s*\n|\A)(.+?)(?=\n\n|\n\s*\n|\Z)"
        
        for match in re.finditer(paragraph_pattern, text, re.DOTALL):
            paragraphs.append((match.start(), match.end()))
        
        return paragraphs
    
    def chunk_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split document into semantic chunks.
        
        Args:
            text: Document text to chunk
            metadata: Optional metadata to include with each chunk
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text:
            logger.warning("Empty document text provided for chunking")
            return []
        
        chunks = []
        text_length = len(text)
        
        # If text is smaller than chunk size, return as is
        if text_length <= self.chunk_size:
            logger.info(f"Document smaller than chunk size ({text_length} <= {self.chunk_size}), returning as single chunk")
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_index": 0,
                "total_chunks": 1,
                "chunk_start": 0,
                "chunk_end": text_length,
                "is_first_chunk": True,
                "is_last_chunk": True
            })
            chunks.append({
                "text": text,
                "metadata": chunk_metadata
            })
            return chunks
        
        # Get document structure for smart chunking
        sections = self.identify_sections(text) if self.respect_sections else []
        paragraphs = self.identify_paragraphs(text) if self.respect_paragraphs else []
        
        # Start chunking
        chunk_start = 0
        chunk_index = 0
        
        while chunk_start < text_length:
            chunk_end = min(chunk_start + self.chunk_size, text_length)
            
            # Try to end at a section boundary if possible
            if self.respect_sections:
                for section_start, section_end, _ in sections:
                    if chunk_start < section_start < chunk_end and chunk_end < text_length:
                        # End chunk at section start to keep sections together
                        chunk_end = section_start
                        break
            
            # Otherwise try to end at a paragraph boundary
            if self.respect_paragraphs and chunk_end < text_length:
                # Find the last paragraph that ends before the chunk end
                last_para_end = 0
                for para_start, para_end in paragraphs:
                    if chunk_start < para_end <= chunk_end:
                        last_para_end = para_end
                
                # If found a paragraph boundary, use it
                if last_para_end > 0:
                    chunk_end = last_para_end
            
            # At minimum, end at a sentence boundary if possible
            if chunk_end < text_length:
                # Look for sentence-ending punctuation followed by whitespace
                sentence_end_pattern = r"[.!?]\s"
                last_sentence_end = 0
                
                # Search for the last sentence boundary in the potential chunk
                for match in re.finditer(sentence_end_pattern, text[chunk_start:chunk_end]):
                    last_sentence_end = match.end() + chunk_start
                
                # If found a sentence boundary, use it
                if last_sentence_end > 0:
                    chunk_end = last_sentence_end
            
            # Extract chunk text
            chunk_text = text[chunk_start:chunk_end]
            
            # Prepare chunk metadata
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_index": chunk_index,
                "chunk_start": chunk_start,
                "chunk_end": chunk_end,
                "is_first_chunk": chunk_index == 0,
                "is_last_chunk": chunk_end >= text_length
            })
            
            # Add chunk
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            
            # Move to next chunk with overlap
            chunk_start = chunk_end - self.chunk_overlap
            chunk_index += 1
            
            # Make sure we're not stuck in an infinite loop
            if chunk_start >= chunk_end:
                break
        
        # Update total chunks info
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = total_chunks
        
        logger.info(f"Document chunked into {total_chunks} chunks (original size: {text_length} chars)")
        return chunks
    
    def chunk_for_model(self, text: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> List[str]:
        """
        Chunk text specifically for AI model processing.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk for the AI model
            
        Returns:
            List of text chunks
        """
        # Estimate chunk size based on token limit (with 20% margin)
        approximate_chars = max_tokens * 4 * 0.8
        
        # Use the chunker with adjusted parameters
        chunker = DocumentChunker(
            chunk_size=int(approximate_chars),
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            respect_sections=True,
            respect_paragraphs=True
        )
        
        # Get chunks
        chunks = chunker.chunk_document(text)
        
        # Return just the text
        return [chunk["text"] for chunk in chunks]
    
    @staticmethod
    def generate_document_map(text: str) -> Dict[str, Any]:
        """
        Generate a map of document structure for easier navigation.
        
        Args:
            text: Document text
            
        Returns:
            Document structure map
        """
        # Initialize document map
        doc_map = {
            "sections": [],
            "paragraphs": 0,
            "sentences": 0,
            "total_length": len(text),
            "estimated_tokens": len(text) // 4
        }
        
        # Count paragraphs
        paragraphs = re.split(r"\n\n|\n\s*\n", text)
        doc_map["paragraphs"] = len(paragraphs)
        
        # Count sentences (approximate)
        sentences = re.split(r"[.!?]\s+", text)
        doc_map["sentences"] = len(sentences)
        
        # Extract section structure
        section_pattern = r"(#{1,6})\s+(.+?)(?:\n|$)"
        for match in re.finditer(section_pattern, text, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            position = match.start()
            doc_map["sections"].append({
                "level": level,
                "title": title,
                "position": position
            })
        
        return doc_map


def chunk_document_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, 
                      chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk document text.
    
    Args:
        text: Document text
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries
    """
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_document(text)


def chunk_for_ai_model(text: str, model_name: str = "gpt-4o") -> List[str]:
    """
    Chunk document for specific AI model.
    
    Args:
        text: Document text
        model_name: Name of the AI model
        
    Returns:
        List of chunks suitable for the specified model
    """
    # Define token limits for different models
    model_token_limits = {
        "gpt-4o": 8000,
        "gpt-4o-mini": 4000,
        "gpt-3.5-turbo": 4000,
        "ollama": 4000,
        "deepseek": 4000,
        "default": 4000
    }
    
    # Get token limit for the specified model
    max_tokens = model_token_limits.get(model_name.lower(), model_token_limits["default"])
    
    # Create chunker
    chunker = DocumentChunker()
    
    # Return chunks suitable for the model
    return chunker.chunk_for_model(text, max_tokens=max_tokens)