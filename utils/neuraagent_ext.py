"""
NeuraAgent Extension - NeuraAgent için ek metodlar
"""

import logging
from typing import Dict, List, Optional, Any

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def add_methods_to_neuraagent():
    """
    NeuraAgent sınıfına eksik metodları ekler
    """
    from utils.neuraagent import NeuraAgentBasic
    
    # process_document_for_scenarios metodu ekle
    if not hasattr(NeuraAgentBasic, 'process_document_for_scenarios'):
        def process_document_for_scenarios(self, document_text: str, document_structure: Dict[str, Any] = None, 
                                         ai_provider: str = "openai", detailed_processing: bool = False, 
                                         preserve_all_content: bool = False) -> Dict[str, Any]:
            """
            Dokümanı test senaryoları oluşturmak için işleme ve hazırlama.
            Görsel içeriği ve tablolar dahil analiz eder.

            Args:
                document_text: İşlenecek belge metni
                document_structure: Belge yapısı bilgisi (NeuraDoc'tan gelen)
                ai_provider: Kullanılacak AI sağlayıcı
                detailed_processing: Ayrıntılı işleme yapılsın mı?
                preserve_all_content: Tüm belge içeriği korunsun mu?

            Returns:
                Optimum içerik ve zenginleştirilmiş belge analizini içeren sözlük
            """
            logger.info(f"Belge test senaryoları için işleniyor. Sağlayıcı: {ai_provider}, Ayrıntılı mod: {detailed_processing}")
            
            # Tüm içeriği koruma modu aktifse, özellikle bildir
            if preserve_all_content:
                logger.info("MÜŞTERİ TALEBİ: Tüm belge içeriği korunuyor (kırpma yok)")
            
            # Doküman analizi yap (eğer zaten yapılmamışsa)
            document_analysis = None
            if hasattr(self, 'process_document'):
                try:
                    if not document_structure:
                        document_analysis = self.process_document(document_text)
                        document_structure = document_analysis
                except Exception as e:
                    logger.error(f"Doküman işleme hatası: {e}")
            
            # Dokümanın boyutu ve içeriği korunduğunu belirt
            if preserve_all_content:
                document_info = {
                    "text": document_text,
                    "structure": document_structure,
                    "content_preserved": True,
                    "size": len(document_text),
                    "ai_provider": ai_provider,
                    "detailed_processing": detailed_processing
                }
                logger.info(f"Belgenin tüm içeriği korundu. Boyut: {len(document_text)} karakter")
            else:
                # Optimize etmek gerekiyorsa optimize et
                if hasattr(self, 'optimize_document'):
                    try:
                        optimized_result = self.optimize_document(document_text, document_structure)
                        document_info = {
                            "text": optimized_result.get("text", document_text),
                            "structure": document_structure,
                            "optimization_ratio": optimized_result.get("optimization_ratio", 1.0),
                            "ai_provider": ai_provider
                        }
                    except Exception as e:
                        logger.error(f"Optimizasyon hatası: {e}")
                        document_info = {
                            "text": document_text,
                            "structure": document_structure,
                            "optimization_ratio": 1.0,
                            "ai_provider": ai_provider
                        }
                else:
                    document_info = {
                        "text": document_text,
                        "structure": document_structure,
                        "content_preserved": True,
                        "ai_provider": ai_provider
                    }
            
            # Sonuç olarak ihtiyaç duyulan tüm verileri içeren bir sözlük dön
            result = {
                "optimized_text": document_info.get("text", document_text),
                "enhanced_structure": document_structure,
                "original_size": len(document_text),
                "processed_size": len(document_info.get("text", document_text)),
                "ai_provider": ai_provider
            }
            
            return result
            
        # Metodu NeuraAgentBasic sınıfına ekle
        NeuraAgentBasic.process_document_for_scenarios = process_document_for_scenarios
        logger.info("process_document_for_scenarios metodu NeuraAgentBasic sınıfına eklendi")
    
    # optimize_for_ai metodu ekle
    if not hasattr(NeuraAgentBasic, 'optimize_for_ai'):
        def optimize_for_ai(self, document_text: str, ai_provider: str = "openai") -> Dict[str, Any]:
            """
            Geriye dönük uyumluluk için optimize metodu (basit)
            
            Args:
                document_text: Doküman metni
                ai_provider: AI sağlayıcı
                
            Returns:
                Optimize edilmiş içerik
            """
            # Tam koruma stratejisi kullan, müşteri talebi üzerine hiçbir içerik kaybı olmamalı
            logger.info(f"Belgenin tüm içeriği korundu (optimize_for_ai). Boyut: {len(document_text)} karakter")
            
            # Sonuç olarak ihtiyaç duyulan tüm verileri içeren bir sözlük dön
            return {
                "optimized_text": document_text,
                "enhanced_structure": None,
                "original_size": len(document_text),
                "processed_size": len(document_text),
                "ai_provider": ai_provider
            }
            
        # Metodu NeuraAgentBasic sınıfına ekle  
        NeuraAgentBasic.optimize_for_ai = optimize_for_ai
        logger.info("optimize_for_ai metodu NeuraAgentBasic sınıfına eklendi")

    # _analyze_document_images metodu ekle
    if not hasattr(NeuraAgentBasic, '_analyze_document_images'):
        def _analyze_document_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            Belgedeki görselleri detaylı olarak analiz eder
            
            Args:
                images: Görsellerin listesi
                
            Returns:
                Zenginleştirilmiş görsel analizi
            """
            enhanced_images = []
            for idx, image in enumerate(images):
                if isinstance(image, dict):
                    enhanced_image = image.copy()
                    enhanced_image["index"] = idx
                    enhanced_image["analyzed"] = True
                    
                    # Her görsel için test senaryoları oluştur (varsa zaten kullan)
                    if "test_scenarios" not in enhanced_image:
                        enhanced_image["test_scenarios"] = [
                            f"Görsel İçerik Doğrulama: Görselin içeriğini doğrula ve beklenen içeriği karşıladığından emin ol",
                            f"Görsel Erişilebilirlik Testi: Görselin erişilebilirlik standartlarına uygunluğunu kontrol et"
                        ]
                    
                    enhanced_images.append(enhanced_image)
                    
            return enhanced_images

        # Metodu NeuraAgentBasic sınıfına ekle
        NeuraAgentBasic._analyze_document_images = _analyze_document_images
        logger.info("_analyze_document_images metodu NeuraAgentBasic sınıfına eklendi")
        
    # _analyze_document_tables metodu ekle
    if not hasattr(NeuraAgentBasic, '_analyze_document_tables'):
        def _analyze_document_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            Belgedeki tabloları detaylı olarak analiz eder
            
            Args:
                tables: Tabloların listesi
                
            Returns:
                Zenginleştirilmiş tablo analizi
            """
            enhanced_tables = []
            for idx, table in enumerate(tables):
                if isinstance(table, dict):
                    enhanced_table = table.copy()
                    enhanced_table["index"] = idx
                    enhanced_table["analyzed"] = True
                    
                    # Her tablo için test senaryoları oluştur (varsa zaten kullan)
                    if "test_actions" not in enhanced_table:
                        enhanced_table["test_actions"] = [
                            f"Tablo Verilerini Doğrulama: Tablodaki verilerin doğruluğunu kontrol et",
                            f"Tablo Başlıklarını Doğrulama: Tablo başlıklarının doğru olduğunu kontrol et"
                        ]
                    
                    enhanced_tables.append(enhanced_table)
                    
            return enhanced_tables
            
        # Metodu NeuraAgentBasic sınıfına ekle
        NeuraAgentBasic._analyze_document_tables = _analyze_document_tables
        logger.info("_analyze_document_tables metodu NeuraAgentBasic sınıfına eklendi")
        
    # _analyze_document_diagrams metodu ekle
    if not hasattr(NeuraAgentBasic, '_analyze_document_diagrams'):
        def _analyze_document_diagrams(self, diagrams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            Belgedeki diyagramları detaylı olarak analiz eder
            
            Args:
                diagrams: Diyagramların listesi
                
            Returns:
                Zenginleştirilmiş diyagram analizi
            """
            enhanced_diagrams = []
            for idx, diagram in enumerate(diagrams):
                if isinstance(diagram, dict):
                    enhanced_diagram = diagram.copy()
                    enhanced_diagram["index"] = idx
                    enhanced_diagram["analyzed"] = True
                    
                    # Her diyagram için test senaryoları oluştur
                    enhanced_diagram["test_scenarios"] = [
                        f"Diyagram Akış Doğrulama: Diyagramda gösterilen akışın doğruluğunu kontrol et",
                        f"İş Mantığı Doğrulama: Diyagramda tanımlanan iş mantığının gerçek iş süreciyle uyumluluğunu kontrol et"
                    ]
                    
                    enhanced_diagrams.append(enhanced_diagram)
                    
            return enhanced_diagrams
            
        # Metodu NeuraAgentBasic sınıfına ekle
        NeuraAgentBasic._analyze_document_diagrams = _analyze_document_diagrams
        logger.info("_analyze_document_diagrams metodu NeuraAgentBasic sınıfına eklendi")
        
    logger.info("NeuraAgent sınıfına eksik metodlar eklendi.")
    
# Modül yüklendiğinde otomatik olarak çalıştırılacak
if __name__ != "__main__":
    try:
        add_methods_to_neuraagent()
    except Exception as e:
        logger.error(f"NeuraAgent extension hatası: {e}")