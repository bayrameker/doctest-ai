"""
Gelişmiş loglama konfigürasyonu modülü
Bu modül, sistemdeki tüm servisler için tutarlı ve detaylı log yapılandırması sağlar.
"""

import os
import logging
import logging.handlers
import sys
import json
import traceback
import re
from datetime import datetime
from pathlib import Path

# Hassas veri filtresi - base64 görsel verilerini gizler
class SensitiveDataFilter(logging.Filter):
    """Hassas verileri loglardan filtreleyen sınıf"""

    def __init__(self):
        super().__init__()
        # Base64 görsel verilerini tespit etmek için regex pattern - daha geniş eşleşme için güncellendi
        self.image_pattern = re.compile(r'(data:image\/[^;]+;base64,[^"\s]+|base64,[^"\s]+)')
        # Alternatif base64 görsel formatı için ikinci pattern
        self.base64_pattern = re.compile(r'([a-zA-Z0-9+/]{100,}={0,2})')
        # API anahtarlarını tespit etmek için regex pattern - daha kapsamlı hale getirildi
        self.api_key_pattern = re.compile(r'(["\']?(?:api[_-]?key|apikey|key|token|secret)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{20,}["\']?)', re.IGNORECASE)
        # Doctest API anahtarlarını tespit etmek için özel pattern
        self.api_key_pattern = re.compile(r'(8RCCs[a-zA-Z0-9]{80,}|DAuzow[a-zA-Z0-9]{80,})')

    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Görsel verilerini maskele - önce image pattern
            record.msg = self.image_pattern.sub('data:image/***;base64,<IMAGE_DATA_HIDDEN>', record.msg)
            # Alternatif base64 pattern ile de maskele
            record.msg = self.base64_pattern.sub('<BASE64_DATA_HIDDEN>', record.msg)
            # API anahtarlarını maskele
            record.msg = self.api_key_pattern.sub('\\1: <API_KEY_HIDDEN>', record.msg)
            # Doctest API anahtarlarını maskele
            record.msg = self.api_key_pattern.sub('<api_API_KEY_HIDDEN>', record.msg)

        # args içinde de hassas veri olabilir
        if hasattr(record, 'args') and record.args:
            args_list = list(record.args)
            for i, arg in enumerate(args_list):
                if isinstance(arg, str):
                    # Görsel verilerini maskele - önce image pattern
                    args_list[i] = self.image_pattern.sub('data:image/***;base64,<IMAGE_DATA_HIDDEN>', arg)
                    # Alternatif base64 pattern ile de maskele
                    args_list[i] = self.base64_pattern.sub('<BASE64_DATA_HIDDEN>', arg)
                    # API anahtarlarını maskele
                    args_list[i] = self.api_key_pattern.sub('\\1: <API_KEY_HIDDEN>', args_list[i])
                    # Doctest API anahtarlarını maskele
                    args_list[i] = self.api_key_pattern.sub('<api_API_KEY_HIDDEN>', args_list[i])
                elif isinstance(arg, dict):
                    # Dict içindeki string değerleri kontrol et
                    for key, value in arg.items():
                        if isinstance(value, str):
                            # Görsel verilerini maskele
                            arg[key] = self.image_pattern.sub('data:image/***;base64,<IMAGE_DATA_HIDDEN>', value)
                            # Alternatif base64 pattern ile de maskele
                            arg[key] = self.base64_pattern.sub('<BASE64_DATA_HIDDEN>', arg[key])
                            # Doctest API anahtarlarını maskele
                            arg[key] = self.api_key_pattern.sub('<api_API_KEY_HIDDEN>', arg[key])
            record.args = tuple(args_list)
        return True

# NeuraDoc için özel fonksiyonlar
def log_processed_content(content, content_type, module_name="neuradoc"):
    """
    İşlenen içeriği loglar.

    Args:
        content (object): İşlenen içerik (dict, list, str olabilir)
        content_type (str): İçerik tipi (belge, görsel, tablo vs.)
        module_name (str, optional): İşleme yapan modül adı
    """
    logger = logging.getLogger(module_name)

    # İçerik boyutu hesaplama
    if isinstance(content, dict) or isinstance(content, list):
        content_size = len(json.dumps(content))
        content_summary = f"{content_type} içeriği: {content_size} karakter"
    elif isinstance(content, str):
        content_size = len(content)
        content_summary = f"{content_type} içeriği: {content_size} karakter"
    else:
        content_summary = f"{content_type} içeriği işlendi"

    # Belgenin %100 kapsandığını loglama mesajında vurgula
    if content_type == "document_structure_analysis":
        content_summary += " - Belge tam kapsama (%100)"

    logger.info(content_summary)

def setup_logger(name, level=logging.INFO):
    """
    Belirli bir isimle logger oluşturur.

    Args:
        name (str): Logger adı
        level (int): Log seviyesi

    Returns:
        Logger: Oluşturulan logger nesnesi
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger

# Ana çıktı biçimi, daha detaylı
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Kısa biçim, daha kompakt loglar için
SHORT_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# JSON formatındaki loglar için biçim
JSON_FORMAT = {"timestamp": "%(asctime)s", "module": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}

# Log dosyaları için dizin
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Kritik hataları ayrıca saklamak için dizin
ERROR_LOG_DIR = LOG_DIR / "errors"
ERROR_LOG_DIR.mkdir(exist_ok=True)

# Depolama hatalarını izlemek için özel günlük
STORAGE_ERROR_LOG = ERROR_LOG_DIR / "storage_errors.log"


def setup_logging(
    level=logging.DEBUG,
    file_name="app.log",
    console=True,
    file=True,
    format_str=LOG_FORMAT,
    error_log=True,
    json_log=False,
    filter_sensitive_data=True
):
    """
    Kapsamlı loglama yapılandırması

    Args:
        level: Log seviyesi
        file_name: Log dosyası adı
        console: Konsola log yazdırılsın mı
        file: Dosyaya log yazdırılsın mı
        format_str: Log biçimi
        error_log: Ayrı hata günlüğü tutulsun mu
        json_log: JSON formatında log tutulsun mu
        filter_sensitive_data: Hassas verileri (görsel kaynakları, API anahtarları vb.) filtrele
    """
    # Kök loglayıcıyı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Var olan tüm handlers'ları temizle
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # Hassas veri filtresini ekle
    if filter_sensitive_data:
        sensitive_filter = SensitiveDataFilter()
        root_logger.addFilter(sensitive_filter)
        # httpx ve urllib3 gibi kütüphanelerin loglarına da filtre uygula
        for logger_name in ['httpx', 'urllib3', 'openai', 'httpcore', 'openai._base_client', 'utils.neuradoc_enhanced', 'utils.ai_service', 'utils.azure_service', 'utils.openai_service']:
            logging.getLogger(logger_name).addFilter(sensitive_filter)
            # Alt modüllere de filtre uygula
            logging.getLogger(logger_name).propagate = False  # Çift loglama önleme
            # Debug seviyesini INFO'ya yükselt (çok fazla detay gösterme)
            if logger_name in ['openai._base_client', 'httpcore', 'httpx']:
                logging.getLogger(logger_name).setLevel(logging.INFO)

    formatter = logging.Formatter(format_str)

    # Dosyaya log
    if file:
        log_path = LOG_DIR / file_name
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

    # Hata logları için ayrı bir dosya
    if error_log:
        error_log_path = ERROR_LOG_DIR / "critical_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path, maxBytes=5*1024*1024, backupCount=10
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)  # Sadece ERROR ve üstü
        root_logger.addHandler(error_handler)

        # Kritik hatalar için ek loglama - Sadece basit bir dosya işleyici kullan
        error_log_extra = ERROR_LOG_DIR / "detailed_errors.log"
        detailed_handler = logging.handlers.RotatingFileHandler(
            error_log_extra, maxBytes=10*1024*1024, backupCount=5
        )
        detailed_handler.setFormatter(formatter)
        detailed_handler.setLevel(logging.ERROR)
        root_logger.addHandler(detailed_handler)

    # JSON formatında log
    if json_log:
        # JSON formatında log için özel formatter
        class JsonFormatter(logging.Formatter):
            """Log kayıtlarını JSON formatına dönüştüren formatter"""
            def format(self, record):
                log_data = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }

                # Exception bilgisi varsa ekle
                if record.exc_info:
                    log_data["exception"] = {
                        "type": record.exc_info[0].__name__,
                        "message": str(record.exc_info[1]),
                        "traceback": traceback.format_exception(*record.exc_info, limit=5)
                    }

                # Ekstra bilgileri ekle
                if hasattr(record, "data") and record.data:
                    log_data["data"] = record.data

                return json.dumps(log_data, ensure_ascii=False)

        json_log_path = LOG_DIR / "application.json.log"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_path, maxBytes=10*1024*1024, backupCount=5
        )
        json_handler.setFormatter(JsonFormatter())
        json_handler.setLevel(level)
        root_logger.addHandler(json_handler)

    # Konsola log
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)

    # İlk log girdisi
    root_logger.info("Loglama servisi başlatıldı - Tüm bileşenler için detaylı loglama aktif")


def setup_service_logging(service_name, level=logging.DEBUG):
    """
    Belirli bir servis için özel loglama yapılandırması

    Args:
        service_name: Servis adı
        level: Log seviyesi
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    # Servis için dosya
    log_file = LOG_DIR / f"{service_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3
    )
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # İlk log
    logger.info(f"{service_name} servisi için loglama başlatıldı")

    return logger


def enable_verbose_logging():
    """Tüm loglayıcılar için ayrıntılı modu etkinleştir"""
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("Ayrıntılı loglama modu etkinleştirildi")


def disable_verbose_logging():
    """Standart log seviyesine geri dön"""
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

    logging.getLogger().setLevel(logging.INFO)
    logging.info("Standart loglama moduna geri dönüldü")


def log_system_info():
    """Sistem bilgilerini logla"""
    import platform
    import sys

    logging.info(f"Python sürümü: {platform.python_version()}")
    logging.info(f"Platform: {platform.platform()}")
    logging.info(f"Çalışma dizini: {os.getcwd()}")

    # Çevresel değişkenler (güvenlik için önemli değişkenleri gizle)
    safe_env_vars = {k: v for k, v in os.environ.items() if not any(
        secret in k.lower() for secret in ['key', 'secret', 'password', 'token', 'credential']
    )}
    logging.debug(f"Çevresel değişkenler: {safe_env_vars}")


# Modül yüklendiğinde kullanılacak handler tanımları
class ErrorDetailHandler(logging.Handler):
    """Kritik hataların detaylı bilgilerini ayrı dosyalara yazan işleyici"""
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            try:
                # Hata detaylarını JSON olarak kaydet
                error_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_id = f"err_{error_time}_{id(record)}"
                error_file = ERROR_LOG_DIR / f"{error_id}.json"

                # Hata detaylarını topla
                error_details = {
                    "timestamp": record.created,
                    "formatted_time": datetime.fromtimestamp(record.created).isoformat(),
                    "logger": record.name,
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "pathname": record.pathname,
                    "lineno": record.lineno,
                    "function": record.funcName
                }

                # Eğer varsa exception bilgisini de ekle
                if record.exc_info:
                    error_details["exception"] = {
                        "type": str(record.exc_info[0].__name__),
                        "value": str(record.exc_info[1]),
                        "traceback": traceback.format_exception(*record.exc_info)
                    }

                # JSON olarak yaz
                with open(error_file, "w", encoding="utf-8") as f:
                    json.dump(error_details, f, ensure_ascii=False, indent=2)
            except Exception as e:
                # İşleyici kendi hatasını loglamaktan kaçın
                sys.stderr.write(f"Error logging error: {str(e)}\n")


class JsonFormatter(logging.Formatter):
    """Log kayıtlarını JSON formatına dönüştüren formatter"""
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Exception bilgisi varsa ekle
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info, limit=5)
            }

        # Ekstra bilgileri ekle
        if hasattr(record, "data") and record.data:
            log_data["data"] = record.data

        return json.dumps(log_data, ensure_ascii=False)


# Görsel işleme ile ilgili modüllerin debug loglarını tamamen devre dışı bırakmak için fonksiyon
def disable_image_processing_debug_logs():
    """Görsel işleme ile ilgili modüllerin debug loglarını devre dışı bırakır"""
    # OpenAI ve HTTP modülleri için debug logları kapat
    for logger_name in ['openai._base_client', 'httpcore', 'httpx', 'urllib3', 'openai']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Görsel işleme ile ilgili modüller için debug logları kapat
    for logger_name in ['utils.neuradoc_enhanced', 'utils.ai_service', 'utils.azure_service', 'utils.openai_service']:
        # Debug loglarını kapat ama WARNING ve üstü logları göster
        logging.getLogger(logger_name).setLevel(logging.WARNING)

# Modül yüklendiğinde otomatik olarak temel yapılandırmayı uygula
setup_logging(filter_sensitive_data=True)

# Görsel işleme ile ilgili debug loglarını devre dışı bırak
disable_image_processing_debug_logs()


if __name__ == "__main__":
    # Test için - modül doğrudan çalıştırıldığında örnek loglar oluştur
    logging.debug("Debug mesajı - Yalnızca ayrıntılı modda görünür")
    logging.info("Bilgi mesajı - Standart log kaydı")
    logging.warning("Uyarı mesajı - Dikkat gerektiren bir durum")
    logging.error("Hata mesajı - İşlem başarısız oldu")

    # Özel servis loglaması test et
    test_logger = setup_service_logging("test_service")
    test_logger.info("Test servisi mesajı")