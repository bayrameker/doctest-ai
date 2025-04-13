"""
LLM Ready doküman parser modülü.
Bu modül, llama-parse kütüphanesini kullanarak dokümanları LLM'ler için 
optimize edilmiş şekilde parse etmeyi sağlar.
"""
import os
import logging
import json
import tempfile
import importlib.util
import sys
from typing import Dict, List, Any, Optional, Union, TypeVar

# Define a type variable for LlamaParse to avoid LSP errors
LlamaParseType = TypeVar('LlamaParseType')
LlamaDocumentType = TypeVar('LlamaDocumentType')

# Llama parse modüllerini daha güvenilir şekilde import edelim
LLAMA_PARSE_AVAILABLE = False

# Önce paketlerin yüklü olup olmadığını kontrol edelim
llama_parse_spec = importlib.util.find_spec("llama_parse")
llama_cloud_spec = importlib.util.find_spec("llama_cloud")

if llama_parse_spec is not None and llama_cloud_spec is not None:
    try:
        from llama_parse import LlamaParse
        # İnceleme sonrası doğru import yolu
        from llama_cloud.types.cloud_document import CloudDocument as LlamaDocument
        LLAMA_PARSE_AVAILABLE = True
        print("LlamaParse ve LlamaCloud başarıyla import edildi.")
    except (ImportError, ModuleNotFoundError) as e:
        print(f"LlamaParse modülleri yüklenemedi: {str(e)}")
        LLAMA_PARSE_AVAILABLE = False
        # Define dummy classes to avoid LSP errors
        class LlamaParse:
            pass
        class LlamaDocument:
            pass
else:
    print("LlamaParse ve/veya LlamaCloud modülleri sistemde bulunamadı.")
    # Define dummy classes to avoid LSP errors
    class LlamaParse:
        pass
    class LlamaDocument:
        pass

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Default API key environment variable
LLAMA_CLOUD_API_KEY_ENV = "LLAMA_CLOUD_API_KEY"
LLAMA_API_KEY = None  # Global değişken olarak API anahtarını saklayacağız

def setup_llama_parser() -> Optional[Any]:
    """
    LlamaParse nesnesini oluşturur ve yapılandırır
    
    Returns:
        Optional[Any]: Yapılandırılmış LlamaParse nesnesi veya API anahtarı/modül yoksa None
    """
    # Modülün kullanılabilir olup olmadığını kontrol et
    if not LLAMA_PARSE_AVAILABLE:
        logger.warning("LlamaParse modülü kullanılamıyor, kurulumu kontrol edin.")
        return None
    
    # Önce global API anahtarını kontrol et
    global LLAMA_API_KEY
    api_key = LLAMA_API_KEY
    
    # Global API anahtarı yoksa ortam değişkenini kontrol et
    if not api_key:
        api_key = os.environ.get(LLAMA_CLOUD_API_KEY_ENV)
    
    if not api_key:
        logger.warning("LlamaParse API anahtarı bulunamadı. API anahtarını ayarlayın.")
        return None
    
    try:
        # LlamaParse'i başlat (LLAMA_PARSE_AVAILABLE=True olduğu için import güvenli)
        # Farklı yapıcı parametreleri dene
        parser = None
        
        try:
            # Mümkün olan tüm parametre kombinasyonlarını dene
            # 1. Temel yapıcı parametreleri
            parser = LlamaParse(api_key=api_key)
            logger.info("LlamaParse basit yapıcı ile başarıyla başlatıldı.")
        except Exception as e1:
            logger.warning(f"Basit yapıcı başarısız oldu, alternatif denenecek: {str(e1)}")
            try:
                # 2. İkinci alternatif: result_type parametresi ile
                parser = LlamaParse(api_key=api_key, result_type="markdown")
                logger.info("LlamaParse result_type parametresi ile başarıyla başlatıldı.")
            except Exception as e2:
                logger.warning(f"İkinci alternatif başarısız oldu: {str(e2)}")
                try:
                    # 3. Üçüncü alternatif: verbose paramtresi ile
                    parser = LlamaParse(api_key=api_key, verbose=True)
                    logger.info("LlamaParse verbose parametresi ile başarıyla başlatıldı.")
                except Exception as e3:
                    logger.warning(f"Üçüncü alternatif başarısız oldu: {str(e3)}")
                    # Son çare: direkt LlamaParse sınıfını kullan
                    parser = LlamaParse()
                    # API anahtarını ayrıca set et
                    if hasattr(parser, 'set_api_key'):
                        parser.set_api_key(api_key)
                        logger.info("API anahtarı set_api_key metodu ile ayarlandı.")
        
        if parser is None:
            raise ValueError("Hiçbir LlamaParse yapıcı yöntemi çalışmadı.")
            
        # Parser'ın mevcut metotlarını kontrol et ve log'la
        parser_methods = dir(parser)
        logger.info(f"LlamaParse parser metotları: {parser_methods}")
        
        return parser
    except Exception as e:
        logger.error(f"LlamaParse kurulumu sırasında hata: {str(e)}")
        return None

def parse_with_llama(file_path: str) -> Dict[str, Any]:
    """
    Bir dokümanı LlamaParse ile parse eder ve yapılandırılmış veri döndürür
    
    Args:
        file_path (str): Doküman dosyasının yolağı
        
    Returns:
        dict: Doküman içeriği ve yapısı veya hata durumunda temel yapı
    """
    parser = setup_llama_parser()
    
    if not parser:
        logger.warning("LlamaParse kullanılamıyor veya API anahtarı geçersiz, basit yapı döndürülüyor.")
        # API anahtarı olmadan da çalışmaya devam et, temel yapıyı döndür
        return {
            "content": "",
            "metadata": {"error": "LlamaParse API anahtarı bulunamadı veya geçersiz."},
            "elements": [],
            "llama_parse_failed": True
        }
    
    try:
        # Dosyayı parse et - Güncel LlamaParse API'sındaki doğru metot adı
        # Önce parser nesnesindeki mevcut metotları kontrol edelim
        parser_methods = dir(parser)
        logger.info(f"Mevcut LlamaParse metotları: {parser_methods}")
        
        # Önce dosya tipini kontrol edelim
        file_ext = os.path.splitext(file_path)[1].lower()
        is_binary = file_ext in ['.pdf', '.docx', '.doc', '.pptx', '.xlsx', '.xls']
        
        # Binary dosyalar için dosyayı açarak parametre olarak geçirelim
        if is_binary:
            logger.info(f"Binary dosya formatı tespit edildi: {file_ext}")
            
            try:
                # Geçici bir dosya oluşturup, LlamaParse API'sine bir dosya yolu olarak verelim
                import tempfile
                import shutil
                
                # Dosyanın tam adını alıp geçici bir dosya oluşturalım
                file_basename = os.path.basename(file_path)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    temp_path = temp_file.name
                    # Orijinal dosyayı geçici dosyaya kopyalayalım
                    shutil.copy2(file_path, temp_path)
                    logger.info(f"Dosya geçici konuma kopyalandı: {temp_path}")
                
                try:
                    # parse_document metodlarını deneyelim
                    logger.info(f"Geçici dosya yolu kullanılıyor: {temp_path}")
                    
                    if hasattr(parser, 'parse_document'):
                        logger.info("parse_document metodu kullanılıyor...")
                        document = parser.parse_document(temp_path)
                    elif hasattr(parser, 'parse_file'):
                        logger.info("parse_file metodu kullanılıyor...")
                        document = parser.parse_file(temp_path)
                    elif hasattr(parser, 'parse'):
                        logger.info("parse metodu kullanılıyor...")
                        document = parser.parse(temp_path)
                    else:
                        logger.warning("Hiçbir parse_document veya parse_file metodu bulunamadı")
                        raise ValueError("Uygun parse metodu bulunamadı")
                        
                finally:
                    # Geçici dosyayı temizleyelim
                    try:
                        os.unlink(temp_path)
                        logger.info(f"Geçici dosya silindi: {temp_path}")
                    except Exception as cleanup_err:
                        logger.warning(f"Geçici dosya silinirken hata: {str(cleanup_err)}")
                
            except Exception as binary_err:
                logger.error(f"Binary dosya işleme hatası: {str(binary_err)}")
                # Hata durumunda normal Parser'ı kullanmaya devam edelim, bu hatayı görmezden gelerek
                logger.warning("LlamaParse işlemi başarısız, normal document parser'a geçiliyor...")
                return {
                    "content": "LlamaParse ile ayrıştırma başarısız oldu. Normal document parser kullanılıyor.",
                    "metadata": {"error": str(binary_err)},
                    "elements": [],
                    "llama_parse_failed": True
                }
        else:
            # Text dosyaları için standart metotlar
            logger.info(f"Metin dosyası formatı tespit edildi: {file_ext}")
            # Yaygın kullanılan metot adlarını deneyelim
            if hasattr(parser, 'parse_document'):
                document = parser.parse_document(file_path)
            elif hasattr(parser, 'parse_file'):
                document = parser.parse_file(file_path)
            elif hasattr(parser, 'parse'):
                document = parser.parse(file_path)
            else:
                # Doğrudan parse_file metodunu varsayılan olarak deneyelim
                try:
                    document = parser.parse_file(file_path)
                except Exception as method_err:
                    logger.error(f"Metot bulunamadı ve alternatif denemeler başarısız oldu: {str(method_err)}")
                    raise ValueError(f"LlamaParse API'sinde belge işleme metodu bulunamadı. Mevcut metotlar: {parser_methods}")
        
        # Sonuçları yapılandırılmış formatta döndür
        result = {
            "content": getattr(document, "text", ""),
            "metadata": getattr(document, "metadata", {}),
            "elements": []
        }
        
        # Document içeriğini kontrol edelim
        logger.info(f"Document özellikleri: {dir(document)}")
        
        # Elements formatı seçildiyse, elementleri de ekle
        if hasattr(document, 'elements') and document.elements:
            result["elements"] = document.elements
            
        # Tablolar ve görsel içerikleri ekle
        if hasattr(document, 'tables') and document.tables:
            result["tables"] = document.tables
            
        if hasattr(document, 'images') and document.images:
            # Resim verilerini json uyumlu hale getir
            image_data = []
            for img in document.images:
                if isinstance(img, dict):
                    img_info = {
                        "caption": img.get("caption", ""),
                        "page": img.get("page", 0),
                        "dimensions": img.get("dimensions", {})
                    }
                    if "data" in img:
                        # Resim verisi çok büyük olabilir, sadece var olduğunu belirt
                        img_info["has_data"] = True
                    image_data.append(img_info)
                else:
                    # Dict olmayan resim nesneleriyle başa çıkma
                    image_data.append({"type": "image", "info": str(type(img))})
            
            result["images"] = image_data
            
        # Sayfalar, bölümler ve içindekiler bilgilerini ekle
        if hasattr(document, 'pages'):
            result["page_count"] = len(document.pages)
            
        if hasattr(document, 'sections'):
            section_data = []
            for section in document.sections:
                if isinstance(section, dict):
                    section_data.append({
                        "title": section.get("title", ""),
                        "content": section.get("content", "")[:200] + "..." if len(section.get("content", "")) > 200 else section.get("content", ""),
                        "level": section.get("level", 0)
                    })
                else:
                    # Dict olmayan section nesneleriyle başa çıkma 
                    section_data.append({"type": "section", "info": str(type(section))})
            result["sections"] = section_data

        return result
        
    except Exception as e:
        logger.error(f"Error parsing document with LlamaParse: {str(e)}")
        # Hata durumunda bile çalışmaya devam edecek şekilde temel yapı döndür
        return {
            "content": "",
            "metadata": {"error": str(e)},
            "elements": [],
            "llama_parse_failed": True
        }

def get_llama_document_structure(file_path: str) -> Dict[str, Any]:
    """
    Doküman yapısını LlamaParse ile analiz eder
    
    Args:
        file_path (str): Doküman dosyasının yolağı
        
    Returns:
        dict: Doküman yapısı bilgileri
    """
    try:
        result = parse_with_llama(file_path)
        
        # LlamaParse başarısız olabilir, bu durumu kontrol edelim
        if result.get("llama_parse_failed", False):
            logger.warning("LlamaParse ile belge yapısı analizi başarısız oldu, temel yapı döndürülüyor...")
            # Dosya tipini ve boyutunu döndür
            file_stats = os.stat(file_path)
            return {
                "file_type": os.path.splitext(file_path)[1].lower().replace('.', ''),
                "content_size": file_stats.st_size,
                "is_llm_optimized": False,
                "llama_parse_error": result.get("metadata", {}).get("error", "Bilinmeyen hata")
            }
        
        # Temel doküman yapısı bilgilerini çıkar
        structure = {
            "file_type": os.path.splitext(file_path)[1].lower().replace('.', ''),
            "content_size": len(result.get("content", "")),
            "is_llm_optimized": True
        }
        
        # Sayfa sayısı ekle
        if "page_count" in result:
            structure["page_count"] = result["page_count"]
            
        # Resim ve tablo sayılarını ekle
        if "images" in result:
            structure["image_count"] = len(result["images"])
            
        if "tables" in result:
            structure["table_count"] = len(result["tables"])
            
        # Bölüm sayısını ekle
        if "sections" in result:
            structure["section_count"] = len(result["sections"])
            
        return structure
        
    except Exception as e:
        logger.error(f"Error getting document structure with LlamaParse: {str(e)}")
        # Hatada bile basit bir yapı döndür, böylece akış bozulmaz
        return {
            "file_type": os.path.splitext(file_path)[1].lower().replace('.', ''),
            "content_size": os.path.getsize(file_path),
            "is_llm_optimized": False,
            "llama_parse_error": str(e)
        }

def extract_llama_content(file_path: str) -> str:
    """
    Bir dokümanın metin içeriğini LlamaParse ile çıkarır
    
    Args:
        file_path (str): Doküman dosyasının yolağı
        
    Returns:
        str: Dokümanın metin içeriği
    """
    try:
        result = parse_with_llama(file_path)
        
        # LlamaParse başarısız olma durumunu kontrol et
        if result.get("llama_parse_failed", False):
            logger.warning("LlamaParse ile metin çıkarma başarısız oldu, standart document_parser'a geçiliyor.")
            # Boş içerik döndürelim, standart parser çalışacak
            return ""
            
        return result.get("content", "")
    except Exception as e:
        logger.error(f"Error extracting content with LlamaParse: {str(e)}")
        # Hata durumunda boş metin dön, böylece akış bozulmaz
        return ""

def set_llama_api_key(api_key: str) -> bool:
    """
    LlamaParse API anahtarını ayarla
    
    Args:
        api_key (str): LlamaParse API anahtarı
    
    Returns:
        bool: Başarılı olursa True, değilse False
    """
    try:
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            logger.warning("Geçersiz API anahtarı formatı")
            return False
        
        cleaned_api_key = api_key.strip()
        
        # API anahtarını ortam değişkenine ayarla
        os.environ[LLAMA_CLOUD_API_KEY_ENV] = cleaned_api_key
        
        # Global değişkeni de güncelle
        global LLAMA_API_KEY
        LLAMA_API_KEY = cleaned_api_key
        
        logger.info(f"LlamaParse API anahtarı başarıyla ayarlandı: {cleaned_api_key[:5]}...{cleaned_api_key[-5:] if len(cleaned_api_key) > 10 else ''}")
        
        # API anahtarının doğru ayarlandığını ve modülün kullanılabilir olduğunu test et
        if not LLAMA_PARSE_AVAILABLE:
            logger.warning("API anahtarı ayarlandı, ancak LlamaParse modülleri yüklü değil.")
            print("LlamaParse modülleri bulunamadı - paketleri tekrar yükleyin.")
            return False
        
        # API anahtarını kontrol et
        print(f"API anahtarı ayarlandı: {cleaned_api_key[:5]}...{cleaned_api_key[-5:] if len(cleaned_api_key) > 10 else ''}")
        logger.debug(f"Mevcut modül yolu: {sys.path}")
        
        try:
            # LlamaParse'i hızlı bir şekilde test et
            if not LLAMA_PARSE_AVAILABLE:
                logger.warning("LlamaParse modülü kullanılamıyor, API anahtarı ayarlandı ama kullanılamıyor.")
                return False
                
            return True
        except Exception as inner_e:
            logger.error(f"API anahtarı ayarlandı, ancak test sırasında hata oluştu: {str(inner_e)}")
            return False
            
    except Exception as e:
        logger.error(f"API anahtarı ayarlanırken hata oluştu: {str(e)}")
        return False

def is_llama_parse_available() -> bool:
    """
    LlamaParse'in kullanılabilir olup olmadığını kontrol eder
    
    Returns:
        bool: API anahtarı varsa ve llama-parse modülü mevcutsa True, yoksa False
    """
    # Önce modülün yüklenip yüklenmediğini kontrol et
    if not LLAMA_PARSE_AVAILABLE:
        logger.warning("LlamaParse modülü yüklü değil veya import edilemedi")
        return False
    
    # Önce global değişkendeki API anahtarını kontrol et
    global LLAMA_API_KEY
    if LLAMA_API_KEY:
        # Global değişkendeki API anahtarını ortam değişkenine de ayarla
        os.environ[LLAMA_CLOUD_API_KEY_ENV] = LLAMA_API_KEY
        logger.info("Global API anahtarı bulundu ve kullanılıyor")
        return True
    
    # Sonra ortam değişkenindeki API anahtarını kontrol et
    api_key = os.environ.get(LLAMA_CLOUD_API_KEY_ENV)
    if api_key:
        # API anahtarını global değişkene de ayarla
        LLAMA_API_KEY = api_key
        logger.info(f"Ortam değişkeninden API anahtarı alındı: {LLAMA_CLOUD_API_KEY_ENV}")
        return True
    
    logger.warning(f"API anahtarı bulunamadı. Global ve {LLAMA_CLOUD_API_KEY_ENV} ortam değişkeni boş.")
    return False