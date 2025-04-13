"""
Toplu İşleme Modülü (Batch Processing Module)
Büyük dokümanlar için paralel ve toplu işleme stratejileri sağlar.
"""

import os
import time
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Callable, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Büyük dokümanların bölümlere ayrılarak paralel işlenmesi için genel amaçlı işleyici.
    Hem metin hem görsel işleme için kullanılabilir, model ve işleme taleplerine göre akıllıca
    parçalara ayırır ve verimliliği artırır.
    """
    
    def __init__(
        self,
        batch_size: int = 5,
        max_workers: int = 4,
        process_timeout: int = 120,
        output_format: str = "json",
        preserve_order: bool = True
    ):
        """
        BatchProcessor sınıfını başlat
        
        Args:
            batch_size: Her batch'teki öğe sayısı
            max_workers: Paralel işleme için maksimum iş parçacığı sayısı
            process_timeout: Her batch için maksimum işleme süresi (saniye)
            output_format: Çıktı formatı ('json' veya 'text')
            preserve_order: Sonuçların orijinal sırada döndürülüp döndürülmeyeceği
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.process_timeout = process_timeout
        self.output_format = output_format
        self.preserve_order = preserve_order
        
        # İşlem istatistikleri
        self.stats = {
            "total_items": 0,
            "successful_items": 0,
            "failed_items": 0,
            "total_batches": 0,
            "total_processing_time": 0,
            "start_time": None,
            "end_time": None
        }
        
        logger.info(f"BatchProcessor initialized: batch_size={batch_size}, max_workers={max_workers}")
    
    def process_items(
        self,
        items: List[Any],
        processor_func: Callable[[Any, Dict[str, Any]], Any],
        processor_kwargs: Optional[Dict[str, Any]] = None,
        adaptive_batching: bool = True
    ) -> List[Any]:
        """
        Öğeleri işle - her öğeyi sağlanan işleme işlevine gönderir
        
        Args:
            items: İşlenecek öğelerin listesi
            processor_func: Her öğeyi işleyecek fonksiyon - func(item, **kwargs) biçiminde olmalı
            processor_kwargs: İşleme fonksiyonuna geçirilecek parametreler sözlüğü
            adaptive_batching: İşleme performansına göre batch boyutunu otomatik ayarla
            
        Returns:
            İşlenmiş öğe sonuçlarının listesi
        """
        if not items:
            logger.warning("Boş öğe listesi, işlem yapılmadı")
            return []
        
        if processor_kwargs is None:
            processor_kwargs = {}
            
        # İşleme istatistiklerini sıfırla ve başlangıç zamanını kaydet
        self.stats = {
            "total_items": len(items),
            "successful_items": 0,
            "failed_items": 0,
            "total_batches": 0,
            "total_processing_time": 0,
            "start_time": time.time(),
            "end_time": None,
            "batch_times": []
        }
        
        # Öğeleri batch'lere ayır
        batch_size = self.batch_size
        batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
        self.stats["total_batches"] = len(batches)
        
        logger.info(f"Toplamda {len(items)} öğe, {len(batches)} batch'e ayrıldı (batch boyutu: {batch_size})")
        
        results = []
        batch_times = []
        
        # Her batch için işleme yap
        try:
            for batch_idx, batch in enumerate(batches):
                batch_start_time = time.time()
                logger.info(f"Batch {batch_idx+1}/{len(batches)} işleniyor ({len(batch)} öğe)")
                
                # Paralel işleme yap
                if self.max_workers > 1:
                    batch_results = self._process_batch_parallel(batch, processor_func, processor_kwargs)
                else:
                    batch_results = self._process_batch_serial(batch, processor_func, processor_kwargs)
                
                # Batch sonuçlarını ana sonuç listesine ekle
                results.extend(batch_results)
                
                # Batch performans istatistiklerini güncelle
                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                batch_times.append(batch_duration)
                
                # Son 3 batch'in ortalama süresini hesapla
                avg_duration = sum(batch_times[-3:]) / len(batch_times[-3:]) if batch_times else 0
                
                logger.info(f"Batch {batch_idx+1} tamamlandı: {batch_duration:.2f} saniye ({len(batch)} öğe, {batch_duration/len(batch):.2f} saniye/öğe)")
                
                # Adaptive batching - batch boyutunu performansa göre ayarla
                if adaptive_batching and batch_idx > 0 and batch_idx < len(batches) - 1:
                    if avg_duration > 0:
                        # Eğer ortalama batch süresi 45 saniyeden fazlaysa, batch boyutunu azalt
                        if avg_duration > 45 and batch_size > 2:
                            batch_size = max(int(batch_size * 0.7), 1)
                            logger.info(f"Batch süresi çok uzun, batch boyutu azaltıldı: {batch_size}")
                        # Eğer ortalama batch süresi 15 saniyeden azsa, batch boyutunu artır
                        elif avg_duration < 15:
                            batch_size = min(int(batch_size * 1.5), 20)
                            logger.info(f"Batch süresi çok kısa, batch boyutu artırıldı: {batch_size}")
        except Exception as e:
            logger.error(f"Batch işlemi sırasında hata: {str(e)}")
            # Hata oluşsa bile mevcut sonuçları döndür
        
        # İşleme istatistiklerini son kez güncelle
        self.stats["end_time"] = time.time()
        self.stats["total_processing_time"] = self.stats["end_time"] - self.stats["start_time"]
        self.stats["successful_items"] = len([r for r in results if not (isinstance(r, dict) and "error" in r)])
        self.stats["failed_items"] = len(results) - self.stats["successful_items"]
        self.stats["batch_times"] = batch_times
        
        # İşleme istatistiklerini logla
        logger.info(f"İşleme tamamlandı: {self.stats['total_items']} öğe, {self.stats['successful_items']} başarılı, " + 
                   f"{self.stats['failed_items']} başarısız, {self.stats['total_processing_time']:.2f} saniye")
        
        return results
    
    def _process_batch_parallel(
        self,
        batch: List[Any],
        processor_func: Callable[[Any, Dict[str, Any]], Any],
        processor_kwargs: Dict[str, Any]
    ) -> List[Any]:
        """
        Bir batch'i paralel olarak işle
        
        Args:
            batch: İşlenecek öğeler batch'i
            processor_func: Her öğeyi işleyecek fonksiyon
            processor_kwargs: İşleme fonksiyonuna geçirilecek parametreler
            
        Returns:
            İşlenmiş öğe sonuçları
        """
        results = [None] * len(batch)  # Sonuçları orijinal sırayla saklayacak liste
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
            # Her öğe için görev başlat
            future_to_idx = {
                executor.submit(self._process_single_item, item, processor_func, processor_kwargs): idx
                for idx, item in enumerate(batch)
            }
            
            # Görevler tamamlandıkça sonuçları topla
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result(timeout=self.process_timeout)
                    results[idx] = result  # Sonucu doğru indekse yerleştir
                except Exception as e:
                    logger.error(f"Öğe {idx} işleme hatası: {str(e)}")
                    results[idx] = {"error": str(e)}
        
        return results
    
    def _process_batch_serial(
        self,
        batch: List[Any],
        processor_func: Callable[[Any, Dict[str, Any]], Any],
        processor_kwargs: Dict[str, Any]
    ) -> List[Any]:
        """
        Bir batch'i seri olarak işle
        
        Args:
            batch: İşlenecek öğeler batch'i
            processor_func: Her öğeyi işleyecek fonksiyon
            processor_kwargs: İşleme fonksiyonuna geçirilecek parametreler
            
        Returns:
            İşlenmiş öğe sonuçları
        """
        results = []
        
        for item in batch:
            try:
                result = self._process_single_item(item, processor_func, processor_kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Öğe işleme hatası: {str(e)}")
                results.append({"error": str(e)})
        
        return results
    
    def _process_single_item(
        self,
        item: Any,
        processor_func: Callable[[Any, Dict[str, Any]], Any],
        processor_kwargs: Dict[str, Any]
    ) -> Any:
        """
        Tek bir öğeyi işle
        
        Args:
            item: İşlenecek öğe
            processor_func: Öğeyi işleyecek fonksiyon
            processor_kwargs: İşleme fonksiyonuna geçirilecek parametreler
            
        Returns:
            İşlenmiş öğe sonucu
        """
        try:
            start_time = time.time()
            result = processor_func(item, **processor_kwargs)
            processing_time = time.time() - start_time
            
            # İşleme süresi çok uzun veya kısa ise log kaydet
            if processing_time > 10:
                logger.info(f"Uzun işleme süresi: {processing_time:.2f} saniye")
            
            return result
        except Exception as e:
            logger.error(f"Öğe işleme hatası: {str(e)}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """İşleme istatistiklerini döndür"""
        return self.stats
    
    def get_stats_formatted(self) -> str:
        """İşleme istatistiklerini okunabilir formatta döndür"""
        stats = self.stats.copy()
        
        # Zaman değerlerini okunabilir formatlara dönüştür
        if stats["start_time"]:
            stats["start_time_formatted"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats["start_time"]))
        if stats["end_time"]:
            stats["end_time_formatted"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stats["end_time"]))
        
        # Batch süreleri için istatistikler
        if "batch_times" in stats and stats["batch_times"]:
            batch_times = stats["batch_times"]
            stats["avg_batch_time"] = sum(batch_times) / len(batch_times)
            stats["min_batch_time"] = min(batch_times)
            stats["max_batch_time"] = max(batch_times)
        
        # Formatlı çıktı oluştur
        if self.output_format.lower() == "json":
            return json.dumps(stats, indent=2, ensure_ascii=False)
        else:
            lines = [
                "Batch İşleme İstatistikleri:",
                f"- Toplam öğe sayısı: {stats['total_items']}",
                f"- Başarılı işlenen öğe sayısı: {stats['successful_items']}",
                f"- Başarısız öğe sayısı: {stats['failed_items']}",
                f"- Toplam batch sayısı: {stats['total_batches']}",
                f"- Toplam işleme süresi: {stats['total_processing_time']:.2f} saniye",
                f"- Ortalama öğe işleme süresi: {stats['total_processing_time']/stats['total_items']:.4f} saniye" if stats["total_items"] > 0 else "",
                f"- Başlangıç zamanı: {stats.get('start_time_formatted', 'N/A')}",
                f"- Bitiş zamanı: {stats.get('end_time_formatted', 'N/A')}"
            ]
            
            if "avg_batch_time" in stats:
                lines.extend([
                    f"- Ortalama batch süresi: {stats['avg_batch_time']:.2f} saniye",
                    f"- En kısa batch süresi: {stats['min_batch_time']:.2f} saniye",
                    f"- En uzun batch süresi: {stats['max_batch_time']:.2f} saniye"
                ])
            
            return "\n".join(lines)

def process_document_in_batches(
    document_content: Dict[str, Any],
    processor_function: Callable[[Any, Dict[str, Any]], Any],
    batch_size: int = 5,
    max_workers: int = 4,
    element_type_filter: Optional[str] = None,
    processor_kwargs: Optional[Dict[str, Any]] = None,
    metadata_key: str = "batch_processing"
) -> Tuple[Dict[str, Any], List[Any]]:
    """
    Belge içeriğini batch işleme kullanarak toplu işle
    
    Args:
        document_content: DocumentContent nesnesini temsil eden sözlük
        processor_function: Her öğeyi işleyecek fonksiyon
        batch_size: Her batch'teki öğe sayısı
        max_workers: Paralel işleme için maksimum iş parçacığı sayısı
        element_type_filter: Sadece belirli tipteki öğeleri işle ('image', 'table', vb.)
        processor_kwargs: İşleme fonksiyonuna geçirilecek parametreler
        metadata_key: Metadata'da işleme sonuçlarının saklanacağı anahtar
        
    Returns:
        Tuple[Dict, List]: İşlenmiş belge içeriği ve işleme sonuçlarının listesi
    """
    batch_processor = BatchProcessor(
        batch_size=batch_size,
        max_workers=max_workers
    )
    
    # İşlenecek öğeleri belirle
    elements_to_process = []
    element_indices = []
    
    try:
        # Belge içeriğinde "elements" listesi var mı kontrol et
        if "elements" not in document_content:
            logger.warning("document_content içerisinde 'elements' listesi bulunamadı")
            return document_content, []
        
        # Filtreleme kriterine göre öğeleri topla
        for idx, element in enumerate(document_content["elements"]):
            if element_type_filter and element.get("type") != element_type_filter:
                continue
            
            # İşleme için öğeyi ekle
            elements_to_process.append(element)
            element_indices.append(idx)
    
        # Eğer işlenecek öğe yoksa orijinal içeriği döndür
        if not elements_to_process:
            logger.info(f"İşlenecek öğe bulunamadı (filtre: {element_type_filter})")
            return document_content, []
            
        logger.info(f"Toplam {len(elements_to_process)} öğe batch işleme için hazırlandı")
        
        # Batch işleme yap
        results = batch_processor.process_items(
            items=elements_to_process,
            processor_func=processor_function,
            processor_kwargs=processor_kwargs or {}
        )
        
        # Sonuçları belgeye entegre et
        processed_elements = []
        for result_idx, (element_idx, result) in enumerate(zip(element_indices, results)):
            if not isinstance(result, dict) or "error" not in result:
                # Başarılı işlenen sonuçları belgeye ekle - burada strateji öğenin tipine göre değişebilir
                # Örnek: element["processed_content"] = result
                document_content["elements"][element_idx]["batch_processed"] = True
                
                if "metadata" not in document_content["elements"][element_idx]:
                    document_content["elements"][element_idx]["metadata"] = {}
                    
                document_content["elements"][element_idx]["metadata"]["processing_result"] = result
                
                # İşlenen öğeyi sonuç listesine ekle
                processed_elements.append({
                    "element_index": element_idx,
                    "result": result
                })
            else:
                # Hatalı işlenen öğeleri logla
                logger.warning(f"Öğe {element_idx} işleme hatası: {result.get('error', 'Bilinmeyen hata')}")
                
                if "metadata" not in document_content["elements"][element_idx]:
                    document_content["elements"][element_idx]["metadata"] = {}
                    
                document_content["elements"][element_idx]["metadata"]["processing_error"] = result.get("error")
        
        # Belge metadata'sına batch işleme istatistiklerini ekle
        if "metadata" not in document_content:
            document_content["metadata"] = {}
            
        document_content["metadata"][metadata_key] = batch_processor.get_stats()
        
        logger.info(f"Batch işleme tamamlandı: {len(processed_elements)} öğe başarıyla işlendi")
            
    except Exception as e:
        logger.error(f"Batch işleme sırasında hata: {str(e)}")
        if "metadata" not in document_content:
            document_content["metadata"] = {}
            
        document_content["metadata"][f"{metadata_key}_error"] = str(e)
    
    return document_content, batch_processor.get_stats()