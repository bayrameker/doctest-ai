import os
import logging
import tempfile
from io import StringIO
import subprocess

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_document(file_path, extract_images=False, extract_tables=False, use_llama_parse=False, use_docling=False, use_neuradoc=False, use_smart_processing=False):
    """
    Parse various document formats and extract text
    Supports: PDF, DOC, DOCX, TXT
    
    Args:
        file_path (str): Path to the document file
        extract_images (bool): Whether to extract images from the document
        extract_tables (bool): Whether to extract tables from the document
        use_llama_parse (bool): Whether to use LlamaParse for LLM-optimized parsing
        use_docling (bool): Whether to use Docling for LLM-optimized parsing
        use_neuradoc (bool): Whether to use NeuraDoc for in-house document processing
        use_smart_processing (bool): Whether to use smart document chunking for large files
        
    Returns:
        str: Extracted text from the document
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        # If NeuraParse Plus is requested (for large documents), use auto_processor.py
        if use_smart_processing:
            logger.info("NeuraParse Plus kullanılıyor: Gelişmiş akıllı belge işleme sistemi")
            try:
                from utils.auto_processor import auto_process_document
                
                # Process document with NeuraParse Plus
                logger.info(f"NeuraParse Plus belge analizi başlatılıyor: {file_path}")
                try:
                    result = auto_process_document(file_path, extract_images=extract_images, extract_tables=extract_tables)
                    if result and "text" in result and result["text"]:
                        logger.info(f"NeuraParse Plus analizi başarılı - {len(result['text'])} karakter, {len(result.get('chunks', []))} parça")
                        return result["text"]
                    else:
                        logger.warning("NeuraParse Plus boş içerik döndürdü, diğer yöntemlere geçiliyor")
                except Exception as extract_error:
                    logger.error(f"NeuraParse Plus belge işleme hatası: {str(extract_error)}")
                    # Continue to other methods
            except ImportError as import_error:
                logger.warning(f"NeuraParse Plus modülü kullanılamıyor: {str(import_error)}")
            except Exception as e:
                logger.error(f"NeuraParse Plus belge işleme hatası: {str(e)}")
                logger.info("Diğer belge işleme yöntemlerine geçiliyor")
        
        # If NeuraDoc is requested, use neuradoc.py
        if use_neuradoc:
            logger.info("Using NeuraDoc for in-house document processing")
            try:
                # Doğrudan import et
                from utils.neuradoc import extract_text, NEURADOC_AVAILABLE
                
                # İlk olarak modülün yüklenip yüklenmediğini kontrol et
                if not NEURADOC_AVAILABLE:
                    logger.warning("NeuraDoc modülü yüklenemedi, standart belge işleme kullanılıyor")
                    # ImportError kullanarak standart işleme mantığına düşmesini sağla
                    raise ImportError("NeuraDoc modülü yüklenemedi")
                
                # Use NeuraDoc to extract content
                logger.info("NeuraDoc ile içerik çıkarılıyor: " + file_path)
                try:
                    content = extract_text(file_path)
                    # İçerik boş olabilir, bu NeuraDoc'un başarısız olduğu anlamına gelir
                    if not content:
                        logger.warning("NeuraDoc boş içerik döndürdü, standart belge işleme kullanılıyor")
                    else:
                        logger.info(f"İçerik başarıyla çıkarıldı - {len(content)} karakter")
                        return content
                except Exception as extract_error:
                    logger.error(f"NeuraDoc ile içerik çıkarma hatası: {str(extract_error)}")
                    # Hatayı yükseltme, sessizce geçiş yap
            except ImportError as import_error:
                logger.warning(f"NeuraDoc modülü import hatası: {str(import_error)}")
                logger.warning("Standart belge işleme kullanılıyor")
            except Exception as e:
                logger.error(f"Error using NeuraDoc: {str(e)}")
                logger.info("Falling back to standard parsing methods")
        
        # If Docling is requested, use docling_parser.py
        if use_docling:
            logger.info("Using Docling for LLM-optimized document parsing")
            try:
                # Doğrudan import et
                from utils.docling_parser import extract_docling_content, is_docling_available, LITE_DOCLING_AVAILABLE
                
                # İlk olarak modülün yüklenip yüklenmediğini kontrol et
                if not LITE_DOCLING_AVAILABLE:
                    logger.warning("Docling modülleri yüklenemedi, standart belge işleme kullanılıyor")
                    # ImportError kullanarak standart işleme mantığına düşmesini sağla
                    raise ImportError("Docling modülleri yüklenemedi")
                
                # Docling kullanılabilir mi kontrol et
                if not is_docling_available():
                    logger.warning("Docling kullanılamıyor, standart belge işleme kullanılıyor")
                else:
                    # Use Docling to extract content
                    logger.info("Docling ile içerik çıkarılıyor: " + file_path)
                    try:
                        content = extract_docling_content(file_path)
                        # İçerik boş olabilir, bu Docling'in başarısız olduğu anlamına gelir
                        if not content:
                            logger.warning("Docling boş içerik döndürdü, standart belge işleme kullanılıyor")
                        else:
                            logger.info(f"İçerik başarıyla çıkarıldı - {len(content)} karakter")
                            return content
                    except Exception as extract_error:
                        logger.error(f"Docling ile içerik çıkarma hatası: {str(extract_error)}")
                        # Hatayı yükseltme, sessizce geçiş yap
            except ImportError as import_error:
                logger.warning(f"Docling modülü import hatası: {str(import_error)}")
                logger.warning("Standart belge işleme kullanılıyor")
            except Exception as e:
                logger.error(f"Error using Docling: {str(e)}")
                logger.info("Falling back to standard parsing methods")
                
        # If LlamaParse is requested, use llama_parser.py
        if use_llama_parse:
            logger.info("Using LlamaParse for LLM-optimized document parsing")
            try:
                # Doğrudan import et
                from utils.llama_parser import extract_llama_content, is_llama_parse_available, LLAMA_PARSE_AVAILABLE
                
                # İlk olarak modülün yüklenip yüklenmediğini kontrol et
                if not LLAMA_PARSE_AVAILABLE:
                    logger.warning("LlamaParse modülleri yüklenemedi, standart belge işleme kullanılıyor")
                    # ImportError kullanarak standart işleme mantığına düşmesini sağla
                    raise ImportError("LlamaParse modülleri yüklenemedi")
                
                # Sonra API anahtarı ve diğer gereksinimlerin sağlanıp sağlanmadığını kontrol et
                if not is_llama_parse_available():
                    logger.warning("LlamaParse API anahtarı bulunamadı, standart belge işleme kullanılıyor")
                else:
                    # Use LlamaParse to extract content
                    logger.info("LlamaParse ile içerik çıkarılıyor: " + file_path)
                    try:
                        content = extract_llama_content(file_path)
                        # İçerik boş olabilir, bu LlamaParse'ın başarısız olduğu anlamına gelir
                        if not content:
                            logger.warning("LlamaParse boş içerik döndürdü, standart belge işleme kullanılıyor")
                        else:
                            logger.info(f"İçerik başarıyla çıkarıldı - {len(content)} karakter")
                            return content
                    except Exception as extract_error:
                        logger.error(f"LlamaParse ile içerik çıkarma hatası: {str(extract_error)}")
                        # Hatayı yükseltme, sessizce geçiş yap
            except ImportError as import_error:
                logger.warning(f"LlamaParse modülü import hatası: {str(import_error)}")
                logger.warning("Standart belge işleme kullanılıyor")
            except Exception as e:
                logger.error(f"Error using LlamaParse: {str(e)}")
                logger.info("Falling back to standard parsing methods")
        
        # If enhanced analysis is requested, use document_analyzer.py
        if extract_images or extract_tables:
            logger.info("Using enhanced document analysis for rich content extraction")
            try:
                from utils.document_analyzer import analyze_document
                # Pass the parser preference flags
                doc_content = analyze_document(
                    file_path,
                    force_neuradoc=use_neuradoc,
                    force_docling=use_docling,
                    force_llama_parse=use_llama_parse
                )
                # Log which parser was actually used if available from metadata
                parser_used = "unknown"
                if hasattr(doc_content, "metadata") and "parser_used" in doc_content.metadata:
                    parser_used = doc_content.metadata.get("parser_used", "unknown")
                    logger.info(f"Document analyzed with parser: {parser_used}")
                
                return doc_content.get_plain_text()
            except ImportError:
                logger.warning("Enhanced document analyzer not available, falling back to text extraction")
            except Exception as e:
                logger.error(f"Error in enhanced document analysis: {str(e)}")
                logger.info("Falling back to text-only extraction")
        
        # Standard text extraction
        if file_extension == '.pdf':
            return parse_pdf(file_path)
        elif file_extension in ['.doc', '.docx']:
            return parse_word(file_path)
        elif file_extension == '.txt':
            return parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise

def parse_pdf(file_path):
    """
    Extract text from PDF files using PyPDF2
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text
    """
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n"
                
        if not text.strip():
            # If PyPDF2 failed to extract text, try textract as fallback
            return extract_with_textract(file_path)
            
        return text
    except ImportError:
        # If PyPDF2 is not available, use textract
        logger.warning("PyPDF2 not available, falling back to textract")
        return extract_with_textract(file_path)
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        # Try textract as fallback
        try:
            return extract_with_textract(file_path)
        except Exception as e2:
            logger.error(f"Textract fallback also failed: {str(e2)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

def parse_word(file_path):
    """
    Extract text from Word documents
    
    Args:
        file_path (str): Path to the DOC/DOCX file
        
    Returns:
        str: Extracted text
    """
    try:
        # First try with python-docx for DOCX
        if file_path.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx not available, trying textract")
                pass
        
        # Fallback to textract (works for both DOC and DOCX)
        return extract_with_textract(file_path)
    except Exception as e:
        logger.error(f"Error parsing Word document: {str(e)}")
        raise

def parse_text(file_path):
    """
    Read text files directly
    
    Args:
        file_path (str): Path to the text file
        
    Returns:
        str: File contents
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # Try different encodings if utf-8 fails
        encodings = ['latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        
        raise Exception("Could not decode text file with any supported encoding")

def extract_with_textract(file_path):
    """
    Extract text using textract as a fallback method
    
    Args:
        file_path (str): Path to the document file
        
    Returns:
        str: Extracted text
    """
    try:
        import textract
        text = textract.process(file_path).decode('utf-8')
        return text
    except ImportError:
        # If textract is not available, try basic command-line tools
        logger.warning("Textract not available, trying command-line tools")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            try:
                # Try using pdftotext if available
                output = subprocess.check_output(['pdftotext', file_path, '-'], stderr=subprocess.PIPE)
                return output.decode('utf-8', errors='replace')
            except (subprocess.SubprocessError, FileNotFoundError):
                raise Exception("Failed to extract text from PDF. Required tools not available.")
                
        elif file_extension in ['.doc', '.docx']:
            try:
                # Try using antiword or catdoc for doc files
                if file_extension == '.doc':
                    try:
                        output = subprocess.check_output(['antiword', file_path], stderr=subprocess.PIPE)
                        return output.decode('utf-8', errors='replace')
                    except (subprocess.SubprocessError, FileNotFoundError):
                        try:
                            output = subprocess.check_output(['catdoc', file_path], stderr=subprocess.PIPE)
                            return output.decode('utf-8', errors='replace')
                        except (subprocess.SubprocessError, FileNotFoundError):
                            pass
                            
                # Try using unzip and grep for docx files
                if file_extension == '.docx':
                    temp_dir = tempfile.mkdtemp()
                    try:
                        subprocess.check_call(['unzip', '-q', '-o', file_path, '*.xml', '-d', temp_dir])
                        
                        # Extract text from document.xml
                        try:
                            document_xml = os.path.join(temp_dir, 'word', 'document.xml')
                            if os.path.exists(document_xml):
                                with open(document_xml, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Very basic XML parsing to extract text
                                    import re
                                    text_parts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', content)
                                    return ' '.join(text_parts)
                        except Exception:
                            pass
                    finally:
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
                
        raise Exception(f"Failed to extract text from {file_extension} file. Required tools not available.")
