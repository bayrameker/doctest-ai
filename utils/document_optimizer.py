"""
Document Optimizer - Dokümanları Azure API için token limitine uygun hale getirme aracı

BASİTLEŞTİRİLMİŞ VERSİYON - VERİMLİ VE GÜVENLİ

Bu modül, eski karmaşık optimizasyon stratejileri yerine her durumda çalışacak
basit ve güvenilir bir yaklaşım kullanır.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_document_for_ai(document_text, document_structure=None, ai_provider="openai", 
                            max_tokens=None, strategy=None):
    """
    Dokümanı AI işleme için optimize et - TAMAMEN YENİDEN YAZILDI - AZAMI GÜVENİLİRLİK İÇİN
    
    Args:
        document_text (str): Doküman metni
        document_structure (dict, optional): Doküman yapısı
        ai_provider (str): AI sağlayıcısı adı
        max_tokens (int, optional): Maksimum token sayısı
        strategy (str): Optimizasyon stratejisi
        
    Returns:
        dict: Optimize edilmiş doküman içeriği ve yapısı
    """
    try:
        # Belge kontrol
        if not document_text:
            logger.warning("Belge metni boş, boş bir belge döndürülüyor")
            return {
                "text": "",
                "truncated": False,
                "original_size": 0,
                "optimized_size": 0,
                "ai_provider": ai_provider,
                "structure": document_structure,
                "is_neuraagent_optimized": True,
                "error": "Boş belge"
            }
            
        # Orijinal belge boyutu
        document_size = len(document_text)
        logger.info(f"Doküman boyutu: {document_size} karakter, AI sağlayıcı: {ai_provider}")
        
        # Azure için çok daha güvenli bir limit belirliyoruz
        # Azure'un maksimum karakter limiti (Error log: "Invalid 'messages[1].content': string too long.
        # Expected a string with maximum length 1048576, but got a string with length 4737654 instead.")
        if ai_provider == "azure":
            # Azure token limitinin çok altında bir sınır belirle
            MAX_SAFE_LENGTH = 90000  # Çok daha güvenli bir sınır
            
            # Belge zaten güvenli limitte mi?
            if document_size <= MAX_SAFE_LENGTH:
                logger.info(f"Belge zaten güvenli limitte ({document_size} karakter), değişiklik yapmıyoruz")
                return {
                    "text": document_text,
                    "truncated": False,
                    "original_size": document_size,
                    "optimized_size": document_size,
                    "ai_provider": ai_provider,
                    "structure": document_structure,
                    "is_neuraagent_optimized": True
                }
            
            # Belge çok büyükse, güvenli bir boyuta kes
            logger.warning(f"Belge çok büyük ({document_size} karakter > {MAX_SAFE_LENGTH}), güvenli bir boyuta kesiliyor")
            
            # Belge hakkında özet bilgi
            document_info = f"""
## BELGE BİLGİSİ
Bu belgenin orijinal boyutu {document_size} karakter olup, Azure API limitlerini aşmaktadır.
Belgenin başından itibaren ilk {MAX_SAFE_LENGTH-1000} karakteri alınmıştır.

İşlenen oran: %{round(((MAX_SAFE_LENGTH-1000) / document_size) * 100, 1)}
"""
            # Güvenli bir şekilde kes
            safe_length = MAX_SAFE_LENGTH - len(document_info) - 200  # Ekstra güvenlik payı
            truncated_content = document_text[:safe_length]
            final_text = document_info + truncated_content + "\n\n... (belge boyutu nedeniyle kalan kısım kırpıldı)"
            
            logger.info(f"Belge güvenli bir boyuta kırpıldı. Yeni boyut: {len(final_text)} karakter")
            
            return {
                "text": final_text,
                "truncated": True,
                "original_size": document_size,
                "optimized_size": len(final_text),
                "ai_provider": ai_provider,
                "structure": document_structure,
                "is_neuraagent_optimized": True
            }
        
        # Azure dışındaki sağlayıcılar için farklı bir limit kullan
        # Diğer AI sağlayıcılar için daha yüksek bir limit belirliyoruz
        else:
            # OpenAI için daha yüksek limit
            MAX_LENGTH = 150000
            
            # Belge zaten limitte mi?
            if document_size <= MAX_LENGTH:
                logger.info(f"Belge zaten güvenli limitte ({document_size} karakter), değişiklik yapmıyoruz")
                return {
                    "text": document_text,
                    "truncated": False,
                    "original_size": document_size,
                    "optimized_size": document_size,
                    "ai_provider": ai_provider,
                    "structure": document_structure,
                    "is_neuraagent_optimized": True
                }
            
            # Belge çok büyükse
            logger.warning(f"Belge çok büyük ({document_size} karakter > {MAX_LENGTH}), güvenli bir boyuta kesiliyor")
            
            # Belge hakkında özet bilgi
            document_info = f"""
## BELGE BİLGİSİ
Bu belgenin orijinal boyutu {document_size} karakter olup kırpılmıştır.
Belgenin başından itibaren ilk {MAX_LENGTH-1000} karakteri alınmıştır.

İşlenen oran: %{round(((MAX_LENGTH-1000) / document_size) * 100, 1)}
"""
            # Güvenli bir şekilde kes
            safe_length = MAX_LENGTH - len(document_info) - 200  # Ekstra güvenlik payı
            truncated_content = document_text[:safe_length]
            final_text = document_info + truncated_content + "\n\n... (belge boyutu nedeniyle kalan kısım kırpıldı)"
            
            logger.info(f"Belge güvenli bir boyuta kırpıldı. Yeni boyut: {len(final_text)} karakter")
            
            return {
                "text": final_text,
                "truncated": True,
                "original_size": document_size,
                "optimized_size": len(final_text),
                "ai_provider": ai_provider,
                "structure": document_structure,
                "is_neuraagent_optimized": True
            }
            
    except Exception as e:
        # Hata durumunda en güvenli davranış - çok küçük bir metin döndür
        logger.error(f"Belge optimizasyon hatası: {str(e)}")
        
        # Acil durum çözümü - en fazla 50K karakter al
        emergency_text = ""
        if document_text:
            emergency_text = document_text[:50000] + "\n\n(Belge işleme hatası nedeniyle kırpılmıştır.)"
        
        return {
            "text": emergency_text,
            "truncated": True,
            "original_size": len(document_text) if document_text else 0,
            "optimized_size": len(emergency_text),
            "ai_provider": ai_provider,
            "structure": document_structure,
            "is_neuraagent_optimized": True,
            "error": f"Optimizasyon hatası: {str(e)}"
        }

# Eski isimleri koruyoruz, ancak basitleştirilmiş işlevselliğe yönlendiriyoruz
def split_large_document_for_azure(document_text, document_structure=None):
    """Eski fonksiyon adı - optimize_document_for_ai'ye yönlendirilir."""
    return optimize_document_for_ai(document_text, document_structure, ai_provider="azure")

# Singleton fonksiyonu - artık ihtiyaç yok ama API uyumluluğu için tutuyoruz
def get_document_optimizer(ai_provider="openai", max_tokens=None, strategy="preserve_all"):
    """Geriye dönük uyumluluk için."""
    # Bu fonksiyonu çağıran kodlar bozulmasın diye None dönüyoruz
    return None
