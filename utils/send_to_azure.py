"""
Azure OpenAI API ile iletişim kurma modülü.

Bu modül Azure OpenAI modellerini kullanarak API istekleri yapmaya ve 
sonuçları işlemeye olanak tanır.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union

# Logging
logger = logging.getLogger(__name__)

def send_to_azure(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    deployment_id: Optional[str] = None,
    api_version: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Mesaj listesi kullanarak Azure OpenAI API'ye istek gönderir ve yanıtı döndürür.
    
    Args:
        messages: OpenAI mesaj formatında gönderilecek mesajlar listesi
        model: Kullanılacak model adı (ör. gpt-4o, o1, o3-mini vb.)
        temperature: Yanıtların yaratıcılık seviyesi (0-1)
        max_tokens: Oluşturulacak maksimum token sayısı
        deployment_id: Özelleştirilmiş Azure deployment ID'si (belirtilmezse model adına göre seçilir)
        api_version: Azure API versiyonu (belirtilmezse model adına göre seçilir)
        
    Returns:
        İşlenmiş API yanıtı veya hata durumunda None
    """
    # Azure kimlik bilgilerini al
    azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    
    # Doctest sabit değerleri (yedek olarak)
    api_api_key = "API-KEY"
    O1_API_KEY = "API-KEY"
    api_endpoint = "https://api-url.openai.azure.com"
    
    # API anahtarı ve endpoint kontrol et
    if not azure_api_key:
        azure_api_key = api_api_key
        logger.warning("Azure API key not found, using default Doctest key")
    
    if not azure_endpoint:
        azure_endpoint = api_endpoint
        logger.warning("Azure endpoint not found, using default Doctest endpoint")
    
    # Model adına göre deployment ID ve API versiyonu belirle (belirtilmemişse)
    if not deployment_id:
        # Model adına göre deployment ID belirle
        if model == "o1":
            deployment_id = "api-url-o1"
            # o1 için özel API anahtarını kullan
            o1_api_key = os.environ.get("O1_API_KEY", O1_API_KEY)
            if o1_api_key:
                azure_api_key = o1_api_key
                logger.info("Using special API key for o1 model")
        elif model == "o3-mini":
            deployment_id = "api-url-o3-mini"
            # o3-mini için de özel API anahtarını kullan
            o3_mini_api_key = os.environ.get("O1_API_KEY", O1_API_KEY)
            if o3_mini_api_key:
                azure_api_key = o3_mini_api_key
                logger.info("Using special API key for o3-mini model")
        else:
            # Diğer modeller için doğrudan model adını kullan
            deployment_id = model
    
    if not api_version:
        # Model adına göre API versiyonu belirle
        if model in ["o1", "o3-mini"]:
            api_version = "2024-12-01-preview"  # Claude modelleri için özel API versiyonu
        else:
            api_version = "2024-08-01-preview"  # Standart modeller için API versiyonu
    
    # API endpoint URL'sini oluştur
    url = f"{azure_endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"
    
    # İstek headerları
    headers = {
        "Content-Type": "application/json",
        "api-key": azure_api_key
    }
    
    # Claude modelleri (o1, o3-mini) için özelleştirilmiş istek payload'ı oluştur
    if model in ["o1", "o3-mini"]:
        payload = {
            "messages": messages,
            "max_completion_tokens": max_tokens  # Claude modelleri için özel parametre
            # Claude modelleri için temperature ve response_format desteklenmiyor
        }
    else:
        # GPT serisi modeller için standart payload
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
    
    try:
        logger.info(f"Sending request to Azure OpenAI API. Model: {model}, Deployment: {deployment_id}")
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request payload: {json.dumps(payload)[:500]}...")
        
        # API isteği gönder
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        # Durumu kontrol et
        if response.status_code == 200:
            # Başarılı yanıt
            response_json = response.json()
            logger.info(f"Request successful. Response length: {len(response.text)}")
            
            # Yanıttan içeriği çıkar ve döndür
            if "choices" in response_json and response_json["choices"]:
                if "message" in response_json["choices"][0]:
                    message_content = response_json["choices"][0]["message"]["content"]
                    return {
                        "content": message_content,
                        "model": model,
                        "usage": response_json.get("usage", {}),
                        "raw_response": response_json
                    }
            
            # Beklenmeyen yanıt formatı
            logger.error(f"Unexpected response format: {response.text[:200]}...")
            return None
            
        else:
            # API hata döndürdü
            logger.error(f"API Error ({response.status_code}): {response.text}")
            error_data = None
            
            try:
                error_data = response.json()
            except:
                pass
                
            return {
                "error": f"API Error ({response.status_code})",
                "details": error_data or response.text,
                "status_code": response.status_code
            }
            
    except Exception as e:
        logger.error(f"Error sending request to Azure OpenAI: {str(e)}")
        return {
            "error": "Request failed",
            "details": str(e)
        }