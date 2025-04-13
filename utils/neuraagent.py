"""
NeuraAgent Pro - Gelişmiş Doküman Analiz ve İşleme Ajanı
"""

import hashlib
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Set, Union

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# AI service için gerekli importlar, OpenAI'ı alternatif olarak kullan
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI kütüphanesi bulunamadı, bazı özellikler çalışmayabilir.")

# Veri analizi için pandas kullan, eğer yoksa alternatif çözümler sağla
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("Pandas kütüphanesi bulunamadı, bazı veri analiz özellikleri devre dışı.")

class NeuraAgentBasic:
    """
    NeuraAgent Basic - İşlenecek dokümanlar için basit bir ajan.
    Bu sürüm temel doküman analizi, optimizasyon ve bölümlendirme sunar.
    """
    
    def __init__(self, 
                settings: Optional[Dict[str, Any]] = None,
                cache_enabled: bool = True,
                memory_mode: str = "session"):
        """
        NeuraAgent Basic başlatma
        
        Args:
            settings: Ajanın davranışını kontrol eden ayarlar sözlüğü
            cache_enabled: Önbellek kullanımı etkin mi?
            memory_mode: Bellek modu ('session', 'disk' veya 'database')
        """
        # Default ayarları tanımla
        self.default_settings = {
            'optimization_level': 'medium',  # low, medium, high
            'max_document_size': 10000,      # MAX token büyüklüğü
            'enable_concept_analysis': True,
            'enable_section_scoring': True,
            'enable_similarity_search': False,
            'detailed_logging': False
        }
        
        # Settings'i ayarla
        self.settings = self.default_settings.copy()
        if settings:
            self.settings.update(settings)
        
        # Temel özellikleri ayarla
        self.cache_enabled = cache_enabled
        self.memory_mode = memory_mode
        self.openai_client = None
        
        # OpenAI kullanılabilir ise istemciyi başlat 
        if OPENAI_AVAILABLE:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI()
                logger.info("OpenAI istemcisi başlatıldı.")
            except Exception as e:
                logger.warning(f"OpenAI istemcisi başlatılamadı: {e}")
        
        logger.info(f"NeuraAgent Basic başlatıldı. Optimizasyon: {self.settings['optimization_level']}")
    
    def process_document(self, document_text: str, document_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Dokümanı işle ve optimum sonuçları döndür.
        
        Args:
            document_text: İşlenecek belgenin tam metni
            document_metadata: Dosya adı, türü vb. içeren metadata
            
        Returns:
            İşlenmiş doküman ve test senaryoları
        """
        logger.info(f"Doküman işleniyor. Uzunluk: {len(document_text)} karakter")
        
        if not document_metadata:
            document_metadata = {}
        
        start_time = time.time()
        
        # Belge için benzersiz hash oluştur
        document_hash = self._calculate_hash(document_text)
        
        # Cache etkin ise önbellekte ara
        if self.cache_enabled:
            cached_document = self._get_cached_analysis(document_hash)
            if cached_document:
                logger.info(f"Önbellekte bulunan doküman analizi kullanılıyor. Hash: {document_hash[:8]}")
                return cached_document
        
        # Analiz sonuçları için veri yapısı
        analysis_result = {
            "document_hash": document_hash,
            "document_metadata": document_metadata,
            "processing_time": 0,
            "document_type": None,
            "language": None,
            "summary": None,
            "sections": [],
            "concepts": [],
            "optimization": {
                "level": self.settings['optimization_level'],
                "original_size": len(document_text),
                "optimized_size": 0
            }
        }
        
        # Belge tipini tespit et
        analysis_result["document_type"] = self._detect_document_type(document_text, document_metadata)
        
        # Belge dilini tespit et
        analysis_result["language"] = self._detect_language(document_text)
        
        # Özet oluştur
        analysis_result["summary"] = self._generate_summary(document_text)
        
        # Belgeyi bölümlere ayır
        sections = self._split_document_into_sections(document_text)
        
        # Bölümlerin önemine göre puanlandır
        if self.settings['enable_section_scoring']:
            sections = self._score_sections(sections)
        
        analysis_result["sections"] = sections
        
        # Kavramları çıkar
        if self.settings['enable_concept_analysis']:
            analysis_result["concepts"] = self._extract_concepts(document_text, sections)
        
        # Analiz sonuçlarını önbelleğe al
        if self.cache_enabled:
            self._cache_analysis_results(document_hash, analysis_result, document_text)
        
        # İşleme süresini kaydet
        analysis_result["processing_time"] = time.time() - start_time
        
        logger.info(f"Doküman analizi tamamlandı. Süre: {analysis_result['processing_time']:.2f} saniye")
        return analysis_result
    
    def optimize_document(self, document_text: str, document_structure: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Dokümanı belirtilen AI için optimize eder
        
        Args:
            document_text: Doküman metni
            document_structure: Doküman yapısı hakkında bilgi
            
        Returns:
            Optimize edilmiş içerik ve yapı
        """
        if not document_structure:
            # Önce kısa bir analiz yap
            document_analysis = self.process_document(document_text)
            document_structure = document_analysis
        
        # Optimizasyon seviyesine bağlı olarak maksimum boyutu belirle
        optimization_level = self.settings['optimization_level']
        max_document_size = self.settings['max_document_size']
        
        if optimization_level == 'low':
            max_size = max(15000, max_document_size * 1.5)
        elif optimization_level == 'medium':
            max_size = max(10000, max_document_size)
        else:  # high
            max_size = max(5000, max_document_size * 0.6)
        
        # Optimize edilmiş doküman metnini oluştur
        optimized_text = self._optimize_document_for_ai(document_text, document_structure, int(max_size))
        
        result = {
            "text": optimized_text,
            "structure": document_structure,
            "is_neuraagent_optimized": True,
            "original_size": len(document_text),
            "optimized_size": len(optimized_text),
            "optimization_ratio": len(optimized_text) / len(document_text) if document_text else 0
        }
        
        logger.info(f"Doküman optimize edildi. Oran: {result['optimization_ratio']:.2f}")
        return result
    
    def detect_tables(self, text: str) -> List[Dict[str, Any]]:
        """
        Metin içindeki tabloları tespit eder ve yapılandırılmış formatta döndürür
        
        Args:
            text: Tablo içerebilecek metin
            
        Returns:
            Tespit edilen tabloların listesi
        """
        if not PANDAS_AVAILABLE:
            logger.warning("Tablo tespiti için pandas gereklidir")
            return []
        
        tables = []
        
        # Basit regex ile tablo benzeri yapıları tespit etmeye çalış
        # Gerçek uygulamada daha gelişmiş bir algoritma kullanılmalı
        table_patterns = [
            r'(\|[^\n]+\|\n)+',  # Markdown tablolar
            r'(\+[-+]+\+\n\|[^+]+\|\n)+',  # ASCII tablolar
            r'(\s*\w+\s*\t\s*\w+\s*\t[^\n]*\n)+',  # Tab-ayrılmış veriler
        ]
        
        for pattern in table_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                table_text = match.group(0)
                table_start = match.start()
                table_end = match.end()
                
                # Tablo tipi tespiti
                table_type = "unknown"
                if '|' in table_text and '\n' in table_text:
                    table_type = "markdown"
                elif '\t' in table_text:
                    table_type = "tsv"
                
                # Tablo verilerini çıkar
                try:
                    if table_type == "markdown":
                        # Basit markdown tablo ayrıştırma
                        lines = table_text.strip().split('\n')
                        headers = [h.strip() for h in lines[0].strip('|').split('|')]
                        rows = []
                        for line in lines[2:]:  # İlk satır başlık, ikinci ayırıcı
                            if '|' in line:
                                cells = [c.strip() for c in line.strip('|').split('|')]
                                rows.append(cells)
                    else:
                        # Diğer formatlar için basit ayrıştırma
                        lines = table_text.strip().split('\n')
                        if len(lines) > 1:
                            separator = '\t' if '\t' in lines[0] else None
                            headers = [h.strip() for h in lines[0].split(separator)]
                            rows = []
                            for line in lines[1:]:
                                cells = [c.strip() for c in line.split(separator)]
                                rows.append(cells)
                        else:
                            headers = []
                            rows = []
                    
                    tables.append({
                        "table_id": f"table_{len(tables) + 1}",
                        "table_type": table_type,
                        "position": {"start": table_start, "end": table_end},
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows),
                        "column_count": len(headers)
                    })
                    
                except Exception as e:
                    logger.error(f"Tablo ayrıştırma hatası: {e}")
        
        return tables
    
    def get_document_history(self, document_hash: str) -> Dict[str, Any]:
        """
        Belirli bir belgenin işleme geçmişini veritabanından al
        
        Args:
            document_hash: Doküman document_hash değeri
            
        Returns:
            Dokümanın işleme geçmişi
        """
        # Gerçek uygulamada burası veritabanından çekilmeli
        # Şu an için hardcoded değerler döndürüyoruz
        return {
            "document_hash": document_hash,
            "access_count": 3,
            "last_accessed": time.time() - 86400,  # 1 gün önce
            "processing_history": [
                {"timestamp": time.time() - 86400 * 2, "operation": "analyzed"},
                {"timestamp": time.time() - 86400 * 1, "operation": "optimized"}
            ]
        }
    
    def find_similar_documents(self, document_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Verilen dokümana benzer dokümanları veritabanından bul
        
        Args:
            document_text: Benzerliği aranacak doküman metni
            limit: Dönecek maksimum benzer doküman sayısı
            
        Returns:
            Benzer dokümanların listesi
        """
        if not self.settings['enable_similarity_search']:
            logger.info("Benzerlik araması devre dışı")
            return []
        
        # Gerçek uygulamada vector DB veya benzerlik algoritması kullanılmalı
        # Şu an için örnek veri döndürüyoruz
        return [
            {
                "document_hash": "1234567890abcdef",
                "similarity_score": 0.95,
                "title": "Benzer Doküman 1",
                "snippet": document_text[:100] + "...",
            },
            {
                "document_hash": "abcdef1234567890",
                "similarity_score": 0.82,
                "title": "Benzer Doküman 2",
                "snippet": document_text[100:200] + "...",
            }
        ][:limit]
    
    def analyze_visual_content(self, image_data: bytes, image_format: str = "jpg") -> Dict[str, Any]:
        """
        Görsel içeriği analiz eder ve metin, tablolar ve önemli içerikleri çıkarır.
        Test senaryoları ve kullanım durumları için önemli içerikleri tanımlar.
        Her görsel öğe için tekil ve detaylı bir analiz yapar.
        
        Args:
            image_data: Görsel verisi
            image_format: Görsel formatı (jpg, png, vs)
            
        Returns:
            Görsel analiz sonuçları ve test senaryoları zenginleştirilmiş
        """
        if not OPENAI_AVAILABLE:
            logger.warning("Görsel analizi için OpenAI Vision API gereklidir")
            return {"error": "OpenAI Vision API mevcut değil"}
        
        try:
            # Base64 ile görsel verilerini kodla
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # OpenAI Vision API ile analiz yap (eğer mevcutsa)
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": """Bu bir test senaryosu oluşturma aracıdır. Görselleri analiz ederek
                            içerdikleri UI öğeleri, akış diyagramları, tablolar ve süreç şemaları hakkında
                            detaylı test senaryoları çıkarın. Her öğe için standartlara uygun test durumları tanımlayın."""
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Bu görseli analiz et ve içerdiği tüm öğeler için test senaryoları oluştur."},
                                {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{image_base64}"}}
                            ]
                        }
                    ],
                    max_tokens=1500
                )
                
                # Analiz sonucunu işle
                analysis_result = {
                    "success": True,
                    "image_format": image_format,
                    "image_size_bytes": len(image_data),
                    "detected_elements": [],
                    "analysis_text": response.choices[0].message.content
                }
                
                # Analiz sonucundan test senaryosu promptu oluştur
                test_prompt = self._build_scenario_prompt(analysis_result)
                
                # Test senaryolarını oluştur
                test_scenarios = self._generate_test_scenarios_from_visual(test_prompt)
                
                # Sonuçları birleştir
                analysis_result["test_scenarios"] = test_scenarios
                
                return analysis_result
            
            else:
                return {
                    "success": False, 
                    "error": "OpenAI istemcisi başlatılamadı",
                    "fallback_description": "Görsel içeriği analiz edilemiyor"
                }
                
        except Exception as e:
            logger.error(f"Görsel analizi sırasında hata: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # Yardımcı fonksiyonlar
    def _exponential_backoff_retry(self, func, max_retries=5, base_delay=1, max_delay=60):
        """
        Üstel gecikme ile fonksiyon yeniden deneme mekanizması
        
        Args:
            func: Çalıştırılacak fonksiyon
            max_retries: Maksimum deneme sayısı
            base_delay: Temel gecikme süresi (saniye)
            max_delay: Maksimum gecikme süresi (saniye)
            
        Returns:
            Fonksiyon sonucu
        """
        retries = 0
        last_exception = None
        
        while retries < max_retries:
            try:
                return func()
            except Exception as e:
                last_exception = e
                retries += 1
                
                if retries >= max_retries:
                    logger.error(f"Maksimum deneme sayısına ulaşıldı: {str(e)}")
                    break
                
                # Üstel gecikme hesapla, maksimum gecikmeyi aşmamasını sağla
                delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                # Rastgele ufak değişimler ekle (jitter)
                delay = delay * (0.8 + 0.4 * (time.time() % 1))
                
                logger.warning(f"Hata oluştu, {delay:.2f} saniye sonra tekrar deneniyor. "
                              f"Deneme {retries}/{max_retries}: {str(e)}")
                time.sleep(delay)
        
        raise last_exception if last_exception else RuntimeError("Bilinmeyen hata")
    
    def _calculate_hash(self, text: str) -> str:
        """
        Metin için SHA-256 değeri hesapla
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_cached_analysis(self, document_hash: str) -> Optional[Dict[str, Any]]:
        """
        Veritabanından önbelleklenmiş analizi çek
        """
        # Gerçek uygulamada veritabanından çekilmeli
        return None
    
    def _cache_analysis_results(self, document_hash: str, document_structure: Dict[str, Any], 
                               original_text: str = None) -> None:
        """
        Analiz sonuçlarını veritabanına kaydet
        """
        # Gerçek uygulamada veritabanına yazılmalı
        pass
    
    def _detect_document_type(self, document_text: str, metadata: Dict[str, Any]) -> str:
        """
        Doküman tipini belirle (Teknik, Fonksiyonel, vs)
        """
        # Gerçek uygulamada içerik analizi ile tespit edilmeli
        file_type = metadata.get('file_type', '')
        
        if file_type:
            if file_type.lower() in ['pdf', 'docx', 'doc']:
                # Teknik dokümantasyon ipuçlarını ara
                technical_indicators = ['api', 'endpoint', 'function', 'class', 'method',
                                       'database', 'schema', 'code', 'implementation']
                
                # Fonksiyonel dokümantasyon ipuçlarını ara
                functional_indicators = ['user story', 'requirement', 'feature', 'scenario',
                                        'acceptance criteria', 'test case', 'use case']
                
                # Basit kelime sayımı ile belge tipini tahmin et
                technical_count = sum(1 for indicator in technical_indicators 
                                     if indicator.lower() in document_text.lower())
                
                functional_count = sum(1 for indicator in functional_indicators 
                                      if indicator.lower() in document_text.lower())
                
                if technical_count > functional_count:
                    return "technical"
                elif functional_count > technical_count:
                    return "functional"
        
        # Net bir sonuç yoksa varsayılan olarak "general" dön
        return "general"
    
    def _detect_language(self, text: str) -> str:
        """
        Metnin dilini tespit et
        """
        # Basit bir dil tespiti
        # Gelişmiş versiyonda langdetect veya CLD3 kütüphanesi kullanılmalı
        turkish_chars = set('çğıöşüÇĞİÖŞÜ')
        text_sample = text[:1000].lower()
        
        # Türkçe karakterler varsa
        if any(char in turkish_chars for char in text_sample):
            return "tr"
        
        # İngilizce mi Türkçe mi karar ver
        en_indicators = ['the', 'and', 'that', 'have', 'for', 'not', 'with']
        tr_indicators = ['ve', 'bu', 'için', 'bir', 'ile', 'olarak', 'tarafından']
        
        en_count = sum(1 for word in en_indicators if f" {word} " in f" {text_sample} ")
        tr_count = sum(1 for word in tr_indicators if f" {word} " in f" {text_sample} ")
        
        return "tr" if tr_count >= en_count else "en"
    
    def _generate_summary(self, text: str) -> str:
        """
        Kısa bir özet oluştur
        """
        # İlk ~200 kelimeyi al
        words = text.split()
        preview = ' '.join(words[:200]) + ('...' if len(words) > 200 else '')
        
        # OpenAI mevcutsa AI özetleme kullan, değilse basit önizleme döndür
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Aşağıdaki metni 2-3 cümle ile özetle."},
                        {"role": "user", "content": text[:4000]}  # İlk 4000 karakteri özet için yeterli olacaktır
                    ],
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"AI özet oluşturma hatası: {e}")
                return preview
        
        return preview
    
    def _split_document_into_sections(self, document_text: str) -> List[Dict[str, Any]]:
        """
        Dokümanı mantıklı bölümlere ayırır
        """
        sections = []
        
        # Belgeyi başlıklara göre bölümlere ayır
        # Basit bir pattern kullanıyoruz, gerçek uygulamada daha gelişmiş olmalı
        section_patterns = [
            r'#+\s+(.+)',  # Markdown headings
            r'(\d+\.[\d\.]*)\s+(.+)',  # Numbered headings (1. Title, 1.2. Subtitle)
            r'([A-Z][A-Z\s]+:)',  # ALL CAPS HEADINGS:
        ]
        
        # Tüm metni bir bölüm olarak kabul ederek başla
        current_section = {
            "section_index": 0,
            "section_level": 0,
            "section_title": "Doküman Başlangıcı",
            "section_content": "",
            "start_position": 0,
            "end_position": 0
        }
        
        # Metin içinde bölüm başlıklarını ara
        section_matches = []
        for pattern in section_patterns:
            for match in re.finditer(pattern, document_text, re.MULTILINE):
                # Başlık ve pozisyon bilgilerini kaydet
                title = match.group(0)
                if len(match.groups()) > 0:
                    # İlk grup (parantez içinde) başlık olabilir
                    title = match.group(1)
                
                section_matches.append({
                    "title": title.strip(),
                    "start": match.start(),
                    "match": match
                })
        
        # Başlıkları pozisyona göre sırala
        section_matches.sort(key=lambda x: x["start"])
        
        # Eğer hiç bölüm bulunamadıysa, tüm metni tek bölüm olarak kabul et
        if not section_matches:
            sections.append({
                "section_index": 0,
                "section_level": 0,
                "section_title": "Doküman İçeriği",
                "section_content": document_text,
                "start_position": 0,
                "end_position": len(document_text)
            })
            return sections
        
        # Bölümleri oluştur
        for i, section in enumerate(section_matches):
            # Önceki bölümün içeriğini güncelle
            if i > 0:
                prev_section = sections[i-1]
                prev_section["end_position"] = section["start"]
                prev_section["section_content"] = document_text[prev_section["start_position"]:prev_section["end_position"]]
            
            # Yeni bölüm ekle
            sections.append({
                "section_index": i,
                "section_level": 1,  # Daha gelişmiş seviye tespiti yapılabilir
                "section_title": section["title"],
                "section_content": "",  # İçerik sonraki iterasyonda doldurulacak
                "start_position": section["start"],
                "end_position": 0  # Sonda güncellenecek
            })
        
        # Son bölümün içeriğini güncelle
        if sections:
            last_section = sections[-1]
            last_section["end_position"] = len(document_text)
            last_section["section_content"] = document_text[last_section["start_position"]:last_section["end_position"]]
        
        return sections
    
    def _score_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Bölümleri önem derecesine göre puanla
        """
        # Bölüm puanlandırma metriği
        for section in sections:
            content = section["section_content"]
            
            # Basit bir puanlama algoritması
            # 1. Bölüm uzunluğu
            length_score = min(len(content) / 500, 5)  # Maksimum 5 puan
            
            # 2. Anahtar kelimeler
            important_keywords = ["önemli", "kritik", "gereklilik", "zorunlu", "test", 
                                 "senaryo", "koşul", "dikkat", "not", "uyarı"]
            
            keyword_score = sum(2 for word in important_keywords if word.lower() in content.lower())
            keyword_score = min(keyword_score, 3)  # Maksimum 3 puan
            
            # 3. Bölüm seviyesi (başlık seviyesi)
            level_score = max(0, 3 - section["section_level"])  # Level 0 = 3 puan, Level 1 = 2 puan, vs.
            
            # Toplam puanı hesapla (1-10 arası normalizasyon)
            total_score = length_score + keyword_score + level_score
            normalized_score = max(1, min(10, total_score))
            
            # Puanları ekle
            section["importance_score"] = normalized_score
            section["scoring_details"] = {
                "length_score": length_score,
                "keyword_score": keyword_score,
                "level_score": level_score
            }
        
        # Bölümleri puana göre sırala
        return sorted(sections, key=lambda x: x["importance_score"], reverse=True)
    
    def _extract_concepts(self, document_text: str, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dokümandan önemli kavramları çıkar."""
        # In a real implementation, this would use NLP techniques
        # For this mock implementation, use basic frequency analysis
        
        # Tokenize and normalize words
        words = re.findall(r'\b[a-zA-ZçğıöşüÇĞİÖŞÜ]{4,}\b', document_text.lower())
        
        # Remove common stop words (English and Turkish)
        stop_words = {"the", "and", "of", "to", "in", "for", "with", "on", "at", "by", "ve", "ile", "için", "bu", "bir"}
        words = [word for word in words if word not in stop_words]
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Filter for relatively frequent words
        min_count = max(3, len(words) * 0.01)  # At least 3 occurrences or 1% of text
        potential_concepts = {word: count for word, count in word_counts.items() if count >= min_count}
        
        # Create concept entries
        concepts = []
        for concept, frequency in sorted(potential_concepts.items(), key=lambda x: x[1], reverse=True)[:20]:
            # Find related sections (sections containing this concept)
            related_sections = []
            for section in sections:
                if concept in section["section_content"].lower():
                    related_sections.append({
                        "section_index": section["section_index"],
                        "section_title": section["section_title"],
                        "importance_score": section.get("importance_score", 0)
                    })
            
            # Calculate concept importance based on frequency and section importance
            concept_importance = frequency * (1 + 0.1 * len(related_sections))
            
            concepts.append({
                "concept_name": concept,
                "concept_frequency": frequency,
                "concept_importance": concept_importance,
                "related_sections": related_sections
            })
        
        return concepts
    
    def _optimize_document_for_ai(self, document_text: str, document_structure: Dict[str, Any], 
                                 max_size: int) -> str:
        """Dokümanı AI için optimum boyuta getir, önemli kısımları koru."""
        if len(document_text) <= max_size:
            return document_text
        
        # Intelligent section-based optimization
        sections = document_structure.get("sections", [])
        
        if not sections:
            # Fallback to simple truncation if no sections available
            return document_text[:max_size-100] + "\n...[içerik kısaltıldı]..."
        
        # Sort sections by importance (should already be sorted)
        sorted_sections = sorted(sections, key=lambda x: x.get("importance_score", 0), reverse=True)
        
        # Start with the document summary and a header
        optimized_text = f"{document_structure.get('summary', '')}\n\n"
        optimized_text += "[Bu doküman AI işleme için optimize edilmiştir. En önemli bölümler korunmuştur.]\n\n"
        
        # Add high-importance sections until we approach the limit
        remaining_size = max_size - len(optimized_text) - 100  # Reserve 100 chars for footer
        
        # Always include at least part of the first section (likely the introduction)
        if sorted_sections and remaining_size > 200:
            try:
                # Gerekli alanlar var mı kontrol et
                first_section = sections[0]
                if "section_content" in first_section and isinstance(first_section["section_content"], str):
                    intro = first_section["section_content"][:min(1000, remaining_size // 2)]
                    optimized_text += f"GİRİŞ:\n{intro}\n\n"
                    remaining_size -= len(intro) + 15  # +15 for the header
            except (IndexError, KeyError, TypeError) as e:
                logger.warning(f"Giriş bölümü işlenirken hata: {e}")
        
        # Add sections by importance until we run out of space
        added_sections = set()
        for section in sorted_sections:
            try:
                # Gerekli alanların varlığını kontrol et
                if "section_index" not in section or section["section_index"] in added_sections:
                    continue
                
                if "section_content" not in section or "section_title" not in section:
                    continue
                    
                section_text = section["section_content"]
                section_title = section["section_title"]
                
                # Metin tipini kontrol et
                if not isinstance(section_text, str) or not isinstance(section_title, str):
                    continue
                
                # If the entire section fits, add it
                if len(section_text) + len(section_title) + 10 <= remaining_size:
                    optimized_text += f"{section_title}:\n{section_text}\n\n"
                    remaining_size -= (len(section_text) + len(section_title) + 12)
                    added_sections.add(section["section_index"])
                # Otherwise, try to add a truncated version
                elif remaining_size > 200:
                    truncated_text = section_text[:remaining_size - len(section_title) - 30]
                    optimized_text += f"{section_title}:\n{truncated_text}...\n\n"
                    remaining_size = 0
                    added_sections.add(section["section_index"])
                
                if remaining_size <= 0:
                    break
            except Exception as e:
                logger.warning(f"Bölüm işlenirken hata: {e}")
                continue
        
        # Add footer
        optimized_text += "\n[Optimize edilmiş doküman sonu]"
        
        return optimized_text
        
    def _build_scenario_prompt(self, analysis_result: Dict[str, Any]) -> str:
        """
        Görsel analiz sonuçlarından test senaryosu promptu oluştur
        
        Args:
            analysis_result: Görsel analiz sonuçları
            
        Returns:
            Prompt metni
        """
        prompt = "Aşağıdaki görsel analiz sonuçlarına dayanarak test senaryoları ve kullanım durumları oluştur:\n\n"
        
        # Analiz metnini ekle
        if "analysis_text" in analysis_result and analysis_result["analysis_text"]:
            prompt += f"GÖRSEL ANALİZİ:\n{analysis_result['analysis_text']}\n\n"
        
        # Tespit edilen öğeleri ekle
        if "detected_elements" in analysis_result and analysis_result["detected_elements"]:
            prompt += "TESPİT EDİLEN ÖĞELER:\n"
            for element in analysis_result["detected_elements"]:
                prompt += f"- {element['element_type']}: {element.get('description', '')}\n"
            prompt += "\n"
        
        # Test notları ekle
        if "test_notes" in analysis_result and analysis_result["test_notes"]:
            prompt += f"TEST NOTLARI:\n{analysis_result['test_notes']}\n\n"
            
        # İstenen çıktı formatını ekle - genişletilmiş ve daha standart odaklı
        prompt += """Lütfen aşağıdaki JSON formatında yanıt ver. Her bir test senaryosu ve kullanım durumu, resimden çıkarılan en iyi test standartlarını ve pratiklerini izlemelidir. Gereksiz veya alakasız test durumları üretme. Yalnızca görselde kesin olarak tespit edilebilen öğeler için test durumları oluştur:"""
        
        prompt += """
{
    "test_scenarios": [
        {
            "scenario_id": "TS001",
            "scenario_name": "Senaryo Adı",
            "description": "Senaryo açıklaması",
            "priority": "Yüksek/Orta/Düşük",
            "applicable_standards": ["İlgili standart veya gereksinim 1", "İlgili standart 2"],
            "category": "UI/Fonksiyonel/Performans/Güvenlik/Uyumluluk",
            "prerequisites": ["Ön koşul 1", "Ön koşul 2"],
            "test_cases": [
                {
                    "test_case_id": "TC001",
                    "test_case_name": "Test Durum Adı",
                    "purpose": "Bu test durumunun amacı",
                    "steps": ["Adım 1", "Adım 2", "Adım 3"],
                    "expected_results": ["Beklenen Sonuç 1", "Beklenen Sonuç 2", "Beklenen Sonuç 3"],
                    "test_data": ["Gerekli test verisi 1", "Gerekli test verisi 2"],
                    "special_requirements": ["Özel gereksinim 1"],
                    "potential_issues": ["Potansiyel sorun 1", "Dikkat edilmesi gereken unsur 2"]
                }
            ]
        }
    ],
    "use_cases": [
        {
            "use_case_id": "UC001",
            "use_case_name": "Kullanım Durumu Adı",
            "description": "Kullanım durumu açıklaması",
            "actor": "Kullanıcı rolü veya sistem",
            "preconditions": ["Ön koşul 1", "Ön koşul 2"],
            "flow": ["Akış adımı 1", "Akış adımı 2", "Akış adımı 3"],
            "alternative_flows": [
                {"condition": "Alternatif koşul 1", "steps": ["Alternatif adım 1", "Alternatif adım 2"]},
                {"condition": "Alternatif koşul 2", "steps": ["Alternatif adım 1", "Alternatif adım 2"]}
            ],
            "postconditions": ["Son durum 1", "Son durum 2"],
            "business_rules": ["İş kuralı 1", "İş kuralı 2"]
        }
    ],
    "test_coverage_analysis": {
        "elements_covered": ["Testin kapsadığı UI/fonksiyon/öğeler"],
        "elements_not_covered": ["Kapsanmayan öğeler veya gerekli ek testler"],
        "coverage_percentage": 85
    },
    "confidence": 0.85
}"""
        
        return prompt
        
    def _generate_test_scenarios_from_visual(self, prompt: str) -> Dict[str, Any]:
        """AI modeli kullanarak görsel analiz verilerinden test senaryoları oluştur"""
        # Gerçek uygulamada OpenAI veya başka bir LLM kullanılmalı
        # Basit bir önyükleme sonucu dönelim
        return {
            "scenarios": [
                {
                    "id": "TS001",
                    "name": "Görsel içeriği doğrulama testi",
                    "description": "Görseldeki içeriklerin doğru görüntülenip görüntülenmediğini test et",
                    "priority": "Yüksek",
                    "test_cases": [
                        {
                            "id": "TC001", 
                            "name": "Görseldeki tüm öğelerin ekranda görünürlüğü", 
                            "steps": ["Sayfayı aç", "Görseli kontrol et"]
                        }
                    ]
                }
            ],
            "summary": "Görseldeki öğeler için temel test senaryoları"
        }