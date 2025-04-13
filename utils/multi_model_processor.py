"""
Multi-Model AI Processor

Bu modül, farklı görev türleri için farklı AI modellerini kullanarak 
doküman analizi ve test senaryosu oluşturma işlemlerini gerçekleştirir.

- Görsel işleme: GPT-4o (OpenAI)
- Metin sınıflandırma ve analiz: o3-mini (Azure)
- Teknik içerik ve otomasyona yönelik senaryolar: o1 (Azure)
"""

import os
import json
import logging
import time
import traceback
import datetime
from typing import Dict, List, Any, Optional, Tuple

# Özel JSON Serializer - Datetime ve diğer özel tipler için
class JSONDateTimeEncoder(json.JSONEncoder):
    """Datetime nesnelerini ISO formatında string'e çeviren JSON encoder"""
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            return o.isoformat()
        return super(JSONDateTimeEncoder, self).default(o)

# Logging yapılandırma
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Model yapılandırmaları
MODEL_CONFIG = {
    "image_analysis": {
        "provider": "openai",
        "model": "gpt-4o",
        "description": "Gelişmiş görsel analiz modeli",
        "max_tokens": 2000
    },
    "classification": {
        "provider": "azure",
        "model": "o3-mini",
        "description": "Metin sınıflandırma ve temel analiz modeli",
        "max_tokens": 1000
    },
    "technical": {
        "provider": "azure",
        "model": "o1",
        "description": "Teknik detay ve otomasyon senaryoları modeli",
        "max_tokens": 3000
    },
    "summary": {
        "provider": "azure",
        "model": "gpt-4o-mini",
        "description": "Özet ve sentez görevleri modeli",
        "max_tokens": 1500
    }
}

class MultiModelProcessor:
    """
    Farklı AI modellerini koordine ederek dokümandan test senaryoları oluşturan sınıf
    """
    
    def __init__(self):
        """Çok modelli işlemciyi başlat"""
        self.results_cache = {}
        logger.info("MultiModelProcessor başlatıldı")
        
    def process_document(self, document_text: str, document_structure: Dict[str, Any], 
                        base_model: str = "o1") -> Dict[str, Any]:
        """
        Dokümanı farklı modeller kullanarak tamamen işle ve sonuçları birleştir
        
        Args:
            document_text: İşlenecek doküman metni
            document_structure: Dokümanın yapısal bilgileri
            base_model: Ana AI modeli (varsayılan: o1)
            
        Returns:
            Birleştirilmiş AI sonuçları
        """
        start_time = time.time()
        logger.info(f"MultiModelProcessor doküman işleme başlatıldı. Uzunluk: {len(document_text)} karakter")
        
        try:
            # 1. Doküman sınıflandırma ve temel özellikleri çıkarma (o3-mini)
            classification_data = {
                "text": document_text, 
                "task": "document_classification"
            }
            
            # Doküman yapısı varsa sınıflandırma context'ine ekle
            if document_structure:
                classification_data["structure"] = document_structure
                
            classification_result = self._process_with_model(
                "classification", 
                classification_data
            )
            
            # 2. Görsel içerikleri analiz et ve işle (GPT-4o)
            image_results = self._process_images(document_structure)
            
            # 3. Tabloları analiz et (o3-mini)
            table_results = self._process_tables(document_structure)
            
            # 4. Diyagramları analiz et (GPT-4o)
            diagram_results = self._process_diagrams(document_structure)
            
            # 5. Teknik ayrıntıları ve ana test senaryolarını oluştur (o1)
            # Boş belge kontrolü - çok kısa metinlerde zengin içerik kullan
            if len(document_text) < 50 and (len(image_results) > 0 or len(table_results) > 0):
                logger.warning(f"Belge metni çok kısa ({len(document_text)} karakter), zengin içerik odaklı işlem yapılıyor.")
                # Metni zenginleştir
                enriched_text = "Belgede yeterli metin yok, ancak görsel ve tablo içerikler mevcut. "
                
                if len(image_results) > 0:
                    enriched_text += f"Belgede {len(image_results)} görsel bulunmaktadır. "
                    # Görsellerden metin oluştur
                    for idx, img in enumerate(image_results[:3]):
                        if isinstance(img, dict) and "description" in img:
                            enriched_text += f"Görsel {idx+1}: {img.get('description', '')}. "
                
                if len(table_results) > 0:
                    enriched_text += f"Belgede {len(table_results)} tablo bulunmaktadır. "
                    # Tablolardan metin oluştur
                    for idx, tbl in enumerate(table_results[:3]):
                        if isinstance(tbl, dict) and "caption" in tbl:
                            enriched_text += f"Tablo {idx+1}: {tbl.get('caption', '')}. "
                
                # Zenginleştirilmiş metni kullan
                document_text = enriched_text
            
            test_scenarios = self._generate_test_scenarios(
                document_text, document_structure, classification_result,
                image_results, table_results, diagram_results
            )
            
            # 6. Tüm sonuçları birleştir ve özet oluştur (gpt-4o-mini)
            final_result = self._synthesize_results(
                test_scenarios, classification_result, 
                image_results, table_results, diagram_results
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Çoklu model işleme tamamlandı. Süre: {processing_time:.2f} saniye")
            
            # İşleme süresini ekle
            final_result["processing_info"] = {
                "processing_time": processing_time,
                "models_used": ["o1", "o3-mini", "gpt-4o", "gpt-4o-mini"],
                "document_size": len(document_text)
            }
            
            return final_result
            
        except Exception as e:
            logger.error(f"Çoklu model işleme hatası: {str(e)}")
            # Hata durumunda bir model ile devam et
            return self._fallback_processing(document_text, document_structure, base_model)
    
    def _process_with_model(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Belirli bir model ile veriyi işle
        
        Args:
            task_type: Görev türü (MODEL_CONFIG'da tanımlı)
            data: İşlenecek veri
            
        Returns:
            İşlenmiş sonuçlar
        """
        if task_type not in MODEL_CONFIG:
            logger.warning(f"Tanımlanmamış görev türü: {task_type}, varsayılan 'technical' kullanılıyor")
            task_type = "technical"
            
        model_config = MODEL_CONFIG[task_type]
        provider = model_config["provider"]
        model = model_config["model"]
        
        logger.info(f"'{task_type}' görevi için {provider} - {model} kullanılıyor")
        
        try:
            # OpenAI modeli ile işleme
            if provider == "openai":
                return self._process_with_openai(model, data)
                
            # Azure modeli ile işleme
            elif provider == "azure":
                return self._process_with_azure(model, data)
                
            else:
                logger.error(f"Desteklenmeyen sağlayıcı: {provider}")
                return {"error": f"Desteklenmeyen sağlayıcı: {provider}"}
                
        except Exception as e:
            logger.error(f"{task_type} görevi için {provider}/{model} modeli ile işleme hatası: {str(e)}")
            return {"error": str(e)}
    
    def _process_with_openai(self, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        OpenAI API kullanarak veriyi işle
        
        Args:
            model: Kullanılacak OpenAI modeli
            data: İşlenecek veri
            
        Returns:
            İşlenmiş sonuçlar
        """
        # OpenAI işlemesi için ayrı bir servis kullan
        try:
            from utils.openai_service import process_with_model
            result = process_with_model(model, data)
            return result
        except ImportError:
            logger.error("OpenAI servisi yüklenemedi")
            return {"error": "OpenAI servisi yüklenemedi"}
    
    def _process_with_azure(self, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Azure OpenAI API kullanarak veriyi işle
        
        Args:
            model: Kullanılacak Azure modeli
            data: İşlenecek veri
            
        Returns:
            İşlenmiş sonuçlar
        """
        # Azure işlemesi için ayrı bir servis kullan
        try:
            # Direk Azure servisinden generate_with_azure kullan
            from utils.azure_service import generate_with_azure, json_serialize
            
            # Azure için model bilgisini ekle
            context = {
                "text": data.get("text", ""),
                "structure": data.get("structure", {}),
                "azure_model": model
            }
            
            # Context içinde task bilgisini sakla
            if "task" in data:
                context["task"] = data["task"]
                
            # Görsel, tablo veya diagram bilgileri varsa ekle
            if "visual_insights" in data:
                # Görsel içgörülerini ayrıntılı logla
                logger.debug(f"Visual insights ekleniyor: {len(data['visual_insights'])} adet")
                try:
                    # Serileştirilebilir olduğunu kontrol et
                    json_serialize(data["visual_insights"])
                    context["visual_insights"] = data["visual_insights"]
                except Exception as vis_err:
                    logger.warning(f"Visual insights serileştirme hatası: {str(vis_err)}")
                    # Hatalıysa metin olarak ekle
                    safe_insights = []
                    for vi in data["visual_insights"]:
                        try:
                            if isinstance(vi, dict):
                                safe_vi = {}
                                for k, v in vi.items():
                                    try:
                                        # Önce serileştirmeyi dene
                                        json.dumps({k: v})
                                        safe_vi[k] = v
                                    except:
                                        # Serileştirilemiyorsa stringe çevir
                                        safe_vi[k] = str(v)
                                safe_insights.append(safe_vi)
                            else:
                                safe_insights.append(str(vi))
                        except:
                            pass
                    context["visual_insights"] = safe_insights
                    
            if "table_insights" in data:
                # Tablo içgörülerini ayrıntılı logla
                logger.debug(f"Table insights ekleniyor: {len(data['table_insights'])} adet")
                try:
                    # Serileştirilebilir olduğunu kontrol et
                    json_serialize(data["table_insights"])
                    context["table_insights"] = data["table_insights"]
                except Exception as tbl_err:
                    logger.warning(f"Table insights serileştirme hatası: {str(tbl_err)}")
                    # Hatalıysa metin olarak ekle
                    safe_insights = []
                    for ti in data["table_insights"]:
                        try:
                            if isinstance(ti, dict):
                                safe_ti = {}
                                for k, v in ti.items():
                                    try:
                                        # Önce serileştirmeyi dene
                                        json.dumps({k: v})
                                        safe_ti[k] = v
                                    except:
                                        # Serileştirilemiyorsa stringe çevir
                                        safe_ti[k] = str(v)
                                safe_insights.append(safe_ti)
                            else:
                                safe_insights.append(str(ti))
                        except:
                            pass
                    context["table_insights"] = safe_insights
                
            # Geriye dönük uyumluluk için özel bir parametre ekle
            context["multi_model_call"] = True
                
            # Detaylı log ekle
            logger.info(f"Azure servisine istek gönderiliyor. Model: {model}, Task: {data.get('task', 'unknown')}")
            
            # Tam context logla (güvenli bir şekilde)
            try:
                logger.debug(f"Azure context detayları: {json_serialize(context)[:500]}...")
            except:
                logger.debug("Azure context detayları loglanamadı")
            
            # Azure servisi üzerinden sonuç al
            result = generate_with_azure(context)
            
            # Sonucu uygun formata çevir
            if result and isinstance(result, dict) and "error" not in result:
                logger.info(f"Azure servisinden başarılı yanıt alındı. Model: {model}")
                # Sorun çıkmaması için tüm nesneleri güvenli bir şekilde serileştirebildiğimizi kontrol et
                try:
                    # Sonucu logla
                    result_preview = json_serialize(result)
                    logger.debug(f"Azure sonuç önizleme: {result_preview[:200]}...")
                except Exception as json_err:
                    logger.warning(f"Azure sonucu serileştirme hatası: {str(json_err)}")
                
                return {
                    "result": result,
                    "model": model,
                    "task": data.get("task", "unknown")
                }
            else:
                logger.error(f"Azure servisinden hata yanıtı: {result}")
                error_msg = result.get("error", "Bilinmeyen hata") if isinstance(result, dict) else "Bilinmeyen hata"
                return {"error": f"Azure servisi hatası: {error_msg}"}
                
        except ImportError as e:
            logger.error(f"Azure servisi yüklenemedi: {str(e)}")
            return {"error": f"Azure servisi yüklenemedi: {str(e)}"}
        except Exception as e:
            logger.error(f"Azure servisi ile işleme hatası: {str(e)}")
            logger.error(f"Hata ayrıntıları: {traceback.format_exc()}")
            return {"error": f"Azure servisi ile işleme hatası: {str(e)}"}
    
    def _process_images(self, document_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Belgedeki görselleri GPT-4o ile işle
        
        Args:
            document_structure: Belge yapısı
            
        Returns:
            İşlenmiş görsel analizleri
        """
        image_results = []
        
        # Görsel varsa işle
        if "images" in document_structure and document_structure["images"]:
            total_images = len(document_structure["images"])
            logger.info(f"{total_images} görsel GPT-4o ile analiz ediliyor")
            
            # Daha detaylı log
            logger.info("Görsel analizi her zaman aktif - kritik müşteri gereksinimidir")
            
            # Eğer belge yapısında 'image_processing' false olarak ayarlanmışsa, true yap
            # Bu, belge analizörünün görsel işlemeyi atlama hatasını düzeltir
            if isinstance(document_structure, dict) and document_structure.get("image_processing") is False:
                document_structure["image_processing"] = True
                logger.info("Görsel işleme zorla etkinleştirildi")
                
            for idx, image in enumerate(document_structure["images"]):
                logger.info(f"Görsel {idx+1}/{total_images} işleniyor")
                if isinstance(image, dict):
                    # Her görseli GPT-4o ile analiz et
                    image_data = {
                        "task": "image_analysis",
                        "image": image,
                        "context": {
                            "document_type": document_structure.get("document_type", ""),
                            "document_purpose": document_structure.get("document_purpose", ""),
                            "page_number": image.get("page", 0)
                        }
                    }
                    
                    # GPT-4o ile analiz
                    image_result = self._process_with_model("image_analysis", image_data)
                    
                    if "error" not in image_result:
                        # Başarılı sonuçları ekle
                        enriched_image = image_result.get("result", {})
                        enriched_image["index"] = idx
                        enriched_image["source_image"] = image
                        image_results.append(enriched_image)
                        
                        logger.info(f"Görsel {idx+1} başarıyla analiz edildi")
                    else:
                        logger.warning(f"Görsel {idx+1} analiz edilemedi: {image_result.get('error')}")
        
        logger.info(f"Toplam {len(image_results)} görsel başarıyla analiz edildi")
        return image_results
    
    def _process_tables(self, document_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Belgedeki tabloları o3-mini ile işle
        
        Args:
            document_structure: Belge yapısı
            
        Returns:
            İşlenmiş tablo analizleri
        """
        table_results = []
        
        # Tablo varsa işle
        if "tables" in document_structure and document_structure["tables"]:
            logger.info(f"{len(document_structure['tables'])} tablo o3-mini ile analiz ediliyor")
            
            for idx, table in enumerate(document_structure["tables"]):
                if isinstance(table, dict):
                    # Her tabloyu o3-mini ile analiz et
                    table_data = {
                        "task": "table_analysis",
                        "table": table,
                        "context": {
                            "document_type": document_structure.get("document_type", ""),
                            "document_purpose": document_structure.get("document_purpose", ""),
                            "page_number": table.get("page", 0)
                        }
                    }
                    
                    # o3-mini ile analiz 
                    table_result = self._process_with_model("classification", table_data)
                    
                    if "error" not in table_result:
                        # Başarılı sonuçları ekle
                        enriched_table = table_result.get("result", {})
                        enriched_table["index"] = idx
                        enriched_table["source_table"] = table
                        table_results.append(enriched_table)
                        
                        logger.info(f"Tablo {idx+1} başarıyla analiz edildi")
                    else:
                        logger.warning(f"Tablo {idx+1} analiz edilemedi: {table_result.get('error')}")
        
        logger.info(f"Toplam {len(table_results)} tablo başarıyla analiz edildi")
        return table_results
    
    def _process_diagrams(self, document_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Belgedeki diyagramları GPT-4o ile işle
        
        Args:
            document_structure: Belge yapısı
            
        Returns:
            İşlenmiş diyagram analizleri
        """
        diagram_results = []
        
        # Diyagram varsa işle
        if "diagrams" in document_structure and document_structure["diagrams"]:
            logger.info(f"{len(document_structure['diagrams'])} diyagram GPT-4o ile analiz ediliyor")
            
            for idx, diagram in enumerate(document_structure["diagrams"]):
                if isinstance(diagram, dict):
                    # Her diyagramı GPT-4o ile analiz et
                    diagram_data = {
                        "task": "diagram_analysis",
                        "diagram": diagram,
                        "context": {
                            "document_type": document_structure.get("document_type", ""),
                            "document_purpose": document_structure.get("document_purpose", ""),
                            "page_number": diagram.get("page", 0)
                        }
                    }
                    
                    # GPT-4o ile analiz
                    diagram_result = self._process_with_model("image_analysis", diagram_data)
                    
                    if "error" not in diagram_result:
                        # Başarılı sonuçları ekle
                        enriched_diagram = diagram_result.get("result", {})
                        enriched_diagram["index"] = idx
                        enriched_diagram["source_diagram"] = diagram
                        diagram_results.append(enriched_diagram)
                        
                        logger.info(f"Diyagram {idx+1} başarıyla analiz edildi")
                    else:
                        logger.warning(f"Diyagram {idx+1} analiz edilemedi: {diagram_result.get('error')}")
        
        logger.info(f"Toplam {len(diagram_results)} diyagram başarıyla analiz edildi")
        return diagram_results
    
    def _generate_test_scenarios(self, document_text: str, document_structure: Dict[str, Any],
                               classification_result: Dict[str, Any], image_results: List[Dict[str, Any]],
                               table_results: List[Dict[str, Any]], diagram_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ana test senaryolarını o1 modeli ile oluştur
        
        Args:
            document_text: İşlenecek doküman metni
            document_structure: Dokümanın yapısal bilgileri
            classification_result: Sınıflandırma sonuçları
            image_results: İşlenmiş görsel analizleri
            table_results: İşlenmiş tablo analizleri
            diagram_results: İşlenmiş diyagram analizleri
            
        Returns:
            Oluşturulan test senaryoları
        """
        logger.info("Ana test senaryoları o1 modeli ile oluşturuluyor")
        
        # Görsel ve tablo analizlerine hızlı erişim
        visual_insights = []
        table_insights = []
        
        # Doküman metni çok kısa ise potansiyel bir sorun var demektir - çözüm uygula
        if len(document_text) < 500 and document_structure:
            logger.warning(f"Doküman metni çok kısa ({len(document_text)} karakter). Yapısal veriyi kullanarak zenginleştirme uygulanıyor.")
            enhanced_text = document_text
            
            # Yapıdan additional_text varsa ekle
            if document_structure.get("additional_text"):
                enhanced_text += "\n\n" + document_structure.get("additional_text")
                logger.info(f"Yapıdan ek metin eklendi: {len(document_structure.get('additional_text'))} karakter")
                
            # Yapıdaki tüm anahtarları metne ekle
            structure_text = "\n".join([f"{k}: {v}" for k, v in document_structure.items() 
                                     if k not in ["additional_text"] and isinstance(v, str)])
            if structure_text:
                enhanced_text += "\n\n" + structure_text
                logger.info(f"Yapı bilgilerinden ek metin eklendi: {len(structure_text)} karakter")
                
            document_text = enhanced_text
            logger.info(f"Zenginleştirilmiş doküman metni: {len(document_text)} karakter")
        
        # Tüm görselleri log detayları ile ekle - önemli kritik fix
        logger.debug(f"İşlenecek görsel sayısı: {len(image_results)}")
        for i, img in enumerate(image_results):
            if isinstance(img, dict):
                logger.debug(f"Görsel {i+1} işleniyor - Anahtarlar: {', '.join(img.keys())}")
                image_content = ""
                
                # OCR ile çıkarılmış metni kontrol et
                if "description" in img and img["description"]:
                    image_content = img["description"]
                    logger.info(f"Görsel {i+1} - OCR metni bulundu: {len(image_content)} karakter")
                
                # Alt metni varsa ekle
                if "alt_text" in img and img["alt_text"]:
                    if image_content:
                        image_content += " - " + img["alt_text"]
                    else:
                        image_content = img["alt_text"]
                    logger.info(f"Görsel {i+1} - Alt metin eklendi")
                
                # Görsel içeriği yoksa uyarı ver ve varsayılan metin oluştur
                if not image_content and ("width" in img or "height" in img):
                    image_width = img.get("width", 0)
                    image_height = img.get("height", 0)
                    image_type = "diagram" if image_width > image_height * 1.5 else "screenshot" if image_width > image_height else "icon" if image_width < 100 and image_height < 100 else "image"
                    image_content = f"Belgede {image_width}x{image_height} boyutunda bir {image_type} bulunmaktadır. Bu görselin içeriği test edilmelidir."
                    logger.warning(f"Görsel {i+1} için OCR metni bulunamadı - varsayılan açıklama oluşturuldu")
                
                # Diğer zenginleştirilmiş içerikleri kontrol et
                if "test_scenarios" in img:
                    logger.info(f"Görsel {i+1}'de {len(img['test_scenarios'])} test senaryosu bulundu")
                    for scenario in img['test_scenarios']:
                        if isinstance(scenario, dict):
                            # Senaryo başlığını zenginleştir
                            if "title" in scenario and not scenario["title"].startswith("Görsel"):
                                scenario["title"] = f"Görsel {i+1} - {scenario['title']}"
                            visual_insights.append(scenario)
                        else:
                            # Dict değilse dict'e çevir
                            visual_insights.append({
                                "title": f"Görsel {i+1} Test Senaryosu",
                                "description": str(scenario),
                                "source": "image_analysis"
                            })
                elif "analysis" in img:
                    analysis_text = str(img["analysis"])
                    logger.info(f"Görsel {i+1}'de analiz metni bulundu: {analysis_text[:100]}...")
                    # Bu içerikten bir senaryo oluştur
                    visual_insights.append({
                        "title": f"Görsel {i+1} Analiz Senaryosu",
                        "description": analysis_text,
                        "source": "image_analysis"
                    })
                elif image_content:
                    # Doğrudan bir senaryo oluştur
                    logger.info(f"Görsel {i+1} için içerik kullanılıyor: {image_content[:100]}...")
                    scenario = {
                        "title": f"Görsel {i+1} Test Senaryosu",
                        "description": f"Görselden çıkarılan içerik: {image_content}",
                        "source": "image_analysis",
                        "test_cases": [
                            {
                                "title": f"Görsel {i+1} İçeriği Testi",
                                "steps": f"1. Belgedeki Görsel {i+1}'i incele\n2. Görselin içeriğini doğrula\n3. Görseldeki işlevselliği test et",
                                "expected_result": "Görseldeki içerik ve işlevsellik doğru çalışmalıdır."
                            }
                        ]
                    }
                    visual_insights.append(scenario)
                else:
                    # Tüm görsel anahtarlarını kullanarak bir senaryo oluştur
                    content = ", ".join([f"{k}: {str(v)[:50]}" for k, v in img.items() if k != "data"])
                    logger.info(f"Görsel {i+1} için alternatif içerik kullanılıyor: {content[:100]}...")
                    scenario = {
                        "title": f"Görsel {i+1} Test Senaryosu",
                        "description": f"Görsel içeriğinden çıkarılan test: {content[:200]}...",
                        "source": "image_analysis_raw"
                    }
                    visual_insights.append(scenario)
        
        # Eğer görsel içgörüleri boşsa, doğrudan document_structure'dan alıp ekle
        if len(visual_insights) == 0 and document_structure and "images" in document_structure:
            logger.warning("Görsel analizleri boş, doğrudan belge yapısından görseller ekleniyor")
            for i, raw_img in enumerate(document_structure["images"]):
                if isinstance(raw_img, dict):
                    desc = raw_img.get("alt_text", "") or raw_img.get("description", "") or f"Görsel {i+1}"
                    scenario = {
                        "title": f"Görsel {i+1} Test Senaryosu",
                        "description": f"Görselin test senaryosu: {desc[:200]}...",
                        "source": "direct_from_structure"
                    }
                    visual_insights.append(scenario)
                    logger.info(f"Belge yapısından görsel {i+1} eklendi: {desc[:100]}...")
                
        # Tablolar için aynı geliştirmeler
        table_insights = []
        logger.info(f"İşlenecek tablo sayısı: {len(table_results)}")
        for i, tbl in enumerate(table_results):
            if isinstance(tbl, dict):
                logger.info(f"Tablo {i+1} işleniyor - Anahtarlar: {', '.join(tbl.keys())}")
                
                # Standart yöntemlerle erişim dene
                if "test_scenarios" in tbl:
                    logger.info(f"Tablo {i+1}'de {len(tbl['test_scenarios'])} test senaryosu bulundu")
                    table_insights.extend(tbl["test_scenarios"])
                elif "analysis" in tbl:
                    logger.info(f"Tablo {i+1}'de analiz metin bulundu: {str(tbl['analysis'])[:100]}...")
                    table_insights.append(tbl["analysis"])
                elif "content" in tbl:
                    # Doğrudan bir senaryo oluştur
                    logger.info(f"Tablo {i+1} için content kullanılıyor")
                    content_str = str(tbl['content'])
                    scenario = {
                        "title": f"Tablo {i+1} Test Senaryosu",
                        "description": f"Tablodan çıkarılan test senaryosu: {content_str[:200]}...",
                        "source": "table_analysis"
                    }
                    table_insights.append(scenario)
                elif "caption" in tbl:
                    # Caption içeriğini kullan
                    logger.info(f"Tablo {i+1} için caption kullanılıyor: {tbl['caption'][:100]}...")
                    scenario = {
                        "title": f"Tablo {i+1} Test Senaryosu",
                        "description": f"Tablo başlığından çıkarılan test: {tbl['caption'][:200]}...",
                        "source": "table_caption"
                    }
                    table_insights.append(scenario)
                else:
                    # Tüm tablo anahtarlarını kullanarak bir senaryo oluştur
                    content = ", ".join([f"{k}: {str(v)[:50]}" for k, v in tbl.items() if k != "data"])
                    logger.info(f"Tablo {i+1} için alternatif içerik kullanılıyor: {content[:100]}...")
                    scenario = {
                        "title": f"Tablo {i+1} Test Senaryosu",
                        "description": f"Tablo içeriğinden çıkarılan test: {content[:200]}...",
                        "source": "table_analysis_raw"
                    }
                    table_insights.append(scenario)
        
        # Eğer tablo içgörüleri boşsa, doğrudan document_structure'dan alıp ekle
        if len(table_insights) == 0 and document_structure and "tables" in document_structure:
            logger.warning("Tablo analizleri boş, doğrudan belge yapısından tablolar ekleniyor")
            for i, raw_tbl in enumerate(document_structure["tables"]):
                if isinstance(raw_tbl, dict):
                    caption = raw_tbl.get("caption", "") or raw_tbl.get("title", "") or f"Tablo {i+1}"
                    content = str(raw_tbl.get("content", "") or raw_tbl.get("data", ""))
                    scenario = {
                        "title": f"Tablo {i+1} Test Senaryosu",
                        "description": f"Tablonun test senaryosu: {caption} - {content[:200]}...",
                        "source": "direct_from_structure"
                    }
                    table_insights.append(scenario)
                    logger.info(f"Belge yapısından tablo {i+1} eklendi: {caption[:100]}...")
        
        # Test senaryosu oluşturma verisi hazırla
        scenario_data = {
            "task": "generate_test_scenarios",
            "text": document_text,
            "structure": document_structure,
            "classification": classification_result.get("result", {}),
            "visual_insights": visual_insights,  # TÜM görsel içgörülerini gönder - Müşteri istedi
            "table_insights": table_insights,    # TÜM tablo içgörülerini gönder - Müşteri istedi
            "image_count": len(image_results),
            "table_count": len(table_results),
            "enhanced_context": True,
            "has_rich_content": True,  # Zengin içerik ekstra güvence 
            "forced_rich_content": True  # Zengin içerik ekstra güvence
        }
        
        # o1 modeli ile test senaryoları oluştur
        test_scenarios = self._process_with_model("technical", scenario_data)
        
        if "error" in test_scenarios:
            logger.error(f"Test senaryosu oluşturma hatası: {test_scenarios.get('error')}")
            return {"error": test_scenarios.get("error")}
            
        logger.info("Test senaryoları başarıyla oluşturuldu")
        return test_scenarios.get("result", {})
    
    def _synthesize_results(self, test_scenarios: Dict[str, Any], classification_result: Dict[str, Any],
                          image_results: List[Dict[str, Any]], table_results: List[Dict[str, Any]],
                          diagram_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tüm sonuçları birleştirip nihai sonucu oluştur
        
        Args:
            test_scenarios: Ana test senaryoları
            classification_result: Sınıflandırma sonuçları 
            image_results: İşlenmiş görsel analizleri
            table_results: İşlenmiş tablo analizleri
            diagram_results: İşlenmiş diyagram analizleri
            
        Returns:
            Birleştirilmiş sonuçlar
        """
        logger.info("Tüm analiz sonuçları gpt-4o-mini ile birleştiriliyor")
        
        # Sonuçları gpt-4o-mini ile özetleyip sentezle
        synthesis_data = {
            "task": "synthesize_results",
            "test_scenarios": test_scenarios,
            "classification": classification_result.get("result", {}),
            "image_count": len(image_results) if isinstance(image_results, list) else 0,
            "table_count": len(table_results) if isinstance(table_results, list) else 0,
            "diagram_count": len(diagram_results) if isinstance(diagram_results, list) else 0
        }
        
        # Sentezleme için belge metnini oluştur
        if isinstance(test_scenarios, dict):
            logger.debug("Test senaryoları synthesize_results için serileştiriliyor")
            try:
                # Test senaryolarını JSON formatına dönüştür (datetime uyumluluk için özel encoder kullanarak)
                try:
                    # İlk olarak JSONDateTimeEncoder ile dönüştürmeyi dene
                    logger.debug("JSONDateTimeEncoder ile JSON serileştirme başlatılıyor")
                    scenario_json = json.dumps(test_scenarios, ensure_ascii=False, cls=JSONDateTimeEncoder)
                    logger.debug(f"JSONDateTimeEncoder ile serileştirme başarılı: {len(scenario_json)} karakter")
                except Exception as json_err:
                    # İlk yöntem başarısız olursa, manuel serileştirmeyi dene
                    logger.warning(f"JSONDateTimeEncoder ile serileştirme başarısız: {str(json_err)}")
                    logger.debug("Manuel JSON serileştirme yöntemi deneniyor")
                    
                    # Yedek plan: Kendimiz dönüştürme yapalım
                    from utils.azure_service import json_serialize
                    scenario_json = json_serialize(test_scenarios)
                    logger.debug("Manuel json_serialize yöntemi ile serileştirme yapıldı")
                
                # Sentezleme için metni ata
                synthesis_data["text"] = scenario_json
                # JSON formatında yanıt istediğimizi belirtelim
                synthesis_data["require_json"] = True
                logger.debug(f"Test senaryosu metni oluşturuldu: {len(scenario_json)} karakter")
            except Exception as e:
                logger.error(f"Test senaryoları serileştirme hatası: {str(e)}")
                # Hata olsa bile boş metin ekle
                synthesis_data["text"] = "Test senaryoları işlenemedi."
        
        synthesis_result = self._process_with_model("summary", synthesis_data)
        
        # Test senaryosu sonucu kontrolü
        if isinstance(test_scenarios, dict) and "error" in test_scenarios:
            error_msg = test_scenarios.get("error", "Bilinmeyen hata")
            logger.warning(f"Test senaryosu oluşturma hatası: {error_msg}")
            
            # Test senaryosu yoksa, görsellerden ve tablolardan senaryo oluştur
            base_result = {"scenarios": []}
            
            # Görsel analiz sonuçlarından senaryo oluştur
            if image_results and len(image_results) > 0:
                logger.info(f"Görsel analiz sonuçlarından senaryo oluşturuluyor. {len(image_results)} görsel var.")
                for idx, img in enumerate(image_results):
                    # Her görselden bir test senaryosu oluştur
                    if isinstance(img, dict) and "description" in img:
                        scenario = {
                            "title": f"Görsel {idx+1} Test Senaryosu",
                            "description": f"Görselden oluşturulan test senaryosu: {img.get('description', '')[:100]}",
                            "test_cases": [
                                {
                                    "title": f"Görsel {idx+1} Doğrulama",
                                    "steps": "1. İlgili ekrana git\n2. Görseli kontrol et\n3. Görselin içeriğini doğrula",
                                    "expected_results": img.get("description", "Görsel içeriği doğru görüntülenmeli")
                                }
                            ]
                        }
                        base_result["scenarios"].append(scenario)
            
            # Tablolardan senaryo oluştur
            if table_results and len(table_results) > 0:
                logger.info(f"Tablo analiz sonuçlarından senaryo oluşturuluyor. {len(table_results)} tablo var.")
                for idx, tbl in enumerate(table_results):
                    # Her tablodan bir test senaryosu oluştur
                    if isinstance(tbl, dict) and "caption" in tbl:
                        scenario = {
                            "title": f"Tablo {idx+1} Test Senaryosu",
                            "description": f"Tablodan oluşturulan test senaryosu: {tbl.get('caption', '')[:100]}",
                            "test_cases": [
                                {
                                    "title": f"Tablo {idx+1} Doğrulama",
                                    "steps": "1. İlgili ekrana git\n2. Tabloyu kontrol et\n3. Tablonun verilerini doğrula",
                                    "expected_results": tbl.get("caption", "Tablo içeriği doğru görüntülenmeli")
                                }
                            ]
                        }
                        base_result["scenarios"].append(scenario)
            
            # Hiçbir veri yoksa, temel bir sonuç döndür
            if len(base_result["scenarios"]) == 0:
                base_result["scenarios"].append({
                    "title": "Temel İşlevsellik Testi",
                    "description": "Belge içeriğinden otomatik senaryo oluşturulamadı. Temel işlevsellik testi senaryosu.",
                    "test_cases": [
                        {
                            "title": "Temel İşlevsellik Kontrolü",
                            "steps": "1. Sisteme giriş yap\n2. Ana sayfaya git\n3. Temel işlevleri kontrol et",
                            "expected_results": "Sistem temel işlevleri sorunsuz çalışmalı"
                        }
                    ]
                })
            
            # Özet ekle
            base_result["summary"] = f"Belgeden otomatik senaryo üretildi. Toplam: {len(base_result['scenarios'])} senaryo."
            final_result = base_result
            
        elif "error" in synthesis_result:
            logger.warning(f"Sonuç sentezleme hatası: {synthesis_result.get('error')}")
            # Sentezleme başarısız olsa bile mevcut sonuçları birleştir
            final_result = test_scenarios
        else:
            # Sentez sonucunu al
            final_result = synthesis_result.get("result", test_scenarios)
            
        # Görsel analizlerini sonuca ekle
        if image_results and isinstance(image_results, list):
            logger.debug(f"Görsel analiz sonuçları birleştiriliyor. Toplam: {len(image_results)} görsel")
            final_result["visual_analysis"] = {
                "count": len(image_results),
                "results": image_results
            }
        elif image_results:
            logger.warning(f"Görsel analiz sonuçları liste değil! Tip: {type(image_results)}")
            if isinstance(image_results, dict):
                final_result["visual_analysis"] = image_results
            
        # Tablo analizlerini sonuca ekle
        if table_results and isinstance(table_results, list):
            logger.debug(f"Tablo analiz sonuçları birleştiriliyor. Toplam: {len(table_results)} tablo")
            final_result["table_analysis"] = {
                "count": len(table_results),
                "results": table_results
            }
        elif table_results:
            logger.warning(f"Tablo analiz sonuçları liste değil! Tip: {type(table_results)}")
            if isinstance(table_results, dict):
                final_result["table_analysis"] = table_results
            
        # Diyagram analizlerini sonuca ekle
        if diagram_results and isinstance(diagram_results, list):
            logger.debug(f"Diyagram analiz sonuçları birleştiriliyor. Toplam: {len(diagram_results)} diyagram")
            final_result["diagram_analysis"] = {
                "count": len(diagram_results),
                "results": diagram_results
            }
        elif diagram_results:
            logger.warning(f"Diyagram analiz sonuçları liste değil! Tip: {type(diagram_results)}")
            if isinstance(diagram_results, dict):
                final_result["diagram_analysis"] = diagram_results
        
        # Doküman sınıflandırmasını ekle
        if "result" in classification_result:
            final_result["document_classification"] = classification_result["result"]
        
        logger.info("Tüm analiz sonuçları başarıyla birleştirildi")
        return final_result
    
    def _fallback_processing(self, document_text: str, document_structure: Dict[str, Any], 
                           base_model: str) -> Dict[str, Any]:
        """
        Hata durumunda tek bir model ile işleme devam et
        
        Args:
            document_text: İşlenecek doküman metni
            document_structure: Dokümanın yapısal bilgileri
            base_model: Temel AI modeli
            
        Returns:
            İşlenmiş sonuçlar
        """
        logger.warning(f"Çoklu model işleme başarısız. Tek model ({base_model}) kullanılıyor")
        
        try:
            from utils.azure_service import generate_with_azure
            
            # Görsel içerik kontrol et
            has_images = False
            has_tables = False
            images_for_scenarios = []
            tables_for_scenarios = []
            
            # Belgede görsel olup olmadığını kontrol et
            if document_structure and "images" in document_structure and document_structure["images"]:
                has_images = True
                images_for_scenarios = document_structure["images"]
                logger.info(f"Belgede görsel içerik mevcut: {len(document_structure['images'])} görsel")
            
            # Belgede tablo olup olmadığını kontrol et
            if document_structure and "tables" in document_structure and document_structure["tables"]:
                has_tables = True
                tables_for_scenarios = document_structure["tables"]
                logger.info(f"Belgede tablo içerik mevcut: {len(document_structure['tables'])} tablo")
            
            # Azure için context oluştur
            context = {
                "text": document_text,
                "structure": document_structure,
                "azure_model": base_model,
                "fallback": True,
                "preserve_all": True  # Tüm içeriği koru
            }
            
            # Zengin içerik bilgisini ekle
            if has_images or has_tables:
                context["has_rich_content"] = True
                
                if has_images:
                    context["images"] = images_for_scenarios
                    context["image_count"] = len(images_for_scenarios)
                    
                if has_tables:
                    context["tables"] = tables_for_scenarios
                    context["table_count"] = len(tables_for_scenarios)
            
            # Azure servisi ile işlemeyi dene
            result = generate_with_azure(context)
            
            # Eğer sonuç yoksa ve zengin içerik varsa, yalnızca zengin içerikle yeniden dene
            if (not result or (isinstance(result, dict) and "error" in result)) and (has_images or has_tables):
                logger.warning("Ana işleme başarısız oldu, yalnızca zengin içerikle (görsel/tablo) yeniden deneniyor")
                
                # Metin içeriğini boşalt, yalnızca görsel/tablo içeriklerini kullan
                context["text"] = ""
                context["rich_content_only"] = True
                
                # Zengin içerik üzerine daha fazla vurgu yap
                context["rich_content_focus"] = True
                
                # Tekrar dene
                result = generate_with_azure(context)
            
            # Hala başarısız olursa temel bir sonuç döndür
            if not result or (isinstance(result, dict) and "error" in result):
                logger.error(f"Fallback işlem de başarısız oldu")
                
                # Çok basit bir sonuç oluştur
                basic_result = {
                    "summary": "Belge işlenemedi ancak temel bir test senaryosu oluşturuldu.",
                    "scenarios": [
                        {
                            "title": "Temel İşlevsellik Testi",
                            "description": "Belge içeriğinden otomatik senaryo oluşturulamadı. Temel işlevsellik testi senaryosu.",
                            "test_cases": [
                                {
                                    "title": "Temel İşlevsellik Kontrolü",
                                    "steps": "1. Sisteme giriş yap\n2. Ana sayfaya git\n3. Temel işlevleri kontrol et",
                                    "expected_results": "Sistem temel işlevleri sorunsuz çalışmalı"
                                }
                            ]
                        }
                    ]
                }
                
                # Görsel varsa ekle
                if has_images:
                    for i, img in enumerate(images_for_scenarios[:3]):  # En fazla 3 görsel için
                        if isinstance(img, dict):
                            img_desc = img.get("description", f"Görsel {i+1}")
                            
                            scenario = {
                                "title": f"Görsel {i+1} Testi",
                                "description": f"Belgede bulunan görsel için test senaryosu: {img_desc[:100]}",
                                "test_cases": [
                                    {
                                        "title": f"Görsel {i+1} Kontrolü",
                                        "steps": "1. İlgili ekrana git\n2. Görseli kontrol et",
                                        "expected_results": "Görsel doğru şekilde görüntüleniyor"
                                    }
                                ]
                            }
                            basic_result["scenarios"].append(scenario)
                
                # Tablo varsa ekle
                if has_tables:
                    for i, tbl in enumerate(tables_for_scenarios[:3]):  # En fazla 3 tablo için
                        if isinstance(tbl, dict):
                            tbl_desc = tbl.get("caption", f"Tablo {i+1}")
                            
                            scenario = {
                                "title": f"Tablo {i+1} Testi",
                                "description": f"Belgede bulunan tablo için test senaryosu: {tbl_desc[:100]}",
                                "test_cases": [
                                    {
                                        "title": f"Tablo {i+1} Veri Kontrolü",
                                        "steps": "1. İlgili ekrana git\n2. Tablo verilerini kontrol et",
                                        "expected_results": "Tablo verileri doğru şekilde görüntüleniyor"
                                    }
                                ]
                            }
                            basic_result["scenarios"].append(scenario)
                
                return basic_result
                
            # Sonuçları döndür
            return result
            
        except Exception as e:
            logger.error(f"Fallback işleme hatası: {str(e)}")
            
            # En basit sonuç formatını döndür
            return {
                "summary": "Belge işlenemedi.",
                "scenarios": [
                    {
                        "title": "Temel Test Senaryosu",
                        "description": "Belge işlenemedi, temel bir test senaryosu sunuluyor.",
                        "test_cases": [
                            {
                                "title": "Temel İşlev Testi",
                                "steps": "1. Sisteme giriş yap\n2. Ana işlevselliği kontrol et",
                                "expected_results": "Sistem çalışıyor olmalı"
                            }
                        ]
                    }
                ]
            }