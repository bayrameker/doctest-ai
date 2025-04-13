"""
Gelişmiş görsel işleme modülü (Advanced Image Processor)
Döküman içindeki görselleri derin anlayış için GPT4o veya benzeri çoklu modlu modeller ile işler
"""

import os
import io
import base64
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from PIL import Image

logger = logging.getLogger(__name__)

# Görsel işleme için varsayılan istek metnini hazırla
DEFAULT_IMAGE_SYSTEM_PROMPT = """
Belgedeki görselleri analiz ederek test senaryoları için SADECE değerli bilgileri çıkar.
Görseli titizlikle incele ve aşağıdakilere odaklan:
1. Arayüz öğeleri: butonlar, formlar, girdi alanları, menüler
2. İş akışları: kullanıcı akışları, süreç akışları
3. İşlevsel gereksinimler: ekran ne yapmalı
4. Test edilebilir özellikler: kontrol edilebilir davranışlar

YAPMA:
- OCR çıktısı verme - yalnızca test senaryolarıyla ilgili içeriği açıkla
- Görsel özellikleri anlatma (renkler, kompozisyon vs)
- Görüntü kalitesi hakkında yorum yapma

ÇIKTI:
JSON formatında yapılandırılmış olarak döndür:
- "screen_name": Ekranın adı (tahmin et)
- "functionality": Ana işlevler
- "test_points": Test edilmesi gereken özellikler (liste)
- "ui_elements": Arayüzdeki önemli öğeler (liste)
"""

DEFAULT_IMAGE_USER_PROMPT = """
Bu ekran görüntüsünü test perspektifinden analiz et. 
Görsel içeriği kullanarak potansiyel test senaryoları için gerekli bilgileri çıkar.
Analizi JSON formatında döndür.
"""

def encode_image_to_base64(image_path: str) -> str:
    """Görsel dosyasını base64'e dönüştür"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Base64 kodlama hatası: {str(e)}")
        return ""

def encode_pil_image_to_base64(image: Image.Image) -> str:
    """PIL görsel nesnesini base64'e dönüştür"""
    try:
        buffered = io.BytesIO()
        # JPEG formatına dönüştür - daha küçük boyut için
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
    except Exception as e:
        logger.error(f"PIL görsel base64 kodlama hatası: {str(e)}")
        return ""

def process_images_with_model(
    images: List[Union[str, Image.Image, Dict[str, Any]]],
    model_type: str = "azure",
    model_name: Optional[str] = "o4",
    batch_size: int = 3,
    parallel: bool = False
) -> List[Dict[str, Any]]:
    """
    Görsel listesini yapay zeka modeliyle işle
    
    Args:
        images: İşlenecek görseller - dosya yolları, PIL görsel nesneleri veya görsel bilgisi içeren sözlükler
        model_type: Kullanılacak model tipi ('azure', 'openai' veya 'ollama')
        model_name: Kullanılacak model adı 
        batch_size: Batch işleme için grup boyutu
        parallel: Paralel işleme yapılsın mı
        
    Returns:
        İşlenmiş görsel analizlerinin listesi
    """
    results = []
    
    # Görselleri batch'lere ayır (bellek verimli işleme için)
    image_batches = [images[i:i+batch_size] for i in range(0, len(images), batch_size)]
    logger.info(f"Toplamda {len(images)} görsel {len(image_batches)} batche ayrıldı (batch boyutu: {batch_size})")
    
    # Her batch için işleme yap
    for batch_idx, image_batch in enumerate(image_batches):
        logger.info(f"Batch {batch_idx+1}/{len(image_batches)} işleniyor ({len(image_batch)} görsel)")
        
        batch_results = []
        batch_start_time = time.time()
        
        # Parallel veya sıralı işleme
        if parallel:
            # TODO: Paralel işleme gerçekleştir (gerekirse threading/asyncio)
            # Bu bölüm şimdilik sıralı olarak işliyor
            for img_idx, img in enumerate(image_batch):
                result = _process_single_image(img, model_type, model_name)
                batch_results.append(result)
        else:
            # Sıralı işleme
            for img_idx, img in enumerate(image_batch):
                result = _process_single_image(img, model_type, model_name)
                batch_results.append(result)
        
        batch_duration = time.time() - batch_start_time
        logger.info(f"Batch {batch_idx+1} tamamlandı - {batch_duration:.2f} saniye ({batch_duration/len(image_batch):.2f} saniye/görsel)")
        
        results.extend(batch_results)
    
    return results

def _process_single_image(
    image: Union[str, Image.Image, Dict[str, Any]],
    model_type: str = "azure", 
    model_name: Optional[str] = "o4"
) -> Dict[str, Any]:
    """
    Tek bir görseli yapay zeka modeli ile işle
    
    Args:
        image: İşlenecek görsel - dosya yolu, PIL görsel nesnesi veya görsel bilgisi içeren sözlük 
        model_type: Kullanılacak model tipi
        model_name: Kullanılacak model adı
        
    Returns:
        Görsel analizi içeren sözlük
    """
    start_time = time.time()
    
    # Görsel girdisini normalize et ve base64 kodlamasını al
    image_b64 = None
    image_metadata = {}
    
    if isinstance(image, str):
        # Dosya yolu
        image_b64 = encode_image_to_base64(image)
        image_metadata = {"source": "file", "path": image}
    elif isinstance(image, Image.Image):
        # PIL görsel nesnesi
        image_b64 = encode_pil_image_to_base64(image)
        image_metadata = {
            "source": "pil_image", 
            "dimensions": {"width": image.width, "height": image.height},
            "mode": image.mode
        }
    elif isinstance(image, dict) and "image" in image:
        # Görsel ve metadata içeren sözlük
        if isinstance(image["image"], Image.Image):
            image_b64 = encode_pil_image_to_base64(image["image"])
        else:
            logger.error("Desteklenmeyen görsel formatı: sözlük içindeki 'image' alanı PIL.Image nesnesi olmalı")
            return {"error": "Desteklenmeyen görsel formatı"}
        
        # Sözlükteki diğer metadata'ları kopyala
        image_metadata = {k: v for k, v in image.items() if k != "image"}
    else:
        logger.error(f"Desteklenmeyen görsel formatı: {type(image)}")
        return {"error": "Desteklenmeyen görsel formatı"}
    
    if not image_b64:
        logger.error("Görsel base64 kodlaması başarısız")
        return {"error": "Görsel base64 kodlaması başarısız"}
    
    # Model tipi bazında uygun servisi çağır
    result = {}
    
    try:
        if model_type.lower() == "azure":
            from utils.azure_service import analyze_image_with_azure
            
            result = analyze_image_with_azure(
                image_b64, 
                system_prompt=DEFAULT_IMAGE_SYSTEM_PROMPT,
                user_prompt=DEFAULT_IMAGE_USER_PROMPT,
                model=model_name or "o4"
            )
        elif model_type.lower() == "openai":
            from utils.openai_service import analyze_image_with_openai
            
            result = analyze_image_with_openai(
                image_b64,
                system_prompt=DEFAULT_IMAGE_SYSTEM_PROMPT,
                user_prompt=DEFAULT_IMAGE_USER_PROMPT,
                model=model_name or "gpt-4o"
            )
        elif model_type.lower() == "ollama":
            from utils.ollama_service import analyze_image_with_ollama
            
            result = analyze_image_with_ollama(
                image_b64,
                system_prompt=DEFAULT_IMAGE_SYSTEM_PROMPT,
                user_prompt=DEFAULT_IMAGE_USER_PROMPT,
                model=model_name or "llava"
            )
        else:
            logger.error(f"Desteklenmeyen model tipi: {model_type}")
            return {"error": f"Desteklenmeyen model tipi: {model_type}"}
    except Exception as e:
        logger.error(f"Görsel analizi sırasında hata: {str(e)}")
        return {"error": f"Görsel analizi sırasında hata: {str(e)}"}
    
    # Orijinal metadata'yı ekle
    result["metadata"] = image_metadata
    result["processing_time"] = time.time() - start_time
    
    return result

def normalize_image_analysis_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Farklı model çıktıları için normalize edilmiş sonuç formatı sağla
    
    Args:
        result: Model çıktısı 
        
    Returns:
        Normalize edilmiş sonuç formatı
    """
    normalized = {
        "screen_name": "",
        "functionality": "",
        "test_points": [],
        "ui_elements": []
    }
    
    # Hata durumlarını işle
    if "error" in result:
        normalized["error"] = result["error"]
        return normalized
    
    try:
        # Sonuç metni varsa içindeki JSON'u çözümle
        if "text" in result and isinstance(result["text"], str):
            try:
                # Metnin tamamını JSON olarak çözümlemeyi dene
                parsed_json = json.loads(result["text"])
                
                # Tüm alanları al
                normalized.update(parsed_json)
            except json.JSONDecodeError:
                # İlk aşama başarısız oldu, JSON bloğunu bulmayı dene
                import re
                json_pattern = r'\{[\s\S]*\}'
                json_matches = re.findall(json_pattern, result["text"])
                
                if json_matches:
                    try:
                        parsed_json = json.loads(json_matches[0])
                        normalized.update(parsed_json)
                    except json.JSONDecodeError:
                        # Düzgün bir JSON bulunamadı, çıktıyı metin olarak al
                        normalized["raw_text"] = result["text"]
                else:
                    normalized["raw_text"] = result["text"]
        
        # Özgün metadata'yı koru
        if "metadata" in result:
            normalized["metadata"] = result["metadata"]
        
        # İşlem süresini koru
        if "processing_time" in result:
            normalized["processing_time"] = result["processing_time"]
    except Exception as e:
        logger.error(f"Sonuç normalizasyonu sırasında hata: {str(e)}")
        normalized["error"] = f"Sonuç normalizasyonu hatası: {str(e)}"
        normalized["raw_result"] = result
    
    return normalized

def batch_process_document_images(
    document_content: Dict[str, Any],
    model_type: str = "azure",
    model_name: Optional[str] = "o4",
    batch_size: int = 3,
    parallel: bool = False
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Belge içindeki tüm görselleri toplu işle
    
    Args:
        document_content: DocumentContent nesnesini temsil eden sözlük yapısı
        model_type: Kullanılacak model tipi
        model_name: Kullanılacak model adı
        batch_size: Batch işleme boyutu
        parallel: Paralel işleme yapılsın mı
        
    Returns:
        Tuple olarak (zenginleştirilmiş belge içeriği, görsel analizleri listesi)
    """
    # Sonuca eklenecek analizleri tutacak liste
    image_analyses = []
    
    try:
        # Belge içeriğinde "elements" listesi var mı kontrol et
        if "elements" not in document_content:
            logger.warning("document_content içerisinde 'elements' listesi bulunamadı")
            return document_content, []
        
        # Tüm görsel öğelerini topla
        images = []
        image_indices = []
        
        for idx, element in enumerate(document_content["elements"]):
            # Sadece görsel tipindeki öğeleri işle
            if element.get("type") == "image" and "content" in element:
                try:
                    # PIL görselini al
                    if isinstance(element["content"], Image.Image):
                        # Görsel ve metadata bilgisiyle sözlük oluştur
                        image_info = {
                            "image": element["content"],
                            "description": element.get("description", ""),
                            "index": idx,
                            "element_id": element.get("id", f"image_{idx}"),
                            "section": element.get("section", None),
                            "format": element.get("format", "unknown")
                        }
                        
                        # İşlenecek görsellere ekle
                        images.append(image_info)
                        image_indices.append(idx)
                except Exception as img_err:
                    logger.error(f"Görsel öğe hazırlanırken hata: {str(img_err)}")
        
        # Eğer işlecek görsel yoksa orijinal içeriği döndür
        if not images:
            logger.info("İşlenecek görsel bulunamadı")
            return document_content, []
            
        logger.info(f"Toplam {len(images)} görsel AI ile analiz edilecek")
        
        # Toplu görsel işleme yap
        results = process_images_with_model(
            images=images,
            model_type=model_type,
            model_name=model_name,
            batch_size=batch_size,
            parallel=parallel
        )
        
        # Sonuçları normalize et
        normalized_results = [normalize_image_analysis_result(r) for r in results]
        
        # Zenginleştirilmiş görsel içeriklerini belgeye ekle
        for result_idx, (image_idx, result) in enumerate(zip(image_indices, normalized_results)):
            # Sonuçları belge içeriğine aktar
            document_content["elements"][image_idx]["ai_analysis"] = result
            
            # Ayrıca sonuç listesine de ekle
            image_analyses.append({
                "element_index": image_idx,
                "analysis": result
            })
            
            logger.info(f"Görsel {result_idx+1}/{len(normalized_results)} analiz sonucu başarıyla eklendi")
        
        # Belge metadata'sına özet bilgi ekle
        if "metadata" not in document_content:
            document_content["metadata"] = {}
        
        document_content["metadata"]["ai_image_analysis"] = {
            "analysis_time": datetime.now().isoformat(),
            "image_count": len(images),
            "model_type": model_type,
            "model_name": model_name,
            "has_analyses": True
        }
            
    except Exception as e:
        logger.error(f"Görsel toplu işleme sırasında hata: {str(e)}")
        if "metadata" not in document_content:
            document_content["metadata"] = {}
        
        document_content["metadata"]["ai_image_analysis_error"] = str(e)
    
    return document_content, image_analyses