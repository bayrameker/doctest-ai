"""
Gelişmiş AI İşlemci - Çoklu model ve gelişmiş işlemleri koordine eden modül

Bu modül, doküman işleme ve test senaryosu oluşturma için farklı AI modellerini
en verimli şekilde kullanarak, dokümanları en yüksek kalitede işleyen sistemi sağlar.
"""

import os
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple

# Bağımlı modülleri içe aktar
from utils.model_selector import model_selector
from utils.multi_model_processor import MultiModelProcessor

# Logging yapılandırması
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AdvancedAIProcessor:
    """
    Farklı AI modellerini koordine eden ve dokümanları akıllıca işleyen sınıf.
    
    Bu sınıf, model seçimi, belge bölümleme, görsel analizi ve test senaryosu 
    oluşturma işlemlerini koordine eder. Belgenin türüne, içeriğine ve
    karmaşıklığına göre en uygun modelleri seçer.
    """
    
    def __init__(self):
        """Gelişmiş AI işlemciyi başlat"""
        self.multi_model_processor = MultiModelProcessor()
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "avg_processing_time": 0
        }
        logger.info("AdvancedAIProcessor başlatıldı")
    
    def process_document(self, document_text: str, document_structure: Dict[str, Any] = None, 
                        preferred_model: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Dokümanı tam ayrıntılı şekilde işle ve test senaryoları oluştur

        Args:
            document_text: İşlenecek belge metni
            document_structure: Belge yapısı bilgisi (varsa)
            preferred_model: Tercih edilen AI modeli (opsiyonel)
            options: İşleme seçenekleri (opsiyonel)
            
        Returns:
            İşlenmiş belge ve oluşturulan test senaryoları
        """
        # Belge yapısı None ise boş dict kullan 
        if document_structure is None:
            document_structure = {}
            
        # Tercih edilen model yoksa, varsayılan olarak "o1" kullan
        if preferred_model is None:
            preferred_model = "o1"
            
        # Seçenekler None ise varsayılan değerler kullan
        if options is None:
            options = {
                "preserve_all_content": True,
                "detailed_processing": True,
                "use_multi_model": True
            }
        # Başlangıç zamanını kaydet
        start_time = time.time()
        
        # Bu kısım artık üstte yapıldığı için kaldırıldı
        # if options is None:
        #    options = {}
        
        # Önemli seçenekleri al
        preserve_all = options.get("preserve_all_content", True)  # Tüm içeriği koru (müşteri talebi)
        detailed_processing = options.get("detailed_processing", True)  # Detaylı işleme (görsel, tablo)
        
        logger.info(f"Gelişmiş doküman işleme başlatıldı. Doküman boyutu: {len(document_text)} karakter")
        logger.info(f"Seçenekler: preserve_all={preserve_all}, detailed={detailed_processing}")
        
        # İçerik analizi yap - document_structure artık her zaman bir dict olacak
        # (Üstte None kontrol edildiği için bu kontrol gereksiz)
        
        # Görevi ve karmaşıklığı belirle
        complexity = model_selector.get_task_complexity(document_text[:5000], "technical")
        logger.info(f"Doküman karmaşıklık puanı: {complexity:.2f}")
        
        # En uygun modeli seç
        if preferred_model:
            logger.info(f"Tercih edilen model kullanılıyor: {preferred_model}")
            primary_model = preferred_model
        else:
            # İçerik karmaşıklığına göre model seç
            model_config = model_selector.select_model_for_task("technical", document_text[:2000], len(document_text), complexity)
            primary_model = model_config["model"]
            logger.info(f"İçerik analizine göre seçilen model: {primary_model}")
        
        try:
            # Tüm işlemeyi birden fazla modelle yap
            if options.get("use_multi_model", True):
                logger.info("Çoklu model işleme stratejisi kullanılıyor")
                result = self.multi_model_processor.process_document(document_text, document_structure, primary_model)
            else:
                # Tek model kullan
                logger.info(f"Tek model işleme stratejisi kullanılıyor ({primary_model})")
                provider = "azure" if primary_model in ["o1", "o3-mini"] else "openai"
                
                if provider == "azure":
                    from utils.azure_service import generate_with_azure
                    context = {
                        "text": document_text,
                        "structure": document_structure,
                        "azure_model": primary_model
                    }
                    result = generate_with_azure(context)
                else:
                    from utils.openai_service import generate_with_openai
                    context = {
                        "text": document_text,
                        "structure": document_structure
                    }
                    result = generate_with_openai(context)
            
            # İşleme süresini kaydet
            processing_time = time.time() - start_time
            
            # Sonuç detaylarını ekle
            if isinstance(result, dict):
                result["processing_details"] = {
                    "processing_time": processing_time,
                    "model_used": primary_model,
                    "complexity_score": complexity,
                    "document_size": len(document_text),
                    "strategy": "multi_model" if options.get("use_multi_model", True) else "single_model"
                }
                
                # İşleme istatistiklerini güncelle
                self._update_stats(True, processing_time)
            else:
                logger.error("İşleme sonucu geçerli bir değer değil")
                result = {"error": "İşleme sonucu geçerli bir değer değil"}
                self._update_stats(False, processing_time)
            
            logger.info(f"Doküman işleme tamamlandı. Süre: {processing_time:.2f} saniye")
            return result
            
        except Exception as e:
            logger.error(f"Doküman işleme hatası: {str(e)}")
            
            # Yedek strateji: daha basit bir model dene
            try:
                logger.warning("Hata sonrası yedek strateji deneniyor...")
                
                # Yedek model olarak o1 dene
                fallback_model = "o1"
                
                from utils.azure_service import generate_with_azure
                context = {
                    "text": document_text,
                    "structure": document_structure,
                    "azure_model": fallback_model,
                    "fallback": True
                }
                result = generate_with_azure(context)
                
                # İşleme süresini kaydet
                processing_time = time.time() - start_time
                
                # Sonuç detaylarını ekle
                if isinstance(result, dict):
                    result["processing_details"] = {
                        "processing_time": processing_time,
                        "model_used": fallback_model,
                        "is_fallback": True,
                        "complexity_score": complexity,
                        "document_size": len(document_text),
                        "original_error": str(e)
                    }
                    
                # İşleme istatistiklerini güncelle
                self._update_stats(True, processing_time)
                logger.info(f"Yedek strateji ile doküman işleme tamamlandı. Süre: {processing_time:.2f} saniye")
                return result
                
            except Exception as fallback_error:
                # Her iki strateji de başarısız oldu
                logger.error(f"Yedek strateji de başarısız oldu: {str(fallback_error)}")
                
                # İşleme süresini kaydet
                processing_time = time.time() - start_time
                
                # İşleme istatistiklerini güncelle
                self._update_stats(False, processing_time)
                
                return {
                    "error": f"Doküman işleme hatası: {str(e)}. Yedek strateji de başarısız oldu: {str(fallback_error)}",
                    "status": "error"
                }
    
    def process_image(self, image_data, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Görsel verilerini işle ve ilişkili test senaryolarını oluştur
        
        Args:
            image_data: Görsel verileri (base64 veya URL olabilir)
            context: Görsel işleme bağlamı
            
        Returns:
            İşlenmiş görsel analizi ve test senaryoları
        """
        start_time = time.time()
        
        try:
            # Görseller için en iyi model gpt-4o (OpenAI)
            model_config = model_selector.select_model_for_task("image_analysis")
            model = model_config["model"]
            provider = model_config["provider"]
            
            logger.info(f"Görsel işleme için seçilen model: {provider}/{model}")
            
            # Görsel içerik kaynağını logla
            if isinstance(image_data, dict) and "base64" in image_data:
                logger.info("Görsel kaynağı: base64 veri (kısa gösterim)")
                # Güvenlik nedeniyle base64 verilerinin ilk 20 karakterini logla
                logger.debug(f"Görsel base64 önizleme: {image_data['base64'][:20]}...")
            elif isinstance(image_data, dict) and "url" in image_data:
                logger.info(f"Görsel kaynağı: URL - {image_data['url']}")
            elif isinstance(image_data, str) and image_data.startswith("http"):
                logger.info(f"Görsel kaynağı: URL - {image_data}")
            elif isinstance(image_data, str) and (image_data.startswith("data:image") or len(image_data) > 100):
                logger.info("Görsel kaynağı: Doğrudan base64 veri (kısa gösterim)")
                logger.debug(f"Görsel base64 önizleme: {image_data[:20]}...")
            else:
                logger.warning(f"Bilinmeyen görsel veri formatı: {type(image_data)}")
            
            # Context bilgilerini logla
            if context:
                logger.info(f"Görsel bağlamı anahtarları: {', '.join(context.keys())}")
                if "image_index" in context:
                    logger.info(f"Görsel indeksi: {context['image_index']}")
                if "page" in context:
                    logger.info(f"Sayfa: {context['page']}")
                if "description" in context:
                    logger.info(f"Açıklama: {context['description'][:100]}...")
            
            data = {
                "task": "image_analysis",
                "image": image_data,
                "context": context or {},
                "full_analysis": True  # Tam analiz iste
            }
            
            if provider == "openai":
                from utils.openai_service import process_with_model
                result = process_with_model(model, data)
            else:
                # Görsel özelliği olmayan Azure modelleri için OpenAI'a yönlendir
                from utils.openai_service import process_with_model
                result = process_with_model("gpt-4o", data)
            
            # İşleme süresini ekle
            processing_time = time.time() - start_time
            
            if "result" in result:
                result["result"]["processing_time"] = processing_time
                result["result"]["model_used"] = model
                
            logger.info(f"Görsel işleme tamamlandı. Süre: {processing_time:.2f} saniye")
            return result
            
        except Exception as e:
            logger.error(f"Görsel işleme hatası: {str(e)}")
            return {"error": str(e)}
    
    def _update_stats(self, success: bool, processing_time: float) -> None:
        """İşleme istatistiklerini güncelle"""
        self.processing_stats["total_processed"] += 1
        
        if success:
            self.processing_stats["successful"] += 1
        else:
            self.processing_stats["failed"] += 1
        
        # Ortalama işleme süresini güncelle
        total = self.processing_stats["successful"] + self.processing_stats["failed"]
        if total > 0:
            current_avg = self.processing_stats["avg_processing_time"]
            new_avg = ((current_avg * (total - 1)) + processing_time) / total
            # float değeri int olarak kaydetme
            self.processing_stats["avg_processing_time"] = new_avg
            
        # Detaylı log ekle
        logger.info(f"İşleme istatistikleri güncellendi: "
                   f"Toplam: {self.processing_stats['total_processed']}, "
                   f"Başarılı: {self.processing_stats['successful']}, "
                   f"Başarısız: {self.processing_stats['failed']}, "
                   f"Ort. Süre: {self.processing_stats['avg_processing_time']:.2f} sn")
    
    def get_stats(self) -> Dict[str, Any]:
        """İşleme istatistiklerini döndür"""
        return self.processing_stats

# Modül yüklendiğinde otomatik olarak işlemci oluştur
advanced_processor = AdvancedAIProcessor()