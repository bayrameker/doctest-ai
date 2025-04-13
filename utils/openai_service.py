"""
OpenAI Service Integration for the application
"""

import os
import json
import logging
import time
import base64
import openai
from openai import OpenAI
from typing import Dict, Optional, Any, Union

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_with_model(model: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenAI API ile belirli bir model kullanarak veri işle
    
    Args:
        model: Kullanılacak OpenAI modeli (örn. gpt-4o)
        data: İşlenecek veri ve görev bilgileri
            
    Returns:
        İşlenmiş sonuçlar
    """
    try:
        # OpenAI modülü zaten import edildi
        
        # OpenAI API anahtarı
        api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Eğer ortam değişkenlerinde yoksa, config manager'dan almayı dene
        if not api_key:
            try:
                from utils.config import config_manager
                api_key = config_manager.get_api_key("openai")
            except Exception as e:
                logger.warning(f"Config manager'dan API anahtarı alınamadı: {e}")
        
        if not api_key:
            logger.error("OpenAI API anahtarı bulunamadı")
            return {"error": "OpenAI API anahtarı gerekli fakat bulunamadı"}
        
        # OpenAI istemcisi oluştur
        client = OpenAI(api_key=api_key)
        
        # Görev türünü belirle
        task = data.get("task", "general")
        logger.info(f"Processing with OpenAI {model} for task: {task}")
        
        # İşlem türüne göre farklı mantık uygula
        if task == "image_analysis":
            return _process_image_with_openai(client, model, data)
        elif task == "document_classification":
            return _process_classification_with_openai(client, model, data)
        elif task == "generate_test_scenarios":
            return _generate_test_scenarios_with_openai(client, model, data)
        else:
            # Genel amaçlı işleme
            return _process_general_with_openai(client, model, data)
        
    except ImportError:
        logger.error("OpenAI package not installed or not accessible")
        return {"error": "OpenAI package not installed"}
    except Exception as e:
        logger.error(f"Error processing with OpenAI: {str(e)}")
        return {"error": str(e)}

def _process_image_with_openai(client, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI ile görsel analizi yap"""
    try:
        # Görsel verisi veya URL'sini kontrol et
        image_data = data.get("image", {})
        if not image_data:
            return {"error": "No image data provided"}
        
        # Görsel URL'si veya Base64 kodlaması burada alınır
        image_url = image_data.get("url", "")
        image_base64 = image_data.get("base64", "")
        
        if not image_url and not image_base64:
            return {"error": "Image URL or base64 data is required"}
        
        # Bağlam bilgisini ayarla
        context = data.get("context", {})
        document_type = context.get("document_type", "")
        document_purpose = context.get("document_purpose", "")
        page_number = context.get("page_number", 0)
        
        # Sistem talimatı
        system_instruction = f"""
        Bu görsel bir test senaryosu oluşturma projesi kapsamında analiz edilecektir.
        Görselden test senaryoları ve kullanım durumları çıkarın.
        
        Belge türü: {document_type}
        Belge amacı: {document_purpose} 
        Sayfa: {page_number}
        
        Görseli detaylı analiz edin ve aşağıdaki yapıda JSON çıktı oluşturun:
        
        {{
            "image_type": "Görselin türü (ekran görüntüsü, diyagram, şema, tablo, vb.)",
            "description": "Görselin kısa açıklaması",
            "test_relevance": "Görselin test senaryoları için önemi (Düşük/Orta/Yüksek)",
            "ui_elements": ["Görselde tespit edilen UI öğeleri listesi"],
            "test_scenarios": [
                {{
                    "title": "Test senaryosu başlığı",
                    "description": "Kısa açıklama",
                    "test_cases": [
                        {{
                            "title": "Test durumu başlığı",
                            "steps": "1. Adım 1\\n2. Adım 2\\n3. Adım 3",
                            "expected_results": "Beklenen sonuç"
                        }}
                    ]
                }}
            ],
            "extracted_text": "Görselden çıkarılan metin (varsa)"
        }}
        
        Görsel bir tablo içeriyorsa, tablodaki verileri de yapılandırılmış formatta çıkarın.
        """
        
        # Kullanıcı talimatı 
        user_instruction = "Bu görseli test senaryoları oluşturma bağlamında analiz edin. Görselde gördüğünüz ekran, süreç, diyagram veya tablodan test senaryoları çıkarın."
        
        # Görsel verisi içeren mesaj oluştur
        message_content = [{"type": "text", "text": user_instruction}]
        
        # Görsel URL veya base64 verisi ekle
        if image_url:
            # String tipindeki mesaj içeriğini doğrudan ekleyemiyoruz, önce uygun formatta bir nesneye dönüştürüyoruz
            message_content = [
                {"type": "text", "text": user_instruction},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        elif image_base64:
            # String tipindeki mesaj içeriğini doğrudan ekleyemiyoruz, önce uygun formatta bir nesneye dönüştürüyoruz
            message_content = [
                {"type": "text", "text": user_instruction},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        
        # API isteği yap
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message_content}
            ],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Yanıtı işle
        if response and response.choices:
            content = response.choices[0].message.content
            try:
                # JSON içeriği çıkar
                result = json.loads(content)
                logger.info(f"Successfully analyzed image with OpenAI {model}")
                return {"result": result, "model": model, "task": "image_analysis"}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from OpenAI")
                return {"error": "JSON parsing error", "raw_content": content[:500]}
        else:
            logger.error("Empty or invalid response from OpenAI")
            return {"error": "Empty or invalid response"}
        
    except Exception as e:
        logger.error(f"Error in image processing with OpenAI: {str(e)}")
        return {"error": str(e)}

def _process_classification_with_openai(client, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI ile metin sınıflandırması yap"""
    try:
        # Metin verisini kontrol et
        text = data.get("text", "")
        if not text:
            return {"error": "No text data provided"}
        
        # Metin büyükse kısalt
        if len(text) > 10000:
            text = text[:10000] + "..."
            logger.info(f"Text truncated to {len(text)} characters for classification")
        
        # Sistem talimatı
        system_instruction = """
        Bu bir belge sınıflandırma görevidir. Verilen metni analiz ederek türünü, amacını ve
        önemli özelliklerini belirlemeniz gerekiyor.
        
        Çıktıyı aşağıdaki JSON formatında verin:
        
        {
            "document_type": "Belge türü (gereksinim, kullanım kılavuzu, API dokümanı, vb.)",
            "document_purpose": "Belgenin amacı",
            "document_category": "Teknik/İş/Süreç/Kullanıcı/vb.",
            "primary_audience": "Hedef kitle (Geliştiriciler, Son Kullanıcılar, Yöneticiler, vb.)",
            "complexity_level": "Belge karmaşıklık seviyesi (Düşük/Orta/Yüksek)",
            "main_topics": ["Ana konu 1", "Ana konu 2", "..."],
            "test_focus_areas": ["Test odak alanı 1", "Test odak alanı 2", "..."],
            "related_system_components": ["İlgili sistem bileşeni 1", "İlgili sistem bileşeni 2", "..."]
        }
        
        Tüm alanları doldurun ve Türkçe olarak yanıt verin.
        """
        
        # API isteği yap
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ],
            max_tokens=1000,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Yanıtı işle
        if response and response.choices:
            content = response.choices[0].message.content
            try:
                # JSON içeriği çıkar
                result = json.loads(content)
                logger.info(f"Successfully classified document with OpenAI {model}")
                return {"result": result, "model": model, "task": "classification"}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from OpenAI")
                return {"error": "JSON parsing error", "raw_content": content[:500]}
        else:
            logger.error("Empty or invalid response from OpenAI")
            return {"error": "Empty or invalid response"}
        
    except Exception as e:
        logger.error(f"Error in classification with OpenAI: {str(e)}")
        return {"error": str(e)}

def _generate_test_scenarios_with_openai(client, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI ile test senaryoları oluştur"""
    try:
        # Metin verisini kontrol et
        text = data.get("text", "")
        if not text:
            return {"error": "No text data provided"}
        
        # Metin büyükse kısalt (gpt-4o 128K token desteğine sahip)
        max_chars = 100000 if model == "gpt-4o" else 50000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.info(f"Text truncated to {len(text)} characters for test scenario generation")
        
        # Ek bağlam bilgilerini al
        structure = data.get("structure", {})
        classification = data.get("classification", {})
        visual_insights = data.get("visual_insights", [])
        table_insights = data.get("table_insights", [])
        
        # Sistem talimatı
        system_instruction = """
        Sen test senaryoları oluşturma konusunda uzmanlaşmış bir yapay zeka asistanısın.
        Belgeleri analiz ederek kapsamlı test senaryoları ve test durumları üretiyorsun.
        Türkçe dilinde profesyonel ve teknik açıdan doğru test senaryoları oluştur.
        
        Aşağıdaki formatı kullan:
        
        {
            "summary": "Belgenin kapsamlı bir özeti",
            "scenarios": [
                {
                    "title": "Senaryo Başlığı",
                    "description": "Senaryonun açıklaması",
                    "priority": "Yüksek/Orta/Düşük",
                    "category": "Fonksiyonel/Performans/Güvenlik/Kullanılabilirlik",
                    "test_cases": [
                        {
                            "title": "Test Durumu Başlığı",
                            "type": "Pozitif/Negatif",
                            "steps": "1. Adım 1\\n2. Adım 2\\n3. Adım 3",
                            "expected_results": "Beklenen sonuçların açıklaması",
                            "preconditions": "Ön koşullar"
                        }
                    ]
                }
            ]
        }
        
        Test senaryoları oluştururken şunlara DİKKAT ET:
        1. Dokümanın TÜM içeriğini dikkate alarak kapsamlı senaryolar oluştur
        2. Her fonksiyon, özellik ve gereksinim için mutlaka en az bir test senaryosu olmalı
        3. Hem pozitif hem de negatif test senaryolarını dahil et
        4. Her bir senaryo için detaylı ve eksiksiz test adımları oluştur (atlamadan belgenin uygulanabilir tüm unsurlarını test et)
        5. Belgede herhangi bir teknik veya fonksiyonel belirtim varsa, bunların doğrulanması için test senaryoları oluştur
        6. Senaryolar için mutlaka anlamlı başlıklar, açıklamalar ve öncelik düzeyleri belirle
        7. Belgedeki görseller, ekran görüntüleri veya diyagramlarda belirtilen her işlev için test senaryoları ekle
        8. Tekrar eden senaryolar yerine, belgenin her bölümünü kapsayan özgün senaryolar oluştur
        9. Sonuçta test senaryoları ve test durumları teknik açıdan uygulanabilir ve doğrulanabilir olmalı
        10. Belgedeki TÜM gereksinimleri kapsayan test senaryoları oluşturduğundan emin ol
        """
        
        # Görsel ve tablo bilgilerini içeren ek bağlam oluştur
        additional_context = ""
        
        # Sınıflandırma bilgilerini ekle
        if classification:
            additional_context += "\n\n### Belge Sınıflandırma Bilgileri ###\n"
            for key, value in classification.items():
                if isinstance(value, list):
                    additional_context += f"{key}: {', '.join(value)}\n"
                else:
                    additional_context += f"{key}: {value}\n"
        
        # Görsel içgörülerini ekle
        if visual_insights:
            additional_context += "\n\n### Görsel Analiz İçgörüleri ###\n"
            for i, insight in enumerate(visual_insights):
                additional_context += f"{i+1}. {insight}\n"
        
        # Tablo içgörülerini ekle
        if table_insights:
            additional_context += "\n\n### Tablo Analiz İçgörüleri ###\n"
            for i, insight in enumerate(table_insights):
                additional_context += f"{i+1}. {insight}\n"
        
        # Belgeyi analiz etmek için daha detaylı kullanıcı yönergesi
        detailed_user_instruction = f"""
        Lütfen aşağıdaki belgeyi detaylı bir şekilde analiz et ve kapsamlı test senaryoları oluştur. 
        Bu işi yaparken belgenin her bölümünü dikkate al ve TÜM teknik gereksinimler, özellikler ve fonksiyonlar için test senaryoları oluştur.
        
        Belge içeriğinde şunlar için özellikle dikkat et:
        - Tüm fonksiyonel gereksinimleri kapsayacak şekilde test senaryoları
        - Kullanıcı arayüzü özellikleri ve bileşenleri
        - Veri doğrulama ve kontrol mekanizmaları
        - Hata durumları ve geçersiz veri girişleri
        - İş akışları ve süreç adımları
        - Entegrasyon noktaları ve sistem bağlantıları
        
        NOT: Her bir fonksiyon ve özellik için mutlaka en az bir pozitif ve bir negatif test senaryosu oluştur.
        
        === BELGE İÇERİĞİ ===
        {text}
        
        === EK BAĞLAM BİLGİLERİ ===
        {additional_context}
        """
        
        # API isteği yap
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": detailed_user_instruction}
            ],
            max_tokens=4000,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Yanıtı işle
        if response and response.choices:
            content = response.choices[0].message.content
            try:
                # JSON içeriği çıkar
                result = json.loads(content)
                logger.info(f"Successfully generated test scenarios with OpenAI {model}")
                return {"result": result, "model": model, "task": "test_scenarios"}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from OpenAI")
                return {"error": "JSON parsing error", "raw_content": content[:500]}
        else:
            logger.error("Empty or invalid response from OpenAI")
            return {"error": "Empty or invalid response"}
        
    except Exception as e:
        logger.error(f"Error in test scenario generation with OpenAI: {str(e)}")
        return {"error": str(e)}

def _process_general_with_openai(client, model: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI ile genel amaçlı işleme yap"""
    try:
        # İstek içeriğini kontrol et
        content = data.get("content", "")
        if not content:
            return {"error": "No content provided"}
        
        # İsteğe bağlı parametreleri al
        system_instruction = data.get("system_instruction", "Sen yardımcı bir yapay zeka asistanısın.")
        temperature = data.get("temperature", 0.2)
        max_tokens = data.get("max_tokens", 1000)
        response_format = data.get("response_format", {"type": "json_object"})
        
        # API isteği yap
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": content}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format
        )
        
        # Yanıtı işle
        if response and response.choices:
            content = response.choices[0].message.content
            
            # Yanıt formatı JSON ise, parse et
            if response_format.get("type") == "json_object":
                try:
                    result = json.loads(content)
                    return {"result": result, "model": model, "task": "general"}
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from OpenAI")
                    return {"error": "JSON parsing error", "raw_content": content[:500]}
            else:
                # Düz metin yanıtı
                return {"result": {"content": content}, "model": model, "task": "general"}
        else:
            logger.error("Empty or invalid response from OpenAI")
            return {"error": "Empty or invalid response"}
            
    except Exception as e:
        logger.error(f"Error in general processing with OpenAI: {str(e)}")
        return {"error": str(e)}

def generate_with_openai(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate test scenarios using OpenAI
    
    Args:
        context (dict): The context data for generating scenarios
        
    Returns:
        dict: Structured test scenarios
    """
    # Eski arayüz (geriye dönük uyumluluk için)
    data = {
        "task": "generate_test_scenarios",
        "text": context.get("text", ""),
        "structure": context.get("structure", {}),
        "enhanced_context": context.get("enhanced_context", False)
    }
    
    result = process_with_model("gpt-4o", data)
    
    if "error" in result:
        logger.error(f"Error generating with OpenAI: {result['error']}")
        # Hata yapısı yerine eski API uyumlu yanıt dön
        return {
            "error": result["error"],
            "scenarios": []
        }
    
    # Sonucu eski format uyumlu yap
    if "result" in result:
        return result["result"]
    else:
        return {
            "error": "Unknown error in OpenAI processing",
            "scenarios": []
        }
    
def analyze_image_with_openai(
    image_base64: str, 
    system_prompt: Optional[str] = None, 
    user_prompt: Optional[str] = None,
    model: Optional[str] = "gpt-4o",
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    OpenAI servisi kullanarak görseli analiz eder
    
    Args:
        image_base64: Base64 formatında görsel
        system_prompt: Sistem prompt
        user_prompt: Kullanıcı prompt
        model: Kullanılacak model adı
        temperature: Üretilen yanıtın çeşitliliği (0-1)
        
    Returns:
        Analiz sonucunu içeren sözlük
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    if not system_prompt:
        system_prompt = "Bu görseli test senaryoları için analiz et"
        
    if not user_prompt:
        user_prompt = "Bu görseli analiz ederek test senaryoları için kullanılabilecek bilgileri çıkar"
    
    try:
        from openai import OpenAI
        
        # OpenAI API anahtarı
        api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Eğer ortam değişkenlerinde yoksa, config manager'dan almayı dene
        if not api_key:
            try:
                from utils.config import config_manager
                api_key = config_manager.get_api_key("openai")
            except Exception as e:
                logger.warning(f"Config manager'dan API anahtarı alınamadı: {e}")
        
        if not api_key:
            logger.error("OpenAI API anahtarı bulunamadı")
            return {"error": "OpenAI API anahtarı gerekli fakat bulunamadı"}
        
        # OpenAI istemcisi oluştur
        client = OpenAI(api_key=api_key)
        
        # Görsel için istek hazırla
        message_content = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        
        # API isteği yap
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_content}
            ],
            max_tokens=1000,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        # Yanıtı işle
        if response and response.choices:
            content = response.choices[0].message.content
            try:
                # Metni JSON olarak ayrıştırma denemesi
                result = json.loads(content)
                return {
                    "text": content,
                    "json": result,
                    "model": model,
                    "analysis_time": time.time() - start_time
                }
            except json.JSONDecodeError:
                # JSON ayrıştırma başarısız olursa sadece metin olarak döndür
                return {
                    "text": content,
                    "model": model,
                    "analysis_time": time.time() - start_time
                }
        else:
            logger.error("Empty or invalid response from OpenAI")
            return {"error": "Empty or invalid response from OpenAI"}
            
    except ImportError:
        logger.error("OpenAI package not installed or not accessible")
        return {"error": "OpenAI package not installed"}
    except Exception as e:
        logger.error(f"Görsel analizi sırasında hata (OpenAI): {str(e)}")
        return {"error": f"Görsel analizi sırasında hata: {str(e)}"}
