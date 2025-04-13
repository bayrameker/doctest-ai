"""
İşlem istatistikleri modülü

Bu modül, NeuraAgent belge işleme ve test senaryoları oluşturma performansını
izlemek ve raporlamak için kullanılır. Her işlemden sonra istatistikleri toplar
ve analiz edilebilir bir formatta sunar.
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Loglama ayarları
logger = logging.getLogger(__name__)

class ProcessStatistics:
    """
    Belge işleme ve test senaryosu oluşturma performansı istatistikleri
    """
    def __init__(self):
        """İstatistik toplayıcıyı başlat"""
        self.stats = {
            "document_processing": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_time": 0,
                "fastest_time": None,
                "slowest_time": None,
                "by_file_type": {},
                "by_model": {}
            },
            "model_usage": {
                "total_calls": 0,
                "by_model": {},
                "by_task": {}
            },
            "errors": {
                "count": 0,
                "by_type": {}
            }
        }
        
        # İstatistik dosyası yolu
        self.stats_file = Path("logs/process_stats.json")
        
        # İstatistikleri varsa yükle
        self._load_stats()
        
        logger.info("İşlem istatistikleri toplayıcısı başlatıldı")
    
    def _load_stats(self):
        """Kaydedilmiş istatistikleri yükle"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logger.info(f"İşlem istatistikleri yüklendi: {self.stats_file}")
            except Exception as e:
                logger.error(f"İstatistik dosyası yüklenirken hata: {str(e)}")
    
    def _save_stats(self):
        """İstatistikleri dosyaya kaydet"""
        try:
            # Dizin yoksa oluştur
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
            logger.debug("İşlem istatistikleri güncellendi ve kaydedildi")
        except Exception as e:
            logger.error(f"İstatistikler kaydedilirken hata: {str(e)}")
    
    def record_document_processing(self, file_type: str, model: str, success: bool, 
                              processing_time: float, details: Dict[str, Any] = None):
        """
        Belge işleme istatistiklerini kaydet
        
        Args:
            file_type: Dosya türü (pdf, docx, vb.)
            model: Kullanılan AI modeli
            success: İşlem başarılı mı
            processing_time: İşlem süresi (saniye)
            details: İlave detaylar
        """
        # Genel istatistikleri güncelle
        self.stats["document_processing"]["total"] += 1
        
        if success:
            self.stats["document_processing"]["successful"] += 1
        else:
            self.stats["document_processing"]["failed"] += 1
        
        # Ortalama süreyi güncelle
        total = self.stats["document_processing"]["total"]
        current_avg = self.stats["document_processing"]["avg_time"]
        
        if total == 1:
            new_avg = processing_time
        else:
            new_avg = ((current_avg * (total - 1)) + processing_time) / total
        
        self.stats["document_processing"]["avg_time"] = new_avg
        
        # En hızlı ve en yavaş süreleri güncelle
        if (self.stats["document_processing"]["fastest_time"] is None or 
            processing_time < self.stats["document_processing"]["fastest_time"]):
            self.stats["document_processing"]["fastest_time"] = processing_time
            
        if (self.stats["document_processing"]["slowest_time"] is None or
            processing_time > self.stats["document_processing"]["slowest_time"]):
            self.stats["document_processing"]["slowest_time"] = processing_time
        
        # Dosya türüne göre istatistikleri güncelle
        if file_type not in self.stats["document_processing"]["by_file_type"]:
            self.stats["document_processing"]["by_file_type"][file_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_time": 0
            }
            
        self.stats["document_processing"]["by_file_type"][file_type]["total"] += 1
        
        if success:
            self.stats["document_processing"]["by_file_type"][file_type]["successful"] += 1
        else:
            self.stats["document_processing"]["by_file_type"][file_type]["failed"] += 1
            
        # Dosya türü için ortalama süreyi güncelle
        ft_total = self.stats["document_processing"]["by_file_type"][file_type]["total"]
        ft_current_avg = self.stats["document_processing"]["by_file_type"][file_type]["avg_time"]
        
        if ft_total == 1:
            ft_new_avg = processing_time
        else:
            ft_new_avg = ((ft_current_avg * (ft_total - 1)) + processing_time) / ft_total
            
        self.stats["document_processing"]["by_file_type"][file_type]["avg_time"] = ft_new_avg
        
        # Modele göre istatistikleri güncelle
        if model not in self.stats["document_processing"]["by_model"]:
            self.stats["document_processing"]["by_model"][model] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_time": 0
            }
            
        self.stats["document_processing"]["by_model"][model]["total"] += 1
        
        if success:
            self.stats["document_processing"]["by_model"][model]["successful"] += 1
        else:
            self.stats["document_processing"]["by_model"][model]["failed"] += 1
            
        # Model için ortalama süreyi güncelle
        model_total = self.stats["document_processing"]["by_model"][model]["total"]
        model_current_avg = self.stats["document_processing"]["by_model"][model]["avg_time"]
        
        if model_total == 1:
            model_new_avg = processing_time
        else:
            model_new_avg = ((model_current_avg * (model_total - 1)) + processing_time) / model_total
            
        self.stats["document_processing"]["by_model"][model]["avg_time"] = model_new_avg
        
        # İstatistikleri kaydet
        self._save_stats()
        
        # Detaylı log
        logger.info(f"Belge işleme istatistikleri güncellendi: "
                   f"Dosya türü: {file_type}, Model: {model}, "
                   f"Başarı: {success}, Süre: {processing_time:.2f} sn")
    
    def record_model_usage(self, model: str, task: str, success: bool, 
                          response_time: float, token_count: int = None):
        """
        Model kullanım istatistiklerini kaydet
        
        Args:
            model: Kullanılan AI modeli
            task: Görev türü
            success: İşlem başarılı mı
            response_time: Yanıt süresi
            token_count: Kullanılan token sayısı
        """
        # Genel istatistikleri güncelle
        self.stats["model_usage"]["total_calls"] += 1
        
        # Modele göre istatistikleri güncelle
        if model not in self.stats["model_usage"]["by_model"]:
            self.stats["model_usage"]["by_model"][model] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_response_time": 0,
                "total_tokens": 0
            }
            
        self.stats["model_usage"]["by_model"][model]["total_calls"] += 1
        
        if success:
            self.stats["model_usage"]["by_model"][model]["successful_calls"] += 1
        else:
            self.stats["model_usage"]["by_model"][model]["failed_calls"] += 1
            
        # Ortalama yanıt süresini güncelle
        model_calls = self.stats["model_usage"]["by_model"][model]["total_calls"]
        model_current_avg = self.stats["model_usage"]["by_model"][model]["avg_response_time"]
        
        if model_calls == 1:
            model_new_avg = response_time
        else:
            model_new_avg = ((model_current_avg * (model_calls - 1)) + response_time) / model_calls
            
        self.stats["model_usage"]["by_model"][model]["avg_response_time"] = model_new_avg
        
        # Token sayısını güncelle (eğer verilmişse)
        if token_count is not None:
            self.stats["model_usage"]["by_model"][model]["total_tokens"] += token_count
        
        # Görev türüne göre istatistikleri güncelle
        if task not in self.stats["model_usage"]["by_task"]:
            self.stats["model_usage"]["by_task"][task] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_response_time": 0,
                "by_model": {}
            }
            
        self.stats["model_usage"]["by_task"][task]["total_calls"] += 1
        
        if success:
            self.stats["model_usage"]["by_task"][task]["successful_calls"] += 1
        else:
            self.stats["model_usage"]["by_task"][task]["failed_calls"] += 1
            
        # Görev için ortalama yanıt süresini güncelle
        task_calls = self.stats["model_usage"]["by_task"][task]["total_calls"]
        task_current_avg = self.stats["model_usage"]["by_task"][task]["avg_response_time"]
        
        if task_calls == 1:
            task_new_avg = response_time
        else:
            task_new_avg = ((task_current_avg * (task_calls - 1)) + response_time) / task_calls
            
        self.stats["model_usage"]["by_task"][task]["avg_response_time"] = task_new_avg
        
        # Görev ve model kombinasyonu istatistiklerini güncelle
        if model not in self.stats["model_usage"]["by_task"][task]["by_model"]:
            self.stats["model_usage"]["by_task"][task]["by_model"][model] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_response_time": 0
            }
            
        self.stats["model_usage"]["by_task"][task]["by_model"][model]["total_calls"] += 1
        
        if success:
            self.stats["model_usage"]["by_task"][task]["by_model"][model]["successful_calls"] += 1
        else:
            self.stats["model_usage"]["by_task"][task]["by_model"][model]["failed_calls"] += 1
            
        # Görev ve model kombinasyonu için ortalama yanıt süresini güncelle
        combo_calls = self.stats["model_usage"]["by_task"][task]["by_model"][model]["total_calls"]
        combo_current_avg = self.stats["model_usage"]["by_task"][task]["by_model"][model]["avg_response_time"]
        
        if combo_calls == 1:
            combo_new_avg = response_time
        else:
            combo_new_avg = ((combo_current_avg * (combo_calls - 1)) + response_time) / combo_calls
            
        self.stats["model_usage"]["by_task"][task]["by_model"][model]["avg_response_time"] = combo_new_avg
        
        # İstatistikleri kaydet
        self._save_stats()
        
        # Detaylı log
        token_info = f", Token: {token_count}" if token_count is not None else ""
        logger.info(f"Model kullanım istatistikleri güncellendi: "
                   f"Model: {model}, Görev: {task}, "
                   f"Başarı: {success}, Süre: {response_time:.2f} sn{token_info}")
    
    def record_error(self, error_type: str, details: Dict[str, Any] = None):
        """
        Hata istatistiklerini kaydet
        
        Args:
            error_type: Hata türü
            details: Hata detayları
        """
        # Genel hata sayısını güncelle
        self.stats["errors"]["count"] += 1
        
        # Hata türüne göre istatistikleri güncelle
        if error_type not in self.stats["errors"]["by_type"]:
            self.stats["errors"]["by_type"][error_type] = {
                "count": 0,
                "first_seen": time.time(),
                "last_seen": time.time()
            }
            
        self.stats["errors"]["by_type"][error_type]["count"] += 1
        self.stats["errors"]["by_type"][error_type]["last_seen"] = time.time()
        
        # İstatistikleri kaydet
        self._save_stats()
        
        # Detaylı log
        logger.warning(f"Hata istatistikleri güncellendi: Tür: {error_type}, "
                     f"Toplam: {self.stats['errors']['by_type'][error_type]['count']}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        İstatistik özetini döndür
        
        Returns:
            Özet istatistikler
        """
        summary = {
            "document_processing": {
                "total": self.stats["document_processing"]["total"],
                "successful": self.stats["document_processing"]["successful"],
                "failed": self.stats["document_processing"]["failed"],
                "success_rate": 0,
                "avg_time": self.stats["document_processing"]["avg_time"],
                "fastest_time": self.stats["document_processing"]["fastest_time"],
                "slowest_time": self.stats["document_processing"]["slowest_time"]
            },
            "model_usage": {
                "total_calls": self.stats["model_usage"]["total_calls"],
                "top_models": self._get_top_models(3),
                "top_tasks": self._get_top_tasks(3)
            },
            "errors": {
                "count": self.stats["errors"]["count"],
                "top_errors": self._get_top_errors(3)
            }
        }
        
        # Başarı oranını hesapla
        if summary["document_processing"]["total"] > 0:
            success_rate = (summary["document_processing"]["successful"] / 
                          summary["document_processing"]["total"]) * 100
            summary["document_processing"]["success_rate"] = round(success_rate, 2)
            
        return summary
    
    def _get_top_models(self, count: int) -> List[Dict[str, Any]]:
        """En çok kullanılan modelleri döndür"""
        models = []
        
        for model, stats in self.stats["model_usage"]["by_model"].items():
            models.append({
                "model": model,
                "total_calls": stats["total_calls"],
                "avg_response_time": stats["avg_response_time"]
            })
            
        # Çağrı sayısına göre sırala
        models.sort(key=lambda x: x["total_calls"], reverse=True)
        
        return models[:count]
    
    def _get_top_tasks(self, count: int) -> List[Dict[str, Any]]:
        """En çok yapılan görevleri döndür"""
        tasks = []
        
        for task, stats in self.stats["model_usage"]["by_task"].items():
            tasks.append({
                "task": task,
                "total_calls": stats["total_calls"],
                "avg_response_time": stats["avg_response_time"]
            })
            
        # Çağrı sayısına göre sırala
        tasks.sort(key=lambda x: x["total_calls"], reverse=True)
        
        return tasks[:count]
    
    def _get_top_errors(self, count: int) -> List[Dict[str, Any]]:
        """En çok karşılaşılan hataları döndür"""
        errors = []
        
        for error_type, stats in self.stats["errors"]["by_type"].items():
            errors.append({
                "type": error_type,
                "count": stats["count"],
                "last_seen": stats["last_seen"]
            })
            
        # Hata sayısına göre sırala
        errors.sort(key=lambda x: x["count"], reverse=True)
        
        return errors[:count]

# Modül yüklendiğinde otomatik olarak istatistik toplayıcıyı başlat
process_stats = ProcessStatistics()