from app import app
import logging
import utils.logging_config as log_config
import os

# api-url API anahtarlarını ve endpoint bilgilerini ortam değişkenlerine ayarla
os.environ["OPENAI_API_KEY"] = "API-KEY"
os.environ["AZURE_OPENAI_API_KEY"] = "API-KEY"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://api-url.openai.azure.com/"
os.environ["O1_API_KEY"] = "API-KEY"

# Loglama sistemi yapılandırma
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    # Uygulama başlatılıyor mesajı
    logger.info("NeuraAgent Test Senaryosu Üreticisi başlatılıyor...")
    logger.info("Geliştirilmiş loglama sistemi aktif")
    logger.info("Detaylı hatalar ve işlemler '/logs' klasöründe kaydediliyor")
    logger.info("api-url API entegrasyonu yapılandırıldı")
    
    # Uygulamayı başlat
    app.run(host="0.0.0.0", port=5000, debug=True)
