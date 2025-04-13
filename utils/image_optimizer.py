"""
Görsel optimizasyon modülü.
Bu modül, belgelerdeki görselleri optimize eder ve AI tabanlı analizlerle zenginleştirir.
"""

import os
import logging
import base64
from typing import List, Dict, Any, Optional

def batch_optimize_images(images: List[Dict[str, Any]], ai_service_type: str = "openai") -> List[Dict[str, Any]]:
    """
    Belgedeki görselleri toplu olarak optimize eder.
    Her görselin küçük bir açıklaması oluşturulur ve token tüketimi minimize edilir.
    
    Args:
        images (List[Dict]): İşlenecek görsel listesi 
        ai_service_type (str): Kullanılacak AI servisi ("openai", "azure", "ollama")
        
    Returns:
        List[Dict]: Optimize edilmiş görsel listesi
    """
    optimized_images = []
    
    for i, image in enumerate(images):
        try:
            # Görsel içeriğini al
            image_content = image.get("content", "")
            image_format = image.get("format", "png")
            existing_description = image.get("description", "")
            
            # Eğer açıklama zaten varsa tekrar analiz etme
            if existing_description:
                optimized_images.append(image)
                continue
                
            # Görsel için kısa açıklama oluştur
            short_description = analyze_image(image_content, ai_service_type)
            
            # Optimize edilmiş görsel verisini hazırla
            optimized_image = {
                "content": image_content,
                "format": image_format,
                "description": short_description,
                "analysis": short_description  # Geriye dönük uyumluluk
            }
            
            optimized_images.append(optimized_image)
            logging.info(f"Görsel {i+1} optimize edildi")
            
        except Exception as e:
            logging.error(f"Görsel optimize edilirken hata: {str(e)}")
            # Hata durumunda orijinal görseli ekle
            optimized_images.append(image)
    
    return optimized_images

def analyze_image(image_content: str, ai_service_type: str = "openai") -> str:
    """
    Görseli analiz eder ve kısa açıklama üretir.
    
    Args:
        image_content (str): Base64 kodlanmış görsel içeriği
        ai_service_type (str): Kullanılacak AI servisi
        
    Returns:
        str: Görsel açıklaması
    """
    try:
        if ai_service_type == "openai":
            return analyze_with_openai(image_content)
        elif ai_service_type == "azure":
            return analyze_with_azure(image_content)
        else:
            # Varsayılan açıklama
            return "Belgeden çıkarılan görsel (AI tanımlama mevcut değil)"
    except Exception as e:
        logging.error(f"Görsel analizi sırasında hata: {str(e)}")
        return "Belgeden çıkarılan görsel (analiz hatası)"

def analyze_with_openai(image_content: str) -> str:
    """
    OpenAI'ın Vision modeli ile görsel analizi.
    
    Args:
        image_content (str): Base64 kodlanmış görsel içeriği
        
    Returns:
        str: Görsel açıklaması
    """
    try:
        # OpenAI API anahtarını kontrol et
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "Belgeden çıkarılan görsel (OpenAI API anahtarı bulunamadı)"
            
        from openai import OpenAI
        
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        # GPT-4o ile görsel analizi yap
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "Görseli kısaca ve net bir şekilde analiz et. En fazla 50 kelime kullan."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Bu görseli kısaca açıkla:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_content}"}
                        }
                    ]
                }
            ],
            max_tokens=100
        )
        
        # Yanıtı al
        description = response.choices[0].message.content.strip()
        
        # Çok uzunsa kısalt
        if len(description) > 200:
            description = description[:197] + "..."
            
        return description
        
    except Exception as e:
        logging.error(f"OpenAI ile görsel analizi sırasında hata: {str(e)}")
        return "Görsel analizi yapılamadı (OpenAI hatası)"

def analyze_with_azure(image_content: str) -> str:
    """
    Azure OpenAI'ın Vision modeli ile görsel analizi.
    
    Args:
        image_content (str): Base64 kodlanmış görsel içeriği
        
    Returns:
        str: Görsel açıklaması
    """
    try:
        # Azure AI servisini kullanabilmek için gerekli ayarları kontrol et
        from utils.config import config_manager
        
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if not azure_api_key:
            return "Belgeden çıkarılan görsel (Azure API anahtarı bulunamadı)"
            
        # Azure servisi şu an için kullanılamıyor varsayalım
        return "Belgeden çıkarılan görsel (Azure Vision analizi henüz entegre edilmedi)"
        
    except Exception as e:
        logging.error(f"Azure ile görsel analizi sırasında hata: {str(e)}")
        return "Görsel analizi yapılamadı (Azure hatası)"