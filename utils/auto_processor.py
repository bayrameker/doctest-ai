"""
NeuraParse Plus: Gelişmiş Akıllı Belge İşleme Modülü

Bu modül, yapay zeka destekli otomatik belge türü tespiti ve en uygun işleme stratejisi seçimi sağlar.
Belge boyutu, türü ve kullanılabilir sistem kaynaklarına göre en optimum belge işleme yöntemini seçer.
Büyük ve karmaşık belgeleri verimli bir şekilde işlemek için tasarlanmıştır.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, Union, Optional, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependent modules dynamically
def import_document_chunker():
    try:
        from utils.document_chunker import DocumentChunker, chunk_document_text
        return DocumentChunker, chunk_document_text
    except ImportError:
        logger.warning("Document chunker not available")
        return None, None

def import_smart_processor():
    try:
        from utils.smart_document_processor import SmartDocumentProcessor, smart_process_document
        return SmartDocumentProcessor, smart_process_document
    except ImportError:
        logger.warning("Smart document processor not available")
        return None, None

# Constants for document size thresholds
SMALL_DOCUMENT_THRESHOLD = 1 * 1024 * 1024  # 1MB
MEDIUM_DOCUMENT_THRESHOLD = 10 * 1024 * 1024  # 10MB
LARGE_DOCUMENT_THRESHOLD = 50 * 1024 * 1024  # 50MB

# NeuraParse Plus işleme stratejileri
PROCESSING_STRATEGIES = {
    "small": {
        "description": "Küçük belgeler için standart NeuraParse işlemi",
        "chunking": False,
        "streaming": False,
        "extract_images": True,
        "extract_tables": True,
        "content_analysis": True,
        "semantic_structure": True
    },
    "medium": {
        "description": "Orta boyuttaki belgeler için akıllı parçalama ve paralelleştirme",
        "chunking": True,
        "streaming": False,
        "extract_images": True,
        "extract_tables": True,
        "content_analysis": True,
        "semantic_structure": True,
        "parallel_processing": True
    },
    "large": {
        "description": "Büyük belgeler için bellek-verimli akış işleme teknolojisi",
        "chunking": True,
        "streaming": True,
        "extract_images": False,  # Büyük dosyalarda belleği korumak için varsayılan olarak kapalı
        "extract_tables": False,  # Büyük dosyalarda belleği korumak için varsayılan olarak kapalı
        "content_analysis": True,
        "semantic_structure": True,
        "parallel_processing": True,
        "memory_optimization": True
    },
    "huge": {
        "description": "Çok büyük belgeler için ultra-verimli yapay zeka destekli işleme",
        "chunking": True,
        "streaming": True,
        "extract_images": False,
        "extract_tables": False,
        "process_subset": True,  # Belgenin sadece bir alt kümesini işle
        "content_analysis": True,
        "semantic_structure": False,  # Bellek tasarrufu için kapandı
        "parallel_processing": True,
        "memory_optimization": True,
        "progressive_loading": True
    }
}

class NeuraParsePlus:
    """
    NeuraParse Plus: Gelişmiş Akıllı Belge İşleme Motoru
    
    Belgenin yapısına ve boyutuna göre en uygun işleme stratejisini otomatik seçer.
    Büyük ve karmaşık belgeleri bile verimli bir şekilde işleyebilir.
    Yapay zeka destekli belge analiz ve yapılandırma özellikleri içerir.
    """
    
    def __init__(self, always_use_smart_processing: bool = False):
        """
        Initialize the auto processor.
        
        Args:
            always_use_smart_processing: Whether to always use smart processing regardless of document size
        """
        self.always_use_smart_processing = always_use_smart_processing
        
        # Try to import needed modules
        self.DocumentChunker, self.chunk_document_text = import_document_chunker()
        self.SmartDocumentProcessor, self.smart_process_document = import_smart_processor()
        
        logger.info(f"NeuraParse Plus başlatıldı (akıllı_işleme_her_zaman={always_use_smart_processing})")
    
    def detect_document_size_category(self, file_path: Union[str, Path]) -> str:
        """
        Detect document size category.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Size category: "small", "medium", "large", or "huge"
        """
        file_size = os.path.getsize(file_path)
        
        if file_size < SMALL_DOCUMENT_THRESHOLD:
            return "small"
        elif file_size < MEDIUM_DOCUMENT_THRESHOLD:
            return "medium"
        elif file_size < LARGE_DOCUMENT_THRESHOLD:
            return "large"
        else:
            return "huge"
    
    def select_processing_strategy(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Select the optimal processing strategy based on document properties.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Processing strategy configuration
        """
        # If smart processing is always enabled, use medium strategy at minimum
        if self.always_use_smart_processing:
            size_category = self.detect_document_size_category(file_path)
            if size_category == "small":
                size_category = "medium"
        else:
            size_category = self.detect_document_size_category(file_path)
        
        # Get strategy from size category
        strategy = PROCESSING_STRATEGIES[size_category].copy()
        
        # Add metadata to strategy
        strategy["size_category"] = size_category
        strategy["file_size"] = os.path.getsize(file_path)
        strategy["file_extension"] = os.path.splitext(file_path)[1].lower()
        
        logger.info(f"Selected processing strategy '{size_category}' for {file_path} ({strategy['file_size']} bytes)")
        return strategy
    
    def process_document(self, file_path: Union[str, Path], 
                        extract_images: Optional[bool] = None,
                        extract_tables: Optional[bool] = None) -> Dict[str, Any]:
        """
        Process document using the optimal strategy.
        
        Args:
            file_path: Path to the document file
            extract_images: Override strategy's image extraction setting
            extract_tables: Override strategy's table extraction setting
            
        Returns:
            Processing results
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        # Select strategy
        strategy = self.select_processing_strategy(file_path)
        
        # Override strategy settings if specified
        if extract_images is not None:
            strategy["extract_images"] = extract_images
        
        if extract_tables is not None:
            strategy["extract_tables"] = extract_tables
        
        # Initialize result with basic file info
        result = {
            "filename": file_path.name,
            "file_type": file_path.suffix.lower().replace('.', ''),
            "file_size": strategy["file_size"],
            "size_category": strategy["size_category"],
            "processing_strategy": strategy["description"],
            "processing_time": 0,
            "text": "",
            "chunks": [],
            "processing_method": "standard"
        }
        
        try:
            # Use smart processor for medium and larger documents
            if strategy["size_category"] in ["medium", "large", "huge"]:
                if self.smart_process_document:
                    logger.info(f"NeuraParse Plus akıllı belge işleme kullanılıyor: {file_path.name}")
                    smart_result = self.smart_process_document(
                        file_path, 
                        extract_images=strategy["extract_images"],
                        extract_tables=strategy["extract_tables"]
                    )
                    
                    # Merge results
                    result.update(smart_result)
                    result["processing_method"] = "smart"
                else:
                    logger.warning("Smart processor not available, falling back to standard processing")
                    # Fall back to standard processing via document_parser.py
                    from utils.document_parser import parse_document
                    result["text"] = parse_document(
                        str(file_path),
                        extract_images=strategy["extract_images"],
                        extract_tables=strategy["extract_tables"]
                    )
                    result["processing_method"] = "standard"
                    
                    # Apply chunking if needed and available
                    if strategy["chunking"] and self.chunk_document_text:
                        result["chunks"] = self.chunk_document_text(result["text"])
            else:
                # Standard processing for small documents
                from utils.document_parser import parse_document
                result["text"] = parse_document(
                    str(file_path),
                    extract_images=strategy["extract_images"],
                    extract_tables=strategy["extract_tables"]
                )
                result["processing_method"] = "standard"
            
            # Calculate processing time
            result["processing_time"] = time.time() - start_time
            
            logger.info(f"Document processed successfully in {result['processing_time']:.2f} seconds")
            return result
            
        except Exception as e:
            # Log error and return partial results with error info
            logger.error(f"Error in auto processing document: {str(e)}")
            result["error"] = str(e)
            result["processing_time"] = time.time() - start_time
            return result


def auto_process_document(file_path: Union[str, Path], 
                        extract_images: Optional[bool] = None,
                        extract_tables: Optional[bool] = None) -> Dict[str, Any]:
    """
    NeuraParse Plus ile belge işleme fonksiyonu.
    
    Args:
        file_path: Belge dosyasının yolu
        extract_images: Görüntü çıkarma ayarını geçersiz kıl
        extract_tables: Tablo çıkarma ayarını geçersiz kıl
        
    Returns:
        İşleme sonuçları (metin, yapı, çıkarılan öğeler vb.)
    """
    processor = NeuraParsePlus()
    return processor.process_document(file_path, extract_images, extract_tables)


def is_large_document(file_path: Union[str, Path]) -> bool:
    """
    Check if a document is considered large.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        True if document is large
    """
    file_size = os.path.getsize(file_path)
    return file_size >= MEDIUM_DOCUMENT_THRESHOLD