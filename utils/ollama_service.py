import os
import json
import logging
import requests
import time
import base64
from typing import Dict, Optional, Any, List, Union

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_with_ollama(document_text):
    """
    Generate test scenarios using Ollama API
    
    Args:
        document_text (str): Text extracted from the document
        
    Returns:
        dict: Structured test scenarios and use cases
    """
    # Get API endpoint from environment with default fallback
    api_endpoint = os.environ.get("OLLAMA_API_ENDPOINT", "http://localhost:11434/api/generate")
    
    # Get model name from environment with default fallback
    model = os.environ.get("OLLAMA_MODEL", "llama3")

def analyze_image_with_ollama(
    image_base64: str, 
    system_prompt: Optional[str] = None, 
    user_prompt: Optional[str] = None,
    model: Optional[str] = "llava:latest",
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Ollama servisi kullanarak görseli analiz eder
    
    Args:
        image_base64: Base64 formatında görsel
        system_prompt: Sistem prompt
        user_prompt: Kullanıcı prompt
        model: Kullanılacak model adı (görsel destekli model olmalı)
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
    
    # Ollama API endpoint
    api_endpoint = os.environ.get("OLLAMA_API_ENDPOINT", "http://localhost:11434/api/chat")
    
    try:
        # Görsel verisi ile birlikte istek gönder
        headers = {"Content-Type": "application/json"}
        
        # Sistem ve kullanıcı mesajları
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": user_prompt,
                "images": [image_base64]
            }
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "format": "json"
        }
        
        # Yanıt için bekleme süresi uzun tutuldu (120 saniye)
        response = requests.post(api_endpoint, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        # Yanıtı işle
        result = response.json()
        
        if "message" in result and "content" in result["message"]:
            content = result["message"]["content"]
            
            # JSON formatını çıkarmaya çalış
            try:
                parsed_json = json.loads(content)
                return {
                    "text": content,
                    "json": parsed_json,
                    "model": model,
                    "analysis_time": time.time() - start_time
                }
            except json.JSONDecodeError:
                # JSON olmayan içeriği ham metin olarak döndür
                return {
                    "text": content,
                    "model": model,
                    "analysis_time": time.time() - start_time
                }
        else:
            logger.error(f"Unexpected Ollama API response format: {result}")
            return {"error": "Unexpected Ollama API response format"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error to Ollama API: {str(e)}")
        return {"error": f"Ollama API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Görsel analizi sırasında hata (Ollama): {str(e)}")
        return {"error": f"Görsel analizi sırasında hata: {str(e)}"}
    
    # Get API endpoint from environment with default fallback
    api_endpoint = os.environ.get("OLLAMA_API_ENDPOINT", "http://localhost:11434/api/generate")
    
    # Get model name from environment with default fallback
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    
    # Ollama kullanılabilirlik kontrolünü ai_service.py modülüne taşıdık
    # Eğer bu kod çalışıyorsa Ollama'nın kullanılabilir olduğu varsayılır
    try:
        # Import is_ollama_available from ai_service module
        from utils.ai_service import is_ollama_available
        if not is_ollama_available():
            logger.warning("Ollama is not available. Make sure it's running or set OLLAMA_API_ENDPOINT.")
            raise ConnectionError("Ollama sunucusuna bağlanılamadı. Bu Replit ortamında normal bir durumdur. Gerçek bir Ollama sunucusu kullanmak için kendi OLLAMA_API_ENDPOINT değerinizi ayarlayın veya OLLAMA_SKIP_CHECK=true olarak ayarlayın ve bir test belgesi kullanın.")
    except ImportError:
        # If there's a circular import, fall back to direct checking
        if os.environ.get("OLLAMA_SKIP_CHECK", "false").lower() == "true":
            logger.info("Skipping Ollama connection check as OLLAMA_SKIP_CHECK is set to true")
        else:
            try:
                # Send a simple ping request to check if Ollama is running
                ping_response = requests.get(os.environ.get("OLLAMA_API_ENDPOINT", "http://localhost:11434"), timeout=2)
                if ping_response.status_code >= 400:
                    raise ConnectionError("Ollama server returned error response")
            except requests.exceptions.RequestException:
                logger.warning("Could not connect to Ollama server. Please make sure Ollama is running locally or set OLLAMA_API_ENDPOINT.")
                raise ConnectionError("Could not connect to Ollama server. Bu Replit ortamında normal bir durumdur. Gerçek bir Ollama sunucusu kullanmak için kendi OLLAMA_API_ENDPOINT değerinizi ayarlayın veya OLLAMA_SKIP_CHECK=true olarak ayarlayın ve bir test belgesi kullanın.")
    
    try:
        # Prepare the prompt for Ollama
        prompt = f"""
        You are a test scenario and use case generation expert. Analyze the provided document and 
        generate comprehensive test scenarios and use cases. Follow these guidelines:
        
        1. Identify key functionality described in the document
        2. Create test scenarios that cover both happy path and edge cases
        3. For each scenario, provide multiple test cases with clear steps and expected results
        4. Ensure your output follows this JSON structure:
        {{
            "summary": "Brief overview of the document and identified scenarios",
            "scenarios": [
                {{
                    "title": "Scenario name",
                    "description": "Detailed description of the scenario",
                    "test_cases": [
                        {{
                            "title": "Test case title",
                            "steps": "Numbered steps to execute the test",
                            "expected_results": "Expected outcomes of the test"
                        }}
                    ]
                }}
            ]
        }}
        
        Be thorough, detailed, and ensure your response is in valid JSON format.
        
        DOCUMENT:
        {document_text}
        """
        
        # Make API call
        logger.info(f"Sending request to Ollama API using model: {model}...")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(api_endpoint, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        # Extract the generated text
        if 'response' in result:
            generated_text = result['response']
        else:
            logger.error(f"Unexpected Ollama API response format: {result}")
            raise Exception("Unexpected Ollama API response format")
        
        # Parse the JSON from the generated text
        try:
            # First, try to parse it directly
            json_result = json.loads(generated_text)
            logger.info("Successfully parsed Ollama response as JSON")
            return json_result
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract the JSON part
            logger.warning("Failed to parse Ollama response directly as JSON. Attempting to extract JSON part...")
            
            # Try to find JSON within the text (between curly braces)
            import re
            json_match = re.search(r'({[\s\S]*})', generated_text)
            
            if json_match:
                try:
                    json_part = json_match.group(1)
                    json_result = json.loads(json_part)
                    logger.info("Successfully extracted and parsed JSON from Ollama response")
                    return json_result
                except json.JSONDecodeError:
                    logger.error("Failed to parse extracted JSON from Ollama response")
            
            # If we can't extract valid JSON, format it using the helper function
            from utils.ai_service import format_test_scenarios
            return format_test_scenarios(generated_text)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to Ollama API: {str(e)}")
        raise Exception(f"Failed to connect to Ollama API: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating test scenarios with Ollama: {str(e)}")
        raise Exception(f"Failed to generate test scenarios with Ollama: {str(e)}")
