"""
Model Selector - Dinamik model seçimi ve AI görev atama modülü

Bu modül, farklı görev türlerine uygun AI modellerini otomatik olarak seçer.
İçerik analizi yaparak görevin karmaşıklığına ve türüne göre en uygun
AI modelini belirler ve çoklu model kullanımını koordine eder.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple

# Logger yapılandırması
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Model konfigürasyonları
MODEL_CONFIGS = {
    # Görsel analiz modelleri
    "image_analysis": {
        "primary": {
            "provider": "openai",
            "model": "gpt-4o",
            "params": {
                "max_tokens": 2000,
                "temperature": 0.3
            },
            "description": "En gelişmiş çok modlu görsel işleme modeli"
        },
        "fallback": {
            "provider": "azure",
            "model": "gpt-4o",
            "params": {
                "max_tokens": 2000,
                "temperature": 0.3
            },
            "description": "Azure üzerinde çalışan görsel işleme modeli"
        }
    },
    
    # Metin sınıflandırma ve hafif işlemler
    "classification": {
        "primary": {
            "provider": "azure",
            "model": "o3-mini",
            "params": {
                "max_completion_tokens": 1000
            },
            "description": "Hızlı sınıflandırma ve kategorizasyon modeli"
        },
        "fallback": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "params": {
                "max_tokens": 1000,
                "temperature": 0.1
            },
            "description": "Temel sınıflandırma ve analiz modeli"
        }
    },
    
    # Teknik detay analizi ve test senaryoları 
    "technical": {
        "primary": {
            "provider": "azure",
            "model": "o1",
            "params": {
                "max_completion_tokens": 3000
            },
            "description": "Karmaşık teknik içerik için özelleştirilmiş model"
        },
        "fallback": {
            "provider": "azure",
            "model": "o3-mini",
            "params": {
                "max_completion_tokens": 2000
            },
            "description": "Temel teknik analiz modeli"
        }
    },
    
    # Entegrasyon ve birleştirme
    "integration": {
        "primary": {
            "provider": "azure",
            "model": "gpt-4o-mini",
            "params": {
                "max_tokens": 2500,
                "temperature": 0.2
            },
            "description": "Sonuçları birleştirme ve entegrasyon modeli"
        },
        "fallback": {
            "provider": "azure",
            "model": "o1",
            "params": {
                "max_completion_tokens": 2000
            },
            "description": "Entegrasyon yedek modeli"
        }
    }
}

# Görev türlerinin tanımları
TASK_DEFINITIONS = {
    "image_analysis": {
        "description": "Görsel içerik analizi",
        "patterns": ["görsel", "image", "resim", "diyagram", "şema", "akış", "ekran görüntüsü"],
        "complexity": 0.8
    },
    "classification": {
        "description": "Metin sınıflandırma ve kategorizasyon",
        "patterns": ["sınıflandır", "kategorize et", "etiketle", "belirle", "tanımla"],
        "complexity": 0.4
    },
    "technical": {
        "description": "Teknik içerik ve test senaryosu oluşturma",
        "patterns": ["test", "teknik", "senaryo", "kullanım durumu", "gereksinim", "özellik"],
        "complexity": 0.7
    },
    "integration": {
        "description": "Sonuçları birleştirme ve sentezleme",
        "patterns": ["birleştir", "sentezle", "özetle", "entegre et", "derle"],
        "complexity": 0.6
    }
}

class ModelSelector:
    """Farklı görevler için optimal AI modellerini seçen sınıf"""
    
    def __init__(self):
        """Model seçici başlat"""
        self.last_selections = {}
        logger.info("ModelSelector başlatıldı")
    
    def select_model_for_task(self, task_type: str, content_hint: str = None, 
                            content_size: int = 0, complexity: float = None) -> Dict[str, Any]:
        """
        Belirli bir görev için optimal modeli seç
        
        Args:
            task_type: Görev türü (MODEL_CONFIGS'da tanımlı)
            content_hint: İçerik hakkında ipucu (metin)
            content_size: İçerik boyutu (karakter)
            complexity: Görev karmaşıklığı (0-1 arası)
            
        Returns:
            Seçilen model konfigürasyonu
        """
        if task_type not in MODEL_CONFIGS:
            logger.warning(f"Bilinmeyen görev türü: {task_type}, varsayılan 'technical' kullanılıyor")
            task_type = "technical"
        
        # İçerik ipucuna göre görev türünü yeniden değerlendir
        if content_hint:
            detected_task = self._detect_task_from_content(content_hint)
            if detected_task and detected_task != task_type:
                logger.info(f"İçerik analizine göre görev türü değiştirildi: {task_type} -> {detected_task}")
                task_type = detected_task
        
        # İçerik boyutuna göre model parametrelerini ayarla
        model_config = MODEL_CONFIGS[task_type]["primary"].copy()
        
        # Çok büyük içerik için daha düşük token limiti kullan
        if content_size > 50000 and "max_tokens" in model_config["params"]:
            logger.info(f"Büyük içerik tespit edildi ({content_size} karakter), token limiti düşürülüyor")
            model_config["params"]["max_tokens"] = int(model_config["params"]["max_tokens"] * 0.8)
        
        # Karmaşıklık seviyesine göre ayarlama
        if complexity is not None:
            if complexity > 0.7 and task_type != "technical":
                logger.info(f"Yüksek karmaşıklık ({complexity}) tespit edildi, daha güçlü model seçiliyor")
                # Karmaşık içerik için daha gelişmiş modele yükselt
                if task_type == "classification":
                    model_config = MODEL_CONFIGS["technical"]["primary"].copy()
            elif complexity < 0.3 and task_type == "technical":
                logger.info(f"Düşük karmaşıklık ({complexity}) tespit edildi, daha hafif model seçiliyor")
                # Basit içerik için daha hafif modele geç
                model_config = MODEL_CONFIGS["classification"]["primary"].copy()
        
        # Bu görevi hatırla
        self.last_selections[task_type] = model_config
        
        logger.info(f"'{task_type}' görevi için {model_config['provider']} / {model_config['model']} seçildi")
        return model_config
    
    def get_fallback_model(self, task_type: str) -> Dict[str, Any]:
        """
        Bir görev için yedek modeli döndür
        
        Args:
            task_type: Görev türü
            
        Returns:
            Yedek model konfigürasyonu
        """
        if task_type not in MODEL_CONFIGS:
            logger.warning(f"Bilinmeyen görev türü: {task_type}, varsayılan 'technical' için yedek kullanılıyor")
            task_type = "technical"
            
        return MODEL_CONFIGS[task_type]["fallback"]
    
    def get_task_complexity(self, content: str, task_type: str = None) -> float:
        """
        İçerik ve görev türüne göre karmaşıklığı hesapla
        
        Args:
            content: Değerlendirilecek içerik
            task_type: Görev türü (opsiyonel)
            
        Returns:
            Karmaşıklık puanı (0-1 arası)
        """
        # Temel karmaşıklık göstergeleri
        indicators = {
            "code_snippets": len(re.findall(r'```[a-z]*\n[\s\S]*?\n```', content)),
            "tables": len(re.findall(r'\|.*\|', content)),
            "technical_terms": len(re.findall(r'\b(API|SQL|HTTP|JSON|XML|REST|SDK|Git|DB|Database|Algorithm|Function)\b', content, re.IGNORECASE)),
            "long_sentences": len([s for s in content.split('.') if len(s) > 100]),
            "paragraphs": content.count('\n\n'),
            "special_chars": len(re.findall(r'[^\w\s]', content)) / max(1, len(content))
        }
        
        # Görev türüne göre ağırlıkları ayarla
        if task_type == "technical":
            weights = {
                "code_snippets": 0.3,
                "tables": 0.2,
                "technical_terms": 0.2,
                "long_sentences": 0.1,
                "paragraphs": 0.1,
                "special_chars": 0.1
            }
        elif task_type == "image_analysis":
            weights = {
                "code_snippets": 0.1,
                "tables": 0.2,
                "technical_terms": 0.2,
                "long_sentences": 0.1,
                "paragraphs": 0.2,
                "special_chars": 0.2
            }
        else:
            weights = {
                "code_snippets": 0.2,
                "tables": 0.2,
                "technical_terms": 0.15,
                "long_sentences": 0.15,
                "paragraphs": 0.15,
                "special_chars": 0.15
            }
        
        # Karmaşıklık puanı hesapla (normalize edilmiş)
        complexity = 0
        for key, value in indicators.items():
            normalized_value = min(1.0, value / 10.0)  # 10+ öğe maksimum normalize edilmiş değer
            complexity += normalized_value * weights[key]
        
        # Toplam metni boyutu için ek faktör
        length_factor = min(1.0, len(content) / 10000.0)  # 10K+ karakter maksimum normalize değer
        complexity = (complexity * 0.7) + (length_factor * 0.3)
        
        logger.info(f"İçerik karmaşıklık puanı: {complexity:.2f}")
        return min(1.0, complexity)  # 0-1 aralığına sınırla
    
    def _detect_task_from_content(self, content: str) -> Optional[str]:
        """
        İçeriğe bakarak hangi görev türüne uygun olduğunu tespit et
        
        Args:
            content: Değerlendirilecek içerik
            
        Returns:
            Tespit edilen görev türü veya None
        """
        scores = {}
        
        # Her görev türü için uyumluluk puanı hesapla
        for task_name, task_def in TASK_DEFINITIONS.items():
            score = 0
            for pattern in task_def["patterns"]:
                # Hem tam kelime hem de kısmi eşleşme ara
                full_word_count = len(re.findall(r'\b' + re.escape(pattern) + r'\b', content, re.IGNORECASE))
                partial_match_count = content.lower().count(pattern.lower()) - full_word_count
                
                # Tam kelime eşleşmesi daha değerli
                score += (full_word_count * 2) + (partial_match_count * 0.5)
            
            # İçerik uzunluğuna göre normalize et
            scores[task_name] = score / max(1, len(content) / 100)
        
        if not scores:
            return None
            
        # En yüksek puanlı görevi seç
        best_task = max(scores.items(), key=lambda x: x[1])
        
        # Minimum bir eşik değeri kontrol et
        if best_task[1] >= 0.05:  # Anlamlı bir eşik değeri
            logger.info(f"İçerik analizi sonucu görev tespit edildi: {best_task[0]} (puan: {best_task[1]:.2f})")
            return best_task[0]
        
        return None
    
# Modül yüklenirken otomatik olarak model seçici oluştur
model_selector = ModelSelector()