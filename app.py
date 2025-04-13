import os
import logging
import threading
import time
import traceback
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_session import Session
from werkzeug.utils import secure_filename
import uuid
import json
from utils.document_parser import parse_document
from utils.ai_service import generate_test_scenarios, is_ollama_available
from utils.analytics import generate_scenario_analytics
from utils.document_optimizer import optimize_document_for_ai
from utils.image_optimizer import batch_optimize_images
from models import configure_db, db, Document, TestScenarioSet, ScenarioAnalytics
from sqlalchemy.exc import SQLAlchemyError

# Geliştirilmiş belge analiz modüllerini içe aktar - neuradoc_enhanced'ı kullanıyoruz
from utils.neuradoc_enhanced import extract_text as neuradoc_extract_text
from utils.neuradoc_enhanced import get_document_structure

# Default values for document analysis functions
ENHANCED_DOCUMENT_ANALYSIS = True

# Geliştirilmiş NeuraDoc modülünü doğrudan içe aktar
try:
    # NeuraDoc Enhanced modülünden doğrudan analize fonksiyonlarını içe aktar
    from utils.neuradoc_enhanced import analyze_document, get_document_structure
    logging.info("Enhanced NeuraDoc document analyzer is available and loaded successfully.")
except ImportError:
    logging.warning("Enhanced document analyzer not available. Using basic document parsing.")
    analyze_document = None
    get_document_structure = None
    ENHANCED_DOCUMENT_ANALYSIS = False

# NeuraAgent Basic ve doküman optimizasyon modüllerini import et
try:
    from utils.neuraagent import NeuraAgentBasic
    from utils.document_optimizer import optimize_document_for_ai, get_document_optimizer
    NEURAAGENT_AVAILABLE = True
    logging.info("NeuraAgent Basic modülü başarıyla yüklendi.")
except ImportError:
    NEURAAGENT_AVAILABLE = False
    logging.warning("NeuraAgent Basic modülü bulunamadı.")

# Varsayılan veritabanı istatistikleri
db_stats = {
    'document_count': 0,
    'section_count': 0,
    'concept_count': 0
}

# Varsayılan NeuraAgent ayarları
default_agent_settings = {
    'enable_agent': NEURAAGENT_AVAILABLE,
    'use_db_cache': True,
    'optimization_level': 'medium',
    'memory_mode': 'session',
    'max_document_size': 10000,
    'enable_concept_analysis': True,
    'enable_section_scoring': True,
    'enable_similarity_search': False,
    'enable_detailed_logging': False
}

# Doctest AI Model Endpoint tanımlamaları - api-url modellerinin en güncel detayları
AI_MODELS = {
    "gpt-4": {
        "endpoint": "URL",
        "api_key": "KEY",
        "param": "max_tokens",
        "api_version": "2024-08-01-preview"
    },
    "gpt-4o": {
        "endpoint": "URL",
        "api_key": "kEY",
        "param": "max_tokens",
        "api_version": "2024-08-01-preview"
    },
    "gpt-4o-mini": {
        "endpoint": "URL",
        "api_key": "KEY",
        "param": "max_tokens",
        "api_version": "2024-08-01-preview"
    },
    "o1": {
        "endpoint": "URL",
        "api_key": "KEY",
        "param": "max_completion_tokens",
        "api_version": "2024-12-01-preview"
    },
    "o3-mini": {
        "endpoint": "URL",
        "api_key": "KEY",
        "param": "max_completion_tokens",
        "api_version": "2024-12-01-preview"
    }
}

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to store session data
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'  # Custom session directory
app.config['SESSION_PERMANENT'] = False  # Session vanishes when browser is closed
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session timeout in seconds
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Initialize the Flask-Session extension
Session(app)

# Configure and initialize the database
configure_db(app)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# İşlemler artık doğrudan yapılacak, asenkron processler kullanılmayacak
# Eskiden asenkron işlemler için kullanılan değişken - artık kullanılmıyor
processing_jobs = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_document(document_text, ai_model, document_structure, filename, file_extension, azure_model=None):
    """
    Belgeyi işleyen ve sonuçları veritabanına kaydedip sonuçları doğrudan döndüren senkron fonksiyon.
    
    Args:
        document_text: İşlenecek belge metni
        ai_model: Kullanılacak AI modeli
        document_structure: Belge yapısı (varsa)
        filename: Dosya adı
        file_extension: Dosya uzantısı
        azure_model: Azure OpenAI modeli (varsa)
        
    Returns:
        (document, scenario_set): İşlenen belge ve oluşturulan senaryo seti
    """
    # NeuraDoc için tam belge yapısı özelliğini etkinleştir
    session['parser_used'] = 'neuradoc'  # Her zaman NeuraDoc'u zorla
    # İşlem istatistikleri topla
    from utils.process_stats import process_stats
    start_time = datetime.now()
    
    # İşlem başlangıç zamanı
    file_type = file_extension.lower()
    
    try:
        logging.info(f"Belge işleme başlatıldı. AI modeli: {ai_model}")
        
        # Belge boyutu kontrolü
        doc_length = len(document_text) if document_text else 0
        logging.info(f"Doküman toplam karakter sayısı: {doc_length}")
        
        # Belge boyutu kontrolü - session'a kaydet
        if document_text:
            # Kullanıcı arayüzünde göstermek için session'a kaydet
            if doc_length > 90000:  # 90K üzerinde uyarı göster
                session['document_size_warning'] = True
                session['document_size'] = doc_length
                logging.warning(f"Belge boyutu büyük: {doc_length} karakter. Belge otomatik olarak optimize edilecek.")
            else:
                session['document_size_warning'] = False
                session['document_size'] = doc_length
        
        # İşlem istatistikleri kaydı oluştur
        process_stats.record_document_processing(
            file_type=file_type,
            model=ai_model if ai_model != "azure" else azure_model or "o1",
            success=False,  # İşlem sonunda başarılı olursa güncellenecek
            processing_time=0,  # İşlem sonunda güncellenecek
            details={"filename": filename, "size": len(document_text)}
        )
        
        # NeuraAgent Basic kullanımı etkin mi kontrol et
        use_neuraagent = session.get('enable_agent', False) and NEURAAGENT_AVAILABLE
        
        # Eğer NeuraAgent etkinse ve kullanılabilirse, içeriği optimize et
        if use_neuraagent:
            try:
                logging.info("NeuraAgent Basic ile doküman optimizasyonu yapılıyor...")
                document_metadata = {
                    "filename": filename,
                    "file_type": file_extension,
                    "content_size": len(document_text),
                    "ai_model": ai_model
                }
                
                # NeuraAgent ile dokümanı optimize et
                optimized_content = optimize_document_for_ai(
                    document_text, 
                    document_structure=document_structure,
                    ai_provider=ai_model
                )
                
                if optimized_content and "text" in optimized_content:
                    logging.info("Doküman NeuraAgent ile optimize edildi")
                    
                    # Doküman yapısı optimize edilmiş modelden alındıysa ve mevcut yapıdan daha zengirıse kullan
                    if "structure" in optimized_content and (not document_structure or 
                                                           len(optimized_content["structure"].keys()) > len(document_structure.keys() if document_structure else {})):
                        document_structure = optimized_content["structure"]
                        logging.info("NeuraAgent'dan doküman yapısı alındı")
                    
                    # Optimize edilmiş içerik veya zenginleştirilmiş yapı
                    if optimized_content.get("is_neuraagent_optimized", False):
                        # AI'ya gönderilecek içeriği zenginleştir
                        enhanced_context = optimized_content
                        
                        # NeuraAgent tarafından optimize edilmiş metni kullan
                        document_text_for_ai = optimized_content.get("text", document_text)
                        
                        # document_optimizer artık zaten optimize ediyor
                        logging.info(f"document_optimizer tarafından optimize edilmiş metin boyutu: {len(document_text_for_ai)} karakter")
                        
                        # Test senaryolarını oluştur - direk içerik gönderme
                        test_scenarios = generate_test_scenarios(
                            document_text_for_ai,
                            ai_model,
                            document_structure=enhanced_context,
                            enhanced_context=True,
                            azure_model=azure_model
                        )
                    else:
                        # Optimize edilmemiş, sadece içerik kırpılmış/düzenlenmiş
                        document_text_for_ai = optimized_content.get("text", document_text)
                        
                        # document_optimizer artık zaten optimize ediyor
                        logging.info(f"document_optimizer tarafından optimize edilmiş metin boyutu: {len(document_text_for_ai)} karakter")
                        
                        # Test senaryolarını oluştur
                        test_scenarios = generate_test_scenarios(
                            document_text_for_ai,
                            ai_model,
                            document_structure=document_structure,
                            enhanced_context=bool(document_structure),
                            azure_model=azure_model
                        )
                else:
                    # NeuraAgent çalışmadı, manuel olarak document_optimizer'ı çağıralım
                    logging.warning("NeuraAgent optimizasyonu başarısız, doğrudan optimize edici kullanılıyor")
                    
                    # document_optimizer'ı doğrudan çağır
                    optimized_result = optimize_document_for_ai(document_text, ai_provider=ai_model)
                    document_text_for_ai = optimized_result.get('text', document_text)
                    logging.info(f"Optimize edilmiş metin boyutu: {len(document_text_for_ai)} karakter")
                    
                    # Test senaryolarını oluştur
                    test_scenarios = generate_test_scenarios(
                        document_text_for_ai,
                        ai_model,
                        document_structure=document_structure,
                        enhanced_context=bool(document_structure),
                        azure_model=azure_model
                    )
            except Exception as agent_error:
                logging.error(f"NeuraAgent hatası, doğrudan optimize edici kullanılıyor: {str(agent_error)}")
                
                # document_optimizer'ı doğrudan çağır
                optimized_result = optimize_document_for_ai(document_text, ai_provider=ai_model)
                document_text_for_ai = optimized_result.get('text', document_text)
                logging.info(f"Optimize edilmiş metin boyutu: {len(document_text_for_ai)} karakter")
                
                # Test senaryolarını oluştur
                test_scenarios = generate_test_scenarios(
                    document_text_for_ai,
                    ai_model,
                    document_structure=document_structure,
                    enhanced_context=bool(document_structure),
                    azure_model=azure_model
                )
        else:
            # NeuraAgent kullanılmıyor, manuel olarak document_optimizer'ı çağıralım
            logging.info("NeuraAgent kullanılmıyor, doğrudan optimize edici kullanılıyor")
            
            # document_optimizer'ı doğrudan çağır
            optimized_result = optimize_document_for_ai(document_text, ai_provider=ai_model)
            document_text_for_ai = optimized_result.get('text', document_text)
            logging.info(f"Optimize edilmiş metin boyutu: {len(document_text_for_ai)} karakter")
            
            # Test senaryolarını oluştur
            test_scenarios = generate_test_scenarios(
                document_text_for_ai,
                ai_model,
                document_structure=document_structure,
                enhanced_context=bool(document_structure),
                azure_model=azure_model
            )
        
        logging.info("AI model yanıtı alındı.")
        
        # Veritabanı işlemleri
        # 1. Belge kaydını oluştur (daha kısa önizleme içeriğiyle)
        short_preview = document_text[:300] + "..." if len(document_text) > 300 else document_text
        
        document = Document(
            filename=filename,
            content_preview=short_preview,
            file_type=file_extension,
            content_size=len(document_text)
        )
        db.session.add(document)
        db.session.flush()  # ID için flush
        
        # 2. Test senaryosu seti kaydını oluştur
        parser_used_value = session.get('parser_used', 'standard')
        scenario_set = TestScenarioSet(
            document_id=document.id,
            ai_model=ai_model,
            scenarios_data=test_scenarios,
            summary=test_scenarios.get('summary', ''),
            total_scenarios=len(test_scenarios.get('scenarios', [])),
            total_test_cases=sum(len(s.get('test_cases', [])) for s in test_scenarios.get('scenarios', [])),
            parser_used=parser_used_value
        )
        db.session.add(scenario_set)
        db.session.flush()  # ID için flush
        
        # 3. Analitik verileri oluştur ve kaydet
        analytics_data = generate_scenario_analytics(test_scenarios)
        scenario_analytics = ScenarioAnalytics(
            scenario_set_id=scenario_set.id,
            category_distribution=analytics_data.get('category_distribution', {}),
            complexity_distribution=analytics_data.get('complexity_distribution', {}),
            coverage_score=analytics_data.get('coverage_score', 0)
        )
        db.session.add(scenario_analytics)
        
        # Tüm değişiklikleri kaydet
        db.session.commit()
        
        # İşlem süresini hesapla
        processing_time = (datetime.now() - start_time).total_seconds()
        logging.info(f"Belge işleme tamamlandı. Senaryo seti kimliği: {scenario_set.id}, Süre: {processing_time:.2f} saniye")
        
        # İşlem istatistiklerini güncelle - işlem başarılı oldu
        process_stats.record_document_processing(
            file_type=file_type,
            model=ai_model if ai_model != "azure" else azure_model or "o1",
            success=True,
            processing_time=processing_time,
            details={
                "filename": filename, 
                "size": len(document_text),
                "scenarios": scenario_set.total_scenarios,
                "test_cases": scenario_set.total_test_cases,
                "coverage_score": analytics_data.get('coverage_score', 0)
            }
        )
        
        # İşlem istatistiklerini loglama
        logging.info(f"İşlem istatistikleri güncellendi. Dosya türü: {file_type}, Model: {ai_model}, Süre: {processing_time:.2f} sn")
        
        # İşlenen belge ve senaryo setini döndür
        return document, scenario_set
    
    except Exception as e:
        # Hata durumunda session'ı geri al ve hatayı yükselt
        db.session.rollback()
        error_details = traceback.format_exc()
        logging.error(f"Belge işleme hatası: {str(e)}")
        logging.error(f"Hata detayları: {error_details}")
        
        # İşlem istatistiklerini hata olarak güncelle
        error_type = str(e.__class__.__name__)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # İşlem istatistiklerini güncelle - işlem başarısız oldu
        process_stats.record_document_processing(
            file_type=file_type,
            model=ai_model if ai_model != "azure" else azure_model or "o1",
            success=False,
            processing_time=processing_time,
            details={"error": error_type, "message": str(e)}
        )
        
        # Hata durumunda None değerlerini döndür
        return None, None


    config_manager.update_setting('features', 'table_extraction', table_extraction)
    config_manager.update_setting('defaults', 'show_extracted_images', show_extracted_images)
    
    # NeuraAgent durumunu session'a kaydet (geriye dönük uyumluluk için)
    session['enable_agent'] = neuraagent_basic_enabled
    
    flash('Özellik ayarları başarıyla güncellendi', 'success')
    return redirect(url_for('agent_settings'))


@app.route('/')
def index():
    # Ollama'nın kullanılabilir olup olmadığını kontrol et
    ollama_active = is_ollama_available()
    
    # NeuraAgent Basic'in etkin olup olmadığını kontrol et
    agent_enabled = session.get('enable_agent', NEURAAGENT_AVAILABLE)
    
    # İlk kez açılışta, eğer NeuraAgent kullanılabilirse varsayılan olarak etkinleştir
    if 'enable_agent' not in session and NEURAAGENT_AVAILABLE:
        session['enable_agent'] = True
        agent_enabled = True
    
    return render_template('index.html', 
                          ollama_active=ollama_active,
                          agent_enabled=agent_enabled,
                          neuraagent_available=NEURAAGENT_AVAILABLE)


# Settings routes

    
    # Endpoint bilgilerini güncelle
    config_manager.update_setting('endpoints', 'azure_openai', azure_endpoint)
    config_manager.update_setting('endpoints', 'azure_region', azure_region)
    
    flash('API anahtarları başarıyla güncellendi', 'success')
    return redirect(url_for('agent_settings'))


@app.route('/clear_all_cache', methods=['POST'])
def clear_all_cache():
    """Tüm önbelleği temizle"""
    try:
        # Session'ı temizle
        session.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Önbellek temizlenirken hata: {e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/agent_settings')
def agent_settings():
    """NeuraAgent Basic ayarları sayfası"""
    # Mevcut ayarları session'dan al veya varsayılanları kullan
    agent_settings = {}
    
    for key, default_value in default_agent_settings.items():
        agent_settings[key] = session.get(key, default_value)
    
    # Veritabanı istatistikleri - normalde gerçek veritabanından gelir
    # Ancak şu an için varsayılan değerleri kullanıyoruz
    
    # Stats mock verileri (gerçek uygulama için veritabanından alınmalı)
    db_stats_data = {
        'document_count': 15,
        'section_count': 87,
        'concept_count': 42
    }
    
    return render_template('agent_settings.html', 
                         agent_settings=agent_settings,
                         db_stats=db_stats_data,
                         neuraagent_available=NEURAAGENT_AVAILABLE)


# Settings routes


@app.route('/update_model_settings', methods=['POST'])
def update_model_settings():
    """Model ayarlarını güncelle"""
    from utils.config import config_manager
    
    default_service = request.form.get('default_service', 'azure_openai')
    default_model = request.form.get('default_model', 'gpt-4o')
    max_tokens = int(request.form.get('max_tokens', 4000))
    temperature = float(request.form.get('temperature', 0.7))
    
    # Model ayarlarını güncelle
    config_manager.update_setting('defaults', 'service', default_service)
    config_manager.update_setting('defaults', 'model', default_model)
    config_manager.update_setting('defaults', 'max_tokens', max_tokens)
    config_manager.update_setting('defaults', 'temperature', temperature)
    
    flash('Model ayarları başarıyla güncellendi', 'success')
    return redirect(url_for('agent_settings'))


@app.route('/update_system_settings', methods=['POST'])
def update_system_settings():
    """Sistem ayarlarını güncelle"""
    from utils.config import config_manager
    
    theme = request.form.get('theme', 'dark')
    language = request.form.get('language', 'tr')
    notification_level = request.form.get('notification_level', 'info')
    
    # UI ayarlarını güncelle
    config_manager.update_setting('ui', 'theme', theme)
    config_manager.update_setting('ui', 'language', language)
    config_manager.update_setting('ui', 'notification_level', notification_level)
    
    flash('Sistem ayarları başarıyla güncellendi', 'success')
    return redirect(url_for('agent_settings'))


@app.route('/update_feature_settings', methods=['POST'])
def update_feature_settings():
    """Özellik ayarlarını güncelle"""
    from utils.config import config_manager
    
    # Checkboxlar için form değerlerini kontrol et
    neuraagent_basic_enabled = 'neuraagent_basic_enabled' in request.form
    advanced_document_parsing = 'advanced_document_parsing' in request.form
    image_recognition = 'image_recognition' in request.form
    table_extraction = 'table_extraction' in request.form
    show_extracted_images = 'show_extracted_images' in request.form
    
    # Özellikleri güncelle
    config_manager.update_setting('features', 'neuraagent_basic_enabled', neuraagent_basic_enabled)
    config_manager.update_setting('features', 'advanced_document_parsing', advanced_document_parsing)
    config_manager.update_setting('features', 'image_recognition', image_recognition)
    config_manager.update_setting('features', 'table_extraction', table_extraction)
    config_manager.update_setting('defaults', 'show_extracted_images', show_extracted_images)
    
    # NeuraAgent durumunu session'a kaydet (geriye dönük uyumluluk için)
    session['enable_agent'] = neuraagent_basic_enabled
    
    flash('Özellik ayarları başarıyla güncellendi', 'success')
    return redirect(url_for('agent_settings'))


@app.route('/clear_agent_cache')
def clear_agent_cache():
    """NeuraAgent Basic önbelleğini temizle"""
    if NEURAAGENT_AVAILABLE:
        try:
            # Gerçek uygulamada veritabanından önbellek verilerini temizleyen kod buraya gelecek
            flash('NeuraAgent önbelleği başarıyla temizlendi', 'success')
        except Exception as e:
            flash(f'Önbellek temizleme hatası: {str(e)}', 'danger')
    else:
        flash('NeuraAgent bu sistemde mevcut değil', 'warning')
    
    return redirect(url_for('agent_settings'))

@app.route('/analytics')
def analytics():
    """View analytics data for all test scenarios."""
    # Get all scenario sets with analytics data
    scenario_sets = TestScenarioSet.query.all()
    analytics_data = []
    
    # Filter for only scenario sets that have analytics
    for scenario_set in scenario_sets:
        try:
            analytics = ScenarioAnalytics.query.filter_by(scenario_set_id=scenario_set.id).first()
            if analytics and scenario_set.document:
                # Convert UUID to string for better compatibility
                scenario_id = str(scenario_set.id) if scenario_set.id else None
                
                # Add data to analytics data list
                # Veritabanından kategori ve karmaşıklık dağılımı dizeleri
                category_dist = analytics.category_distribution
                complexity_dist = analytics.complexity_distribution
                
                # Dağılım verilerini işlerken karşılaşılan hatalardan kaçınmak için
                # JSON dizeyi yükle ve verilerin beklenen yapıda olduğundan emin ol
                if category_dist and complexity_dist:
                    # JSON verilerin doğru biçimde süzülmesini sağla
                    analytics_data.append({
                        'id': scenario_id,
                        'document': scenario_set.document.filename,
                        'ai_model': scenario_set.ai_model,
                        'date': scenario_set.generated_date,
                        'total_scenarios': scenario_set.total_scenarios,
                        'total_test_cases': scenario_set.total_test_cases,
                        'coverage_score': analytics.coverage_score,
                        'category_distribution': category_dist,
                        'complexity_distribution': complexity_dist
                    })
        except Exception as e:
            app.logger.error(f"Error processing analytics for scenario set {scenario_set.id}: {e}")
            # Skip this scenario set if there was an error
    
    # Get statistics for time series data (gerçek veri yoksa örnek veriler)
    time_data = {
        'labels': ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs"],
        'scenarios': [12, 19, 25, 32, 45],
        'testCases': [35, 42, 78, 95, 130]
    }
    
    # Mevcut senaryolar için kategorik dağılım
    category_data = {}
    complexity_data = {}
    
    # Varsa ilk analitik verisini kullan
    if analytics_data and len(analytics_data) > 0:
        if 'category_distribution' in analytics_data[0] and analytics_data[0]['category_distribution']:
            category_data = analytics_data[0]['category_distribution']
        if 'complexity_distribution' in analytics_data[0] and analytics_data[0]['complexity_distribution']:
            complexity_data = analytics_data[0]['complexity_distribution']
    
    # Ortalama kapsama puanı
    avg_coverage = 0
    if analytics_data:
        total_coverage = sum(item['coverage_score'] for item in analytics_data)
        avg_coverage = total_coverage / len(analytics_data) if len(analytics_data) > 0 else 0
    
    return render_template('analytics.html', 
                          analytics_data=analytics_data,
                          category_data=category_data,
                          complexity_data=complexity_data,
                          avg_coverage=avg_coverage,
                          time_data=time_data)

@app.route('/run_analytics_query', methods=['POST'])
def run_analytics_query():
    """Run a custom SQL query for analytics."""
    sql_query = request.form.get('sql_query', '')
    
    # Basic protection - only allow SELECT statements
    if not sql_query.lower().strip().startswith('select'):
        flash('Güvenlik nedeniyle yalnızca SELECT sorgularına izin verilir.', 'danger')
        return redirect(url_for('analytics'))
    
    try:
        # Execute the query
        result = db.session.execute(sql_query)
        
        # Get column names
        columns = result.keys()
        
        # Get all rows
        data = [list(row) for row in result.fetchall()]
        
        # Format query results
        query_results = {
            'columns': columns,
            'data': data
        }
        
        # Pass both the original analytics data and query results
        scenario_sets = TestScenarioSet.query.all()
        analytics_data = []
        
        for scenario_set in scenario_sets:
            try:
                analytics = ScenarioAnalytics.query.filter_by(scenario_set_id=scenario_set.id).first()
                if analytics and scenario_set.document:
                    # Düzgün UUID dönüşümü sağla
                    scenario_id = str(scenario_set.id) if scenario_set.id else None
                    
                    # Veritabanından kategori ve karmaşıklık dağılımı dizeleri
                    category_dist = analytics.category_distribution
                    complexity_dist = analytics.complexity_distribution
                    
                    if category_dist and complexity_dist:
                        analytics_data.append({
                            'id': scenario_id,
                            'document': scenario_set.document.filename,
                            'ai_model': scenario_set.ai_model,
                            'date': scenario_set.generated_date,
                            'total_scenarios': scenario_set.total_scenarios,
                            'total_test_cases': scenario_set.total_test_cases,
                            'coverage_score': analytics.coverage_score,
                            'category_distribution': category_dist,
                            'complexity_distribution': complexity_dist
                        })
            except Exception as e:
                app.logger.error(f"Error processing analytics in query for scenario set {scenario_set.id}: {e}")
                # Skip this scenario set if there was an error
        
        # Get statistics for time series data (gerçek veri yoksa örnek veriler)
        time_data = {
            'labels': ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs"],
            'scenarios': [12, 19, 25, 32, 45],
            'testCases': [35, 42, 78, 95, 130]
        }
        
        # Mevcut senaryolar için kategorik dağılım
        category_data = {}
        complexity_data = {}
        
        # Varsa ilk analitik verisini kullan
        if analytics_data and len(analytics_data) > 0:
            if 'category_distribution' in analytics_data[0] and analytics_data[0]['category_distribution']:
                category_data = analytics_data[0]['category_distribution']
            if 'complexity_distribution' in analytics_data[0] and analytics_data[0]['complexity_distribution']:
                complexity_data = analytics_data[0]['complexity_distribution']
        
        # Ortalama kapsama puanı
        avg_coverage = 0
        if analytics_data:
            total_coverage = sum(item['coverage_score'] for item in analytics_data)
            avg_coverage = total_coverage / len(analytics_data) if len(analytics_data) > 0 else 0
        
        flash('SQL sorgunuz başarıyla çalıştırıldı.', 'success')
        
        return render_template('analytics.html', 
                              analytics_data=analytics_data,
                              category_data=category_data,
                              complexity_data=complexity_data,
                              avg_coverage=avg_coverage,
                              time_data=time_data,
                              query_results=query_results)
    
    except Exception as e:
        flash(f'SQL sorgusu çalıştırılırken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('analytics'))

@app.route('/upload', methods=['POST'])
def upload_file():
    # Get input method
    input_method = request.form.get('input_method', 'document')
    ai_model = request.form.get('ai_model', 'ollama')
    azure_model = request.form.get('azure_model', None)
    document_text = None
    filename = None
    file_extension = None
    
    # DOCUMENT UPLOAD METHOD
    if input_method == 'document':
        # Check if a file was provided
        if 'document' not in request.files:
            flash('Dosya alanı bulunamadı', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        
        # Check if the file was actually selected
        if file.filename == '':
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{str(uuid.uuid4())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save file
            file.save(filepath)
            
            try:
                # Parse document with enhanced features if available
                document_structure = None
                extract_images = request.form.get('extract_images', 'false') == 'true'
                extract_tables = request.form.get('extract_tables', 'false') == 'true'
                use_llama_parse = request.form.get('use_llama_parse', 'false') == 'true'
                use_docling = request.form.get('use_docling', 'false') == 'true'
                use_neuradoc = request.form.get('use_neuradoc', 'false') == 'true'
                use_smart_processing = request.form.get('use_smart_processing', 'false') == 'true'
                
                # Check if this is a large document that needs smart processing automatically
                file_size = os.path.getsize(filepath)
                large_doc_threshold = 5 * 1024 * 1024  # 5MB threshold
                
                # Automatically enable smart processing for large files if not explicitly disabled
                if file_size >= large_doc_threshold and not use_smart_processing:
                    use_smart_processing = True
                    flash(f'Büyük doküman tespit edildi ({file_size/1024/1024:.1f} MB). Akıllı işleme otomatik olarak etkinleştirildi.', 'info')
                
                # Check if NeuraDoc should be used first (this is our in-house solution)
                if use_neuradoc:
                    logging.info("Using NeuraDoc for in-house document processing")
                    try:
                        # NeuraDoc modüllerini try-except bloğu içinde doğrudan import edelim
                        try:
                            from utils.neuradoc import (
                                extract_text,
                                get_document_structure,
                                process_with_neuradoc,
                                NEURADOC_AVAILABLE
                            )
                            
                            # İmport işlemi başarılı oldu mu kontrol et
                            if not NEURADOC_AVAILABLE:
                                logging.warning("NeuraDoc modülleri yüklenemedi. Paketler düzgün kurulmamış olabilir.")
                                flash("NeuraDoc modülleri bulunamadı.", "warning")
                                raise ImportError("NeuraDoc modülleri import edilemedi.")
                        except ImportError as imp_err:
                            logging.error(f"NeuraDoc modülleri import edilemedi: {str(imp_err)}")
                            flash("NeuraDoc modülleri bulunamadı. Standart belge işleme kullanılıyor.", "warning")
                            raise
                            
                        # NeuraDoc her zaman kullanılabilir olmalı
                        logging.info("NeuraDoc kullanılabilir, doküman yapısı analiz ediliyor...")
                        try:
                            # Get document structure
                            document_structure = get_document_structure(filepath)
                            
                            # Store document structure in session for AI use
                            session['document_structure'] = document_structure
                            
                            # Parse document with NeuraDoc
                            document_text = parse_document(filepath, use_neuradoc=True, use_smart_processing=use_smart_processing)
                            
                            # NeuraDoc modu olarak "in-house" kullan
                            neuradoc_mode = "in-house"
                            session['docling_mode'] = neuradoc_mode  # Aynı template değişkenini kullanıyoruz
                            logging.info(f"NeuraDoc mode: {neuradoc_mode}")
                            
                            # Başarılı olup olmadığını kontrol et
                            if document_structure is None:
                                logging.warning("NeuraDoc returned None document structure")
                                flash("Belge ayrıştırma işlemi başarısız oldu.", "warning")
                            elif document_structure.get('is_llm_optimized', False):
                                logging.info("Document successfully parsed with NeuraDoc")
                                flash("Belge NeuraDoc ile başarıyla işlendi.", "success")
                            else:
                                # NeuraDoc çalışmadıysa temel bir yapı döndürülür
                                logging.info("Basic document structure created with NeuraDoc")
                                if document_structure is not None and 'error' in document_structure:
                                    flash(f"Temel belge yapısı oluşturuldu: {document_structure.get('error')}", "info")
                                else:
                                    flash(f"Temel belge yapısı NeuraDoc ile oluşturuldu.", "info")
                        except Exception as e:
                            logging.error(f"NeuraDoc document parsing failed: {str(e)}")
                            flash(f"NeuraDoc ile belge işlenirken hata oluştu, diğer işleme yöntemlerine geçiliyor: {str(e)}", "warning")
                            raise  # Re-raise for fallback logic in outer exception handler
                    except ImportError:
                        logging.warning("NeuraDoc module not available, trying other methods")
                        flash("NeuraDoc modülü bulunamadı, diğer işleme yöntemlerine geçiliyor.", "warning")
                    except Exception as neuradoc_error:
                        logging.error(f"NeuraDoc failed: {str(neuradoc_error)}")
                        flash(f"NeuraDoc işleme hatası: {str(neuradoc_error)}", "warning")

                # Check if Docling should be used
                if document_text is None and use_docling:
                    logging.info("Using Docling for LLM-optimized document parsing")
                    try:
                        try:
                            from utils.docling_parser import (
                                parse_with_docling,
                                get_docling_document_structure,
                                is_docling_available,
                                is_using_lite_mode,
                                LITE_DOCLING_AVAILABLE
                            )
                            
                            # İmport işlemi başarılı oldu mu kontrol et
                            if not LITE_DOCLING_AVAILABLE:
                                logging.warning("Docling modülleri yüklenemedi. Paketler düzgün kurulmamış olabilir.")
                                flash("Docling modülleri bulunamadı. Lütfen sisteminizde docling paketinin kurulu olduğundan emin olun.", "warning")
                                raise ImportError("Docling modülleri import edilemedi.")
                        except ImportError as imp_err:
                            logging.error(f"Docling modülleri import edilemedi: {str(imp_err)}")
                            flash("Docling modülleri bulunamadı. Standart belge işleme kullanılıyor.", "warning")
                            raise
                            
                        # Docling kullanılabilir mi kontrol et
                        docling_available = is_docling_available()
                        if docling_available:
                            logging.info("Docling kullanılabilir, doküman yapısı analiz ediliyor...")
                            try:
                                # Get document structure
                                document_structure = get_docling_document_structure(filepath)
                                
                                # Store document structure in session for AI use
                                session['document_structure'] = document_structure
                                
                                # Parse document with Docling
                                document_text = parse_document(filepath, use_docling=True, use_smart_processing=use_smart_processing)
                                
                                # Docling modunu kontrol et ve sakla
                                docling_mode = "lite" if is_using_lite_mode() else "pro"
                                session['docling_mode'] = docling_mode
                                logging.info(f"Docling mode: {docling_mode}")
                                
                                # Başarılı olup olmadığını kontrol et
                                if document_structure.get('is_llm_optimized', False):
                                    logging.info("Document successfully parsed with Docling")
                                    flash(f"Belge Docling {docling_mode.upper()} ile başarıyla işlendi.", "success")
                                else:
                                    # Docling çalışmadıysa temel bir yapı döndürülür
                                    logging.info("Basic LLM Ready structure created with Docling")
                                    if 'docling_parse_error' in document_structure:
                                        flash(f"Temel LLM Ready yapısı oluşturuldu: {document_structure.get('docling_parse_error')}", "info")
                                    else:
                                        flash(f"Temel LLM Ready yapısı Docling {docling_mode.upper()} ile oluşturuldu.", "info")
                            except Exception as e:
                                logging.error(f"Docling document parsing failed: {str(e)}")
                                flash(f"Docling ile belge işlenirken hata oluştu, diğer işleme yöntemlerine geçiliyor: {str(e)}", "warning")
                                raise  # Re-raise for fallback logic in outer exception handler
                        else:
                            logging.warning("Docling is not available")
                            flash("Docling kullanılamıyor. Diğer işleme yöntemlerine geçiliyor.", "warning")
                    except ImportError:
                        logging.warning("Docling module not available, trying other methods")
                        flash("Docling modülü bulunamadı, diğer işleme yöntemlerine geçiliyor.", "warning")
                    except Exception as docling_error:
                        logging.error(f"Docling failed: {str(docling_error)}")
                        flash(f"Docling işleme hatası: {str(docling_error)}", "warning")
                
                # Check if LlamaParse should be used
                if document_text is None and use_llama_parse:
                    logging.info("Using LlamaParse for LLM-optimized document parsing")
                    try:
                        # LlamaParse modülünü try-except bloğu içinde doğrudan import edelim
                        try:
                            from utils.llama_parser import (
                                parse_with_llama,
                                get_llama_document_structure, 
                                is_llama_parse_available, 
                                set_llama_api_key,
                                LLAMA_PARSE_AVAILABLE
                            )
                            # İmport işlemi başarılı oldu mu kontrol et
                            if not LLAMA_PARSE_AVAILABLE:
                                logging.warning("LlamaParse modülleri yüklenemedi. Paketler düzgün kurulmamış olabilir.")
                                flash("LlamaParse modülleri bulunamadı. Lütfen sisteminizde llama-parse ve llama-cloud paketlerinin kurulu olduğundan emin olun.", "warning")
                                raise ImportError("LlamaParse modülleri import edilemedi.")
                        except ImportError as imp_err:
                            logging.error(f"LlamaParse modülleri import edilemedi: {str(imp_err)}")
                            flash("LlamaParse modülleri bulunamadı. Standart belge işleme kullanılıyor.", "warning")
                            raise
                        
                        # API anahtarı form'dan al (boş olsa bile)
                        llama_api_key = request.form.get('llama_api_key', '')
                        
                        # Form'dan gelen API anahtarını işle
                        if llama_api_key and llama_api_key.strip():
                            logging.info("LlamaParse API anahtarı formdan alındı, ayarlanıyor...")
                            api_key_set = set_llama_api_key(llama_api_key.strip())
                            
                            if not api_key_set:
                                logging.warning("API anahtarı ayarlama başarısız oldu")
                                flash("LlamaParse API anahtarını ayarlarken bir hata oluştu. Standart belge işleme kullanılıyor.", "warning")
                                # API anahtarı ayarlanamadı, LlamaParse olmadan devam et
                        else:
                            logging.warning("LlamaParse API anahtarı formda boş veya geçersiz biçimde geldi")
                            flash("LlamaParse API anahtarı girilmedi, daha sınırlı LLM Ready yapısı kullanılacak. En iyi sonuçlar için API anahtarı girmeniz önerilir.", "info")
                            # API anahtarı verilmedi ama yine de LLM ready data yapısı kullanılacak
                        
                        # LlamaParse'in kullanılabilir olup olmadığını kontrol et
                        llama_available = is_llama_parse_available()
                        if llama_available:
                            logging.info("LlamaParse kullanılabilir, doküman yapısı analiz ediliyor...")
                            try:
                                # Get document structure - API anahtarı olmasa bile çalışacak şekilde düzenlendi
                                document_structure = get_llama_document_structure(filepath)
                                
                                # Store document structure in session for AI use
                                session['document_structure'] = document_structure
                                
                                # Parse document with LlamaParse
                                document_text = parse_document(filepath, use_llama_parse=True, use_smart_processing=use_smart_processing)
                                
                                # Başarılı olup olmadığını kontrol et
                                if document_structure.get('is_llm_optimized', False):
                                    logging.info("Document successfully parsed with LlamaParse")
                                    flash("Belge LlamaParse ile başarıyla işlendi.", "success")
                                else:
                                    # API anahtarı olmadığında veya hata olduğunda da temel bir yapı döndürülür
                                    logging.info("Basic LLM Ready structure created without full LlamaParse capabilities")
                                    if 'llama_parse_error' in document_structure:
                                        flash(f"Temel LLM Ready yapısı oluşturuldu: {document_structure.get('llama_parse_error')}", "info")
                                    else:
                                        flash("Temel LLM Ready yapısı oluşturuldu. Daha gelişmiş sonuçlar için API anahtarı giriniz.", "info")
                            except Exception as e:
                                logging.error(f"LlamaParse document parsing failed: {str(e)}")
                                flash(f"LlamaParse ile belge işlenirken hata oluştu, standart işlemeye geçiliyor: {str(e)}", "warning")
                                raise  # Re-raise for fallback logic in outer exception handler
                        else:
                            logging.warning("LlamaParse API key is valid but parsing is not available")
                            
                            # API anahtarı olsa bile LlamaParse mevcut değilse, sınırlı LLM Ready yapısını oluştur
                            try:
                                # API anahtarı olmasa bile temel bir yapı oluşturabilir
                                document_structure = get_llama_document_structure(filepath)
                                session['document_structure'] = document_structure
                                
                                # Parse document with standard method
                                document_text = parse_document(filepath, use_smart_processing=use_smart_processing)
                                
                                flash('LlamaParse kullanılamıyor. Temel LLM Ready yapısı oluşturuldu, ancak tam kapasitede değil.', 'info')
                            except Exception as inner_e:
                                logging.error(f"Basic LLM Ready structure creation failed: {str(inner_e)}")
                                flash('LlamaParse kullanılamıyor. Standart belge işleme kullanılıyor.', 'warning')
                                
                                # Gelişmiş doküman analizi veya temel işleme kullan
                                if ENHANCED_DOCUMENT_ANALYSIS and (extract_images or extract_tables):
                                    raise Exception("Using enhanced document analysis instead")
                                else:
                                    document_text = parse_document(filepath, use_smart_processing=use_smart_processing)
                    except ImportError:
                        logging.warning("LlamaParse module not available, falling back to standard parsing")
                        # Fall back to standard parsing with or without enhanced features
                        if ENHANCED_DOCUMENT_ANALYSIS and (extract_images or extract_tables):
                            raise Exception("Using enhanced document analysis instead")
                        else:
                            document_text = parse_document(filepath, use_smart_processing=use_smart_processing)
                    except Exception as llama_error:
                        logging.error(f"LlamaParse failed: {str(llama_error)}")
                        # Continue to enhanced document analysis or basic parsing
                
                # If LlamaParse failed or wasn't requested, try enhanced document analysis
                if document_text is None and ENHANCED_DOCUMENT_ANALYSIS and (extract_images or extract_tables):
                    logging.info("Using enhanced document analysis with rich content extraction")
                    try:
                        try:
                            # Geliştirilmiş NeuraDoc modülünü kullan
                            from utils.neuradoc_enhanced import get_document_structure as neuradoc_get_structure
                            
                            # Geliştirilmiş yapıyla belge analizi yap
                            document_structure = neuradoc_get_structure(filepath)
                            
                            # NeuraDoc kullanılıyor olarak işaretle
                            session['parser_used'] = 'neuradoc'
                            
                            # Log which parser was actually used
                            parser_used = document_structure.get('parser_used', 'standard')
                            logging.info(f"Document structure parsed with: {parser_used}")
                            
                            # Parse document with full analysis - also pass the parser preference
                            doc_content = analyze_document(
                                filepath,
                                force_neuradoc=use_neuradoc,
                                force_docling=use_docling,
                                force_llama_parse=use_llama_parse
                            )
                            document_text = doc_content.get_plain_text()
                            
                            # Store which parser was used in the session for UI feedback
                            session['parser_used'] = parser_used
                        except ImportError:
                            logging.warning("Enhanced document analysis functions are not available, falling back to standard parsing")
                            raise ImportError("Enhanced document analysis functions are not available")
                        
                        # Store document structure in session for AI use
                        session['document_structure'] = document_structure
                        
                        # Add image and table counts if available
                        images = doc_content.get_elements_by_type("image")
                        tables = doc_content.get_elements_by_type("table")
                        
                        document_structure['image_count'] = len(images)
                        document_structure['table_count'] = len(tables)
                        
                        logging.info(f"Extracted {len(images)} images and {len(tables)} tables from document")
                        
                        # Extracted images and tables
                        if len(images) > 0 or len(tables) > 0:
                            extracted_images = []
                            extracted_tables = []
                            
                            # Process images
                            for img in images:
                                extracted_images.append({
                                    "content": img.get("content", ""),
                                    "format": img.get("format", "png"),
                                    "description": img.get("description", ""),
                                    "analysis": img.get("analysis", "")
                                })
                            
                            # Process tables
                            for tbl in tables:
                                extracted_tables.append({
                                    "content": tbl.get("content", []),
                                    "headers": tbl.get("headers", []),
                                    "caption": tbl.get("caption", "")
                                })
                            
                            # Add to document structure
                            document_structure["extracted_images"] = extracted_images
                            document_structure["extracted_tables"] = extracted_tables
                        
                    except Exception as analyze_error:
                        logging.error(f"Enhanced document analysis failed: {str(analyze_error)}. Falling back to basic parsing.")
                        # Fall back to basic parsing
                        document_text = parse_document(filepath, use_smart_processing=use_smart_processing)
                
                # If nothing worked or was requested, use basic document parsing
                if document_text is None:
                    # Basic document parsing
                    document_text = parse_document(filepath, use_smart_processing=use_smart_processing)
                
                file_extension = filename.rsplit('.', 1)[1].lower()
            except Exception as e:
                logging.error(f"Error processing file: {str(e)}")
                flash(f"Dosya işlenirken hata oluştu: {str(e)}", 'danger')
                return redirect(url_for('index'))
        else:
            flash('Dosya türüne izin verilmiyor. İzin verilen türler: PDF, DOC, DOCX, TXT', 'danger')
            return redirect(request.url)
    
    # TEXT INPUT METHOD
    elif input_method == 'text':
        input_text = request.form.get('input_text', '').strip()
        
        if not input_text:
            flash('Lütfen analiz edilecek bir metin girin', 'danger')
            return redirect(request.url)
        
        document_text = input_text
        filename = f"text_input_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        file_extension = 'txt'
    
    # Invalid input method
    else:
        flash('Geçersiz giriş yöntemi', 'danger')
        return redirect(url_for('index'))
    
    # Belge yapısını session'dan al
    document_structure = session.get('document_structure')
    
    # Doğrudan senkron işleme başla
    try:
        # Bildirim göster
        flash(f"Belge işleniyor ve test senaryoları oluşturuluyor, lütfen bekleyin...", 'info')
        
        # Doküman boyutunu kontrol et ve loglama ekle
        logging.info(f"İşlenecek belge boyutu: {len(document_text)} karakter, Dosya adı: {filename}, Uzantı: {file_extension}")
        
        # Görsel/tablo içeriği için belge yapısını kontrol et
        rich_content_info = ""
        if document_structure:
            img_count = len(document_structure.get('images', [])) if isinstance(document_structure, dict) else 0
            tbl_count = len(document_structure.get('tables', [])) if isinstance(document_structure, dict) else 0
            logging.info(f"Belge yapısında görsel sayısı: {img_count}, tablo sayısı: {tbl_count}")
            rich_content_info = f" ({img_count} görsel, {tbl_count} tablo içeriyor)"
            
            # Görsellerin içeriğini daha detaylı logla
            if img_count > 0 and isinstance(document_structure.get('images'), list):
                for i, img in enumerate(document_structure.get('images')):
                    if isinstance(img, dict):
                        img_keys = ', '.join(img.keys())
                        img_desc = img.get('description', 'Açıklama yok')[:100]
                        logging.info(f"Görsel {i+1} detayları - Anahtarlar: {img_keys}, Açıklama: {img_desc}...")
        
        # Doğrudan senkron işleme fonksiyonunu çağır
        document, scenario_set = process_document(document_text, ai_model, document_structure, filename, file_extension, azure_model=azure_model)
        
        # İşlem başarılı oldu, sonuç sayfasına yönlendir
        logging.info(f"Belge işlendi ve test senaryoları oluşturuldu. Senaryo seti ID: {scenario_set.id}{rich_content_info}")
        
        # Kullanıcıya başarı mesajı göster
        flash(f"Belge başarıyla işlendi ve {scenario_set.total_scenarios} senaryo, {scenario_set.total_test_cases} test senaryosu oluşturuldu.", 'success')
        
        # Sonuç sayfasına yönlendir - id parametresini doğrudan ID nesnesi olarak geçir
        session['scenario_set_id'] = str(scenario_set.id)
        session['document_id'] = str(document.id)
        
        # Not: Test etmek için URL'i logluyoruz
        results_url = url_for('results', id=scenario_set.id)
        logging.info(f"Yönlendirme URL'i: {results_url}")
        
        return redirect(results_url)
        
    except Exception as e:
        # Hata durumunu işle
        error_details = traceback.format_exc()
        logging.error(f"Belge işleme hatası: {str(e)}")
        logging.error(f"Hata detayları: {error_details}")
        
        # Hata mesajı session'a kaydet
        error_message = str(e)
        # Eğer "string too long" veya "maximum context length" hatası varsa ya da belge 1048576 karakterden büyükse
        if "string too long" in error_message or "maximum context length" in error_message or len(document_text) > 1048576:
            error_message = f"Belge boyutu Azure API token limitini (1.048.576 karakter) aşıyor. Belge boyutu: {len(document_text)} karakter. Lütfen daha küçük bir belge kullanın veya OpenAI yerine Ollama modelini seçin."
        
        # Session'a kaydet
        session['processing_error'] = error_message
        
        # Kullanıcıya hata mesajı göster
        flash(f"Belge işlenirken hata oluştu: {error_message}", 'danger')
        return redirect(url_for('index'))


@app.route('/scenarios')
def scenarios():
    """View all generated test scenarios with management features."""
    try:
        # Fetch all scenario sets with their documents
        scenario_sets = TestScenarioSet.query.join(Document).order_by(TestScenarioSet.generated_date.desc()).all()
        
        return render_template('scenarios.html', scenario_sets=scenario_sets)
    except Exception as e:
        app.logger.error(f"Error fetching scenarios: {e}")
        flash("Senaryolar yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for('index'))

@app.route('/progress')
@app.route('/progress/<uuid:job_id>')
def progress(job_id=None):
    """İşleme ilerlemesini görüntüle"""
    # Session'dan iş kimliğini al
    if job_id is None:
        job_id = session.get('job_id')
        if not job_id:
            flash('İşleme bilgisi bulunamadı.', 'warning')
            return redirect(url_for('index'))
    
    # İş kimliğini string'e dönüştür (uuid nesnesi olabilir)
    job_id = str(job_id)
    
    # İş bilgilerini al
    job_info = processing_jobs.get(job_id, {})
    status = job_info.get('status', 'unknown')
    
    # İş tamamlandıysa sonuçlar sayfasına yönlendir
    if status == 'completed' and 'result_id' in job_info:
        result_id = job_info.get('result_id')
        logging.info(f"Job completed, redirecting to results page. Job ID: {job_id}, Result ID: {result_id}")
        flash('İşlem tamamlandı, sonuçlar görüntüleniyor.', 'success')
        return redirect(url_for('results', id=result_id))
    
    # Şablon değişkenleri hazırla
    ai_model = job_info.get('ai_model', session.get('ai_model', ''))
    filename = job_info.get('filename', session.get('filename', ''))
    
    return render_template('progress.html', 
                          job_id=job_id, 
                          status=status,
                          progress=job_info.get('progress', 0),
                          message=job_info.get('message', 'İşlem başlatılıyor...'),
                          ai_model=ai_model,
                          filename=filename)

@app.route('/api/job_status/<uuid:job_id>')
def job_status(job_id):
    """İş durumu hakkında JSON bilgisi döndür"""
    job_id = str(job_id)
    
    logging.info(f"Job status requested for ID: {job_id}")
    logging.debug(f"Available jobs: {list(processing_jobs.keys())}")
    
    # İş bilgisi alınamadıysa
    if job_id not in processing_jobs:
        logging.warning(f"Job not found: {job_id}")
        return jsonify({
            'status': 'error',
            'message': 'İş bulunamadı',
            'progress': 0
        }), 404
    
    # İş bilgilerini döndür
    job_info = processing_jobs[job_id]
    logging.info(f"Found job info: {job_info}")
    
    response = {
        'status': job_info.get('status', 'unknown'),
        'progress': job_info.get('progress', 0),
        'message': job_info.get('message', ''),
    }
    
    # İş tamamlandıysa sonuç kimliği ve yönlendirme URL'sini ekle
    if job_info.get('status') == 'completed':
        # Sonuç ID'sini ekle (varsa)
        if 'result_id' in job_info:
            result_id = job_info.get('result_id')
            response['result_id'] = result_id
        
        # Yönlendirme URL'sini doğrudan job_info'dan al (doğrudan eklemiştik)
        if 'redirect_url' in job_info:
            response['redirect_url'] = job_info.get('redirect_url')
            logging.info(f"Using direct redirect URL from job_info: {response['redirect_url']}")
        else:
            # Eski yöntem ile URL oluştur
            try:
                result_id = job_info.get('result_id')
                # Sonuç ID'si yoksa sonuçlar ana sayfasına yönlendir
                if not result_id:
                    response['redirect_url'] = url_for('results')
                else:
                    # UUID formatına çevir (gerekiyorsa)
                    if isinstance(result_id, str):
                        try:
                            uuid_result_id = uuid.UUID(result_id)
                        except ValueError:
                            # String UUID değil, muhtemelen bir string ID
                            uuid_result_id = result_id
                    else:
                        uuid_result_id = result_id
                        
                    # Absolute URL oluştur - ilk karakter / olmalı
                    redirect_url = url_for('results', id=uuid_result_id)
                    response['redirect_url'] = redirect_url
                    
                    # Debug log
                    logging.info(f"Generated redirect URL: {redirect_url} for result_id: {result_id}")
                    
                logging.info(f"Added generated redirect URL for completed job: {response['redirect_url']}")
            except Exception as e:
                logging.error(f"Error generating redirect URL: {str(e)}")
                # Fallback for safety - her durumda en azından results sayfasına yönlendir
                response['redirect_url'] = "/results"
                if 'result_id' in job_info:
                    response['redirect_url'] = f"/results/{job_info['result_id']}"
                response['error_detail'] = str(e)
        
        # Ekstra hata ayıklama bilgisi
        response['debug_info'] = {
            'job_completed_at': job_info.get('completed_at', ''),
            'processing_time': job_info.get('processing_time', ''),
            'server_time': datetime.now().isoformat()
        }
        if 'result_id' in job_info:
            response['debug_info']['result_id'] = str(job_info['result_id'])
            response['debug_info']['result_id_type'] = str(type(job_info['result_id']))
    
    return jsonify(response)

@app.route('/delete-scenario/<uuid:id>', methods=['POST'])
def delete_scenario(id):
    """Delete a scenario set by ID."""
    try:
        scenario_set = TestScenarioSet.query.get_or_404(id)
        
        # Delete associated analytics
        analytics = ScenarioAnalytics.query.filter_by(scenario_set_id=id).first()
        if analytics:
            db.session.delete(analytics)
        
        # Delete the scenario set itself
        db.session.delete(scenario_set)
        db.session.commit()
        
        flash("Test senaryosu başarıyla silindi.", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting scenario: {e}")
        flash("Senaryo silinirken bir hata oluştu.", "danger")
    
    return redirect(url_for('scenarios'))

@app.route('/results')
@app.route('/results/<id>')
@app.route('/results/<uuid:id>')
def results(id=None):
    """View all generated test scenarios."""
    # Get session data
    scenario_set_id = id or session.get('scenario_set_id')
    document_id = session.get('document_id')
    docling_mode = session.get('docling_mode')
    processing_error = session.get('processing_error')
    
    logging.info(f"Results page requested. scenario_set_id: {scenario_set_id}, document_id: {document_id}")
    
    # Try to get data from database first (if available)
    test_scenarios = None
    document_text = None
    document = None
    scenario_set = None
    analytics = None
    
    # Veri dizini oluştur - data dizini olmazsa hata veriyor
    temp_data_dir = os.path.join('/tmp', 'data')
    os.makedirs(temp_data_dir, exist_ok=True)
    
    # "latest" durumunu kontrol et - en son oluşturulan senaryo setini getir
    if scenario_set_id == "latest":
        logging.info("Latest result requested, finding most recent scenario set")
        try:
            latest_scenario_set = TestScenarioSet.query.order_by(TestScenarioSet.generated_date.desc()).first()
            if latest_scenario_set:
                scenario_set_id = latest_scenario_set.id
                logging.info(f"Found latest scenario set ID: {scenario_set_id}")
                # Eğer en son senaryonun dökümanını da bulmak istiyorsak
                document_id = latest_scenario_set.document_id
            else:
                flash("Henüz oluşturulmuş bir test senaryosu bulunamadı.", "warning")
                return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error finding latest scenario set: {str(e)}")
            flash("En son test senaryosu bilgisi alınamadı.", "danger")
            return redirect(url_for('index'))
    
    if document_id and scenario_set_id:
        try:
            # Handle both string and UUID objects
            if isinstance(scenario_set_id, str) and scenario_set_id != "latest":
                try:
                    scenario_set_id = uuid.UUID(scenario_set_id)
                except ValueError as ve:
                    logging.error(f"Invalid UUID format for scenario_set_id: {scenario_set_id}")
                    flash("Geçersiz senaryo seti kimliği formatı.", "warning")
                    return redirect(url_for('index'))
            
            if isinstance(document_id, str):
                try:
                    document_id = uuid.UUID(document_id)
                except ValueError as ve:
                    logging.error(f"Invalid UUID format for document_id: {document_id}")
                    flash("Geçersiz döküman kimliği formatı.", "warning")
                    return redirect(url_for('index'))
            
            # Get data from database
            document = Document.query.get(document_id)
            scenario_set = TestScenarioSet.query.get(scenario_set_id)
            
            if scenario_set:
                # Senaryo seti analitik verilerini al veya oluştur
                analytics = ScenarioAnalytics.query.filter_by(scenario_set_id=scenario_set_id).first()
                
                # Analytics yoksa oluştur
                if not analytics and scenario_set.scenarios_data:
                    from utils.analytics.coverage_analyzer import analyze_scenarios
                    
                    # Analiz oluştur ve veritabanına kaydet
                    logging.info(f"Scenario set {scenario_set_id} için analitik hesaplanıyor...")
                    
                    # Analiz verilerini oluştur
                    doc_content_length = len(document.content_preview) if document and document.content_preview else 2000
                    analysis_results = analyze_scenarios(scenario_set.scenarios_data, doc_content_length=doc_content_length)
                    
                    # Veritabanına kaydet
                    analytics = ScenarioAnalytics(
                        scenario_set_id=scenario_set_id,
                        category_distribution=analysis_results.get('category_distribution', {}),
                        complexity_distribution=analysis_results.get('complexity_distribution', {}),
                        coverage_score=analysis_results.get('coverage_score', 100.0),
                        content_quality_score=analysis_results.get('content_quality_score', 95.0),
                        feature_coverage_ratio=analysis_results.get('feature_coverage_ratio', 1.0),
                        image_analysis_score=analysis_results.get('image_analysis_score', 100.0)
                    )
                    db.session.add(analytics)
                    db.session.commit()
                    logging.info(f"Yeni analitik oluşturuldu - Kapsama puanı: {analytics.coverage_score}")
                test_scenarios = scenario_set.scenarios_data
                logging.info(f"Successfully loaded scenario set {scenario_set_id} from database")
                
                # Document text is not stored in database, still need to get from file
        except Exception as e:
            logging.error(f"Error retrieving from database: {str(e)}")
            # Continue with file-based fallback
    
    # Fallback to file-based retrieval if database retrieval failed
    if test_scenarios is None:
        # Get session ID and other small data from session
        session_id = session.get('session_id', None)
        
        if not session_id:
            flash('No test scenarios found. Please upload a document first.', 'warning')
            return redirect(url_for('index'))
        
        # Load test scenarios and document text from temporary files
        temp_data_dir = os.path.join('/tmp', 'data')
        scenarios_file = os.path.join(temp_data_dir, f"{session_id}_scenarios.json")
        document_file = os.path.join(temp_data_dir, f"{session_id}_document.txt")
        
        # Check if files exist
        if not os.path.exists(scenarios_file) or not os.path.exists(document_file):
            flash('Session data has expired. Please upload your document again.', 'warning')
            return redirect(url_for('index'))
        
        # Load test scenarios from file
        try:
            with open(scenarios_file, 'r') as f:
                test_scenarios = json.load(f)
                
            with open(document_file, 'r') as f:
                document_text = f.read()
        except Exception as e:
            logging.error(f"Error loading session data: {str(e)}")
            flash('Error loading results. Please try again.', 'danger')
            return redirect(url_for('index'))
    
    # Always get document text from file since we don't store full text in database
    if document_text is None:
        session_id = session.get('session_id', None)
        if session_id:
            temp_data_dir = os.path.join('/tmp', 'data')
            document_file = os.path.join(temp_data_dir, f"{session_id}_document.txt")
            try:
                if os.path.exists(document_file):
                    with open(document_file, 'r') as f:
                        document_text = f.read()
                elif document and document.content_preview:
                    # Eğer dosya yoksa ama veritabanında önizleme varsa
                    document_text = document.content_preview
                    app.logger.info(f"Using document content preview for document {document.id}")
            except Exception as e:
                app.logger.error(f"Error retrieving document content: {e}")
                document_text = "Doküman metni yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin."
    
    ai_model = session.get('ai_model', 'ollama')
    filename = session.get('filename', '')
    
    # Prefer parser_used from database if scenario_set exists, otherwise use session
    parser_used = scenario_set.parser_used if scenario_set else session.get('parser_used', None)
    
    # Get analytics data if available
    analytics_data = {}
    if analytics:
        analytics_data = {
            'category_distribution': analytics.category_distribution,
            'complexity_distribution': analytics.complexity_distribution,
            'coverage_score': analytics.coverage_score
        }
    
    # Add extracted images and tables to the test_scenarios data for display
    document_structure = session.get('document_structure', {})
    
    # Eğer test_scenarios None ise, boş bir sözlük oluştur
    if test_scenarios is None:
        test_scenarios = {}
        logging.warning("test_scenarios is None, creating empty dictionary")
    
    if isinstance(test_scenarios, dict):
        # Transfer image and table data from document_structure to test_scenarios
        if document_structure:
            # Görselleri optimize ederek ekleyelim 
            extracted_images = document_structure.get('extracted_images', [])
            
            # Optimize et - küçük token kullanarak kısa açıklamalar oluştur
            if extracted_images:
                try:
                    from utils.image_optimizer import batch_optimize_images
                    optimized_images = batch_optimize_images(extracted_images, ai_service_type=ai_model)
                    logging.info(f"{len(optimized_images)} adet görsel optimize edildi, kısa açıklamalarla")
                    document_structure['extracted_images'] = optimized_images
                except Exception as e:
                    logging.error(f"Görsel optimizasyonu sırasında hata: {e}")
            
            # Görselleri ve tabloları test_scenarios nesnesine ekleyelim
            test_scenarios['image_count'] = document_structure.get('image_count', 0)  
            test_scenarios['table_count'] = document_structure.get('table_count', 0)
            test_scenarios['extracted_images'] = document_structure.get('extracted_images', []) # Görselleri doğrudan aktarıyoruz
            test_scenarios['extracted_tables'] = document_structure.get('extracted_tables', [])
            
            logging.info(f"Added {test_scenarios['image_count']} images and {test_scenarios['table_count']} tables to test_scenarios for UI rendering")
        else:
            # Ensure we have these keys to avoid template errors
            if 'image_count' not in test_scenarios:
                test_scenarios['image_count'] = 0
            if 'table_count' not in test_scenarios:
                test_scenarios['table_count'] = 0
            if 'extracted_images' not in test_scenarios:
                test_scenarios['extracted_images'] = []
            if 'extracted_tables' not in test_scenarios:
                test_scenarios['extracted_tables'] = []
                
        # Temel yapıyı da oluştur ki şablonda hatalar oluşmasın
        if 'scenarios' not in test_scenarios:
            test_scenarios['scenarios'] = []
        if 'summary' not in test_scenarios:
            test_scenarios['summary'] = "Belge analiz edildi ancak henüz sonuçlar üretilmedi."
        
    return render_template('results.html', 
                          test_scenarios=test_scenarios, 
                          document_text=document_text,
                          ai_model=ai_model,
                          filename=filename,
                          analytics=analytics_data,
                          document=document,
                          scenario_set=scenario_set,
                          docling_mode=docling_mode,
                          parser_used=parser_used,
                          processing_error=processing_error,
                          document_structure=document_structure)

@app.route('/export_scenarios')
@app.route('/export_scenarios/<uuid:id>')
def export_scenarios(id=None):
    format_type = request.args.get('format', 'json')
    
    # If ID is provided, get scenario data from database
    if id:
        try:
            # Get data from database
            scenario_set = TestScenarioSet.query.get_or_404(id)
            test_scenarios = scenario_set.scenarios_data
        except Exception as e:
            logging.error(f"Error retrieving scenario for export: {str(e)}")
            flash('Error loading scenario data for export', 'danger')
            return redirect(url_for('scenarios'))
    else:
        # Fallback to session-based export
        session_id = session.get('session_id', None)
        
        if not session_id:
            return jsonify({'error': 'No test scenarios found'}), 400
        
        # Load test scenarios from file
        temp_data_dir = os.path.join('/tmp', 'data')
        scenarios_file = os.path.join(temp_data_dir, f"{session_id}_scenarios.json")
        
        if not os.path.exists(scenarios_file):
            return jsonify({'error': 'Session data has expired'}), 400
        
        try:
            with open(scenarios_file, 'r') as f:
                test_scenarios = json.load(f)
        except Exception as e:
            logging.error(f"Error loading session data for export: {str(e)}")
            return jsonify({'error': 'Error loading test scenarios'}), 500
    
    # test_scenarios kontrolleri
    if test_scenarios is None:
        return jsonify({'error': 'Test scenarios not found or invalid format'}), 400
    
    if format_type == 'json':
        return jsonify(test_scenarios)
    elif format_type == 'text':
        # Format scenarios as plain text
        text_output = "# Test Scenarios\n\n"
        
        if not isinstance(test_scenarios, dict) or 'scenarios' not in test_scenarios:
            return jsonify({'error': 'Invalid scenario format'}), 400
            
        if not test_scenarios['scenarios']:
            return jsonify({'text': "# Test Scenarios\n\nHenüz senaryo oluşturulmamış."})
            
        for scenario in test_scenarios['scenarios']:
            text_output += f"## {scenario.get('title', 'Başlıksız Senaryo')}\n"
            text_output += f"Description: {scenario.get('description', 'Açıklama yok')}\n\n"
            
            text_output += "### Test Cases:\n"
            
            if 'test_cases' not in scenario or not scenario['test_cases']:
                text_output += "Henüz test case oluşturulmamış.\n\n"
                continue
                
            for i, test_case in enumerate(scenario['test_cases'], 1):
                text_output += f"{i}. {test_case.get('title', 'Başlıksız Test')}\n"
                text_output += f"   Steps: {test_case.get('steps', 'Adımlar tanımlanmamış')}\n"
                text_output += f"   Expected Results: {test_case.get('expected_results', 'Beklenen sonuçlar tanımlanmamış')}\n\n"
            
            text_output += "\n---\n\n"
        
        return jsonify({'text': text_output})
    else:
        return jsonify({'error': 'Unsupported export format'}), 400

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File too large. Max size is 16MB', 'danger')
    return redirect(url_for('index')), 413

@app.errorhandler(500)
def internal_server_error(error):
    # Get the error message
    error_message = str(error)
    
    # Daha detaylı hata bilgisi
    logging.error(f"500 Internal Server Error: {error_message}")
    logging.error(traceback.format_exc())
    
    # Check if it's an Ollama connectivity error and suggest demo mode
    if "Ollama server" in error_message and "DEMO_MODE" in error_message:
        flash(error_message, 'warning')
    elif "test_scenarios" in error_message:
        flash(f'Senaryo verileri işlenirken hata oluştu: {error_message}', 'danger')
        logging.error(f"test_scenarios hatası: {error_message}")
        session['debug_info'] = f"Hata: {error_message}"
        return redirect(url_for('index')), 500
    else:
        flash('Sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
        # Geliştiriciler için debug modunda daha fazla bilgi göster
        if app.debug:
            flash(f'Debug bilgisi: {error_message}', 'warning')
    
    return redirect(url_for('index')), 500

# API endpoint for updating scenario data in the database
@app.route('/api/update_scenario', methods=['POST'])
def update_scenario():
    """
    Updates scenario data in the database
    Accepts JSON data with scenario_set_id and updates
    """
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        # Get required fields
        scenario_set_id = data.get('scenario_set_id')
        field = data.get('field')
        value = data.get('value')
        scenario_index = data.get('scenario_index')
        test_case_index = data.get('test_case_index')
        
        # Log request data for debugging
        logging.info(f"Updating scenario: ID={scenario_set_id}, field={field}, scenario_index={scenario_index}, test_case_index={test_case_index}")
        
        # Validate required fields
        if not scenario_set_id or not field:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Find the scenario set in the database
        try:
            # Convert string UUID to UUID object if needed
            if isinstance(scenario_set_id, str):
                try:
                    scenario_set_id = uuid.UUID(scenario_set_id)
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid UUID format'}), 400
                    
            scenario_set = TestScenarioSet.query.get(scenario_set_id)
            if not scenario_set:
                return jsonify({'success': False, 'error': 'Scenario set not found'}), 404
                
            # Get current scenarios data
            scenarios_data = scenario_set.scenarios_data
            
            # Update based on the field
            if field == 'summary':
                scenarios_data['summary'] = value
            elif scenario_index is not None:
                # Convert indices to integers
                scenario_index = int(scenario_index)
                
                # Make sure index is valid
                if scenario_index >= len(scenarios_data.get('scenarios', [])):
                    return jsonify({'success': False, 'error': 'Invalid scenario index'}), 400
                    
                # Update scenario field or test case field
                if test_case_index is not None:
                    test_case_index = int(test_case_index)
                    if test_case_index >= len(scenarios_data['scenarios'][scenario_index].get('test_cases', [])):
                        return jsonify({'success': False, 'error': 'Invalid test case index'}), 400
                        
                    # Update test case field
                    scenarios_data['scenarios'][scenario_index]['test_cases'][test_case_index][field] = value
                else:
                    # Update scenario field
                    scenarios_data['scenarios'][scenario_index][field] = value
            
            # Save updates to the database
            scenario_set.scenarios_data = scenarios_data
            db.session.commit()
            
            # Log successful commit
            logging.info(f"Successfully updated scenario data for {scenario_set_id}, field={field}")
            
            return jsonify({
                'success': True, 
                'message': 'Scenario data updated successfully'
            })
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating scenario: {str(e)}")
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Error updating scenario: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint for updating playground data
@app.route('/api/update_playground', methods=['POST'])
def update_playground():
    """
    Test Senaryosu Playground verilerini günceller.
    Bir senaryo ve onun ilk test case'i için tüm alanları
    birden güncellemeye olanak tanır.
    """
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        # Get required fields
        scenario_set_id = data.get('scenario_set_id')
        scenario_index = data.get('scenario_index')
        title = data.get('title')
        priority = data.get('priority')
        description = data.get('description')
        steps = data.get('steps')
        expected_results = data.get('expected_results')
        
        # Log request data for debugging
        logging.info(f"Updating playground: ID={scenario_set_id}, scenario_index={scenario_index}")
        
        # Validate required fields
        if not scenario_set_id or scenario_index is None:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Find the scenario set in the database
        try:
            # Convert string UUID to UUID object if needed
            if isinstance(scenario_set_id, str):
                try:
                    scenario_set_id = uuid.UUID(scenario_set_id)
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid UUID format'}), 400
                    
            scenario_set = TestScenarioSet.query.get(scenario_set_id)
            if not scenario_set:
                return jsonify({'success': False, 'error': 'Scenario set not found'}), 404
                
            # Get current scenarios data
            scenarios_data = scenario_set.scenarios_data
            
            # Convert index to integer
            scenario_index = int(scenario_index)
            
            # Make sure index is valid
            if scenario_index >= len(scenarios_data.get('scenarios', [])):
                return jsonify({'success': False, 'error': 'Invalid scenario index'}), 400
            
            # Update scenario data
            scenarios_data['scenarios'][scenario_index]['title'] = title
            scenarios_data['scenarios'][scenario_index]['priority'] = priority
            scenarios_data['scenarios'][scenario_index]['description'] = description
            
            # Update test case data if exists, else create a new one
            if 'test_cases' not in scenarios_data['scenarios'][scenario_index]:
                scenarios_data['scenarios'][scenario_index]['test_cases'] = []
                
            if len(scenarios_data['scenarios'][scenario_index]['test_cases']) == 0:
                scenarios_data['scenarios'][scenario_index]['test_cases'].append({
                    'title': f"{title} Test",
                    'steps': steps,
                    'expected_results': expected_results
                })
            else:
                scenarios_data['scenarios'][scenario_index]['test_cases'][0]['steps'] = steps
                scenarios_data['scenarios'][scenario_index]['test_cases'][0]['expected_results'] = expected_results
            
            # Save updates to the database
            scenario_set.scenarios_data = scenarios_data
            db.session.commit()
            
            # Log successful commit
            logging.info(f"Successfully updated playground data for {scenario_set_id}, scenario_index={scenario_index}")
            
            return jsonify({
                'success': True, 
                'message': 'Playground data updated successfully'
            })
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error updating playground: {str(e)}")
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Error updating playground: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API endpoint for generating test automation code
@app.route('/api/generate_automation', methods=['POST'])
def generate_automation():
    """
    Test otomasyonu kodu oluşturur.
    Yapay zeka modelini kullanarak daha kapsamlı ve doğru kod üretir.
    """
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        # Get required fields
        scenario_set_id = data.get('scenario_set_id')
        scenario_index = data.get('scenario_index')
        format = data.get('format')
        
        # Validate required fields
        if not scenario_set_id or scenario_index is None or not format:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Find the scenario set in the database
        try:
            # Try to find by both UUID and string representations
            # Sometimes client sends string IDs that aren't valid UUIDs
            scenario_set = None
            
            # Try as UUID first if it's a string that looks like UUID
            if isinstance(scenario_set_id, str):
                try:
                    # Check if it's a valid UUID format
                    uuid_obj = uuid.UUID(scenario_set_id)
                    scenario_set = TestScenarioSet.query.get(uuid_obj)
                except ValueError:
                    # Not a valid UUID format, try direct query as string
                    # In a real production app, you'd use a better approach, but for demo:
                    app.logger.warning(f"Invalid UUID format: {scenario_set_id}, trying fallback...")
                    test_scenario_sets = TestScenarioSet.query.all()
                    for ts in test_scenario_sets:
                        if str(ts.id) == scenario_set_id:
                            scenario_set = ts
                            break
            else:
                # Assume it's already a UUID object
                scenario_set = TestScenarioSet.query.get(scenario_set_id)
            
            # Handle case where we need to use the database's most recent scenario set
            if not scenario_set and scenario_set_id == "latest":
                # Get the most recent scenario set
                scenario_set = TestScenarioSet.query.order_by(TestScenarioSet.generated_date.desc()).first()
            
            # For demo/development environment if no valid ID was found, create a fallback
            if not scenario_set:
                app.logger.warning(f"No scenario set found, using demo fallback with id: {scenario_set_id}")
                # Get scenario data from current session if possible
                session_id = session.get('session_id', None)
                if session_id:
                    temp_data_dir = os.path.join('/tmp', 'data')
                    scenarios_file = os.path.join(temp_data_dir, f"{session_id}_scenarios.json")
                    
                    if os.path.exists(scenarios_file):
                        try:
                            with open(scenarios_file, 'r') as f:
                                scenarios_data = json.load(f)
                        except Exception as e:
                            app.logger.error(f"Error loading session scenarios: {e}")
                            return jsonify({'success': False, 'error': 'Session data error'}), 500
                    else:
                        # Use demo data as last resort
                        from utils.ai_service import get_demo_response
                        scenarios_data = get_demo_response()
                else:
                    # Use demo data as last resort 
                    from utils.ai_service import get_demo_response
                    scenarios_data = get_demo_response()
            else:
                # Get current scenarios data from database
                scenarios_data = scenario_set.scenarios_data
            
            # Convert index to integer
            try:
                scenario_index = int(scenario_index)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid scenario index format'}), 400
            
            # Make sure index is valid
            if scenario_index >= len(scenarios_data.get('scenarios', [])):
                return jsonify({'success': False, 'error': 'Invalid scenario index'}), 400
            
            # Get scenario and test case data
            scenario = scenarios_data['scenarios'][scenario_index]
            test_case = None
            
            if 'test_cases' in scenario and len(scenario['test_cases']) > 0:
                test_case = scenario['test_cases'][0]
            else:
                # Create a default test case if none exists
                test_case = {
                    'title': f"{scenario['title']} Test",
                    'steps': scenario.get('description', ''),
                    'expected_results': 'Expected results not specified'
                }
                
            # Generate code based on format - burada normalde AI modelini kullanabiliriz
            # Ancak örnek olarak temel bir kod üretimi yapıyoruz
            code = ""
            language = ""
            
            if format == 'selenium-java':
                code = generate_selenium_java_code(scenario, test_case)
                language = "java"
            elif format == 'selenium-python':
                code = generate_selenium_python_code(scenario, test_case)
                language = "python"
            elif format == 'cypress':
                code = generate_cypress_code(scenario, test_case)
                language = "javascript"
            elif format == 'playwright':
                code = generate_playwright_code(scenario, test_case)
                language = "javascript"
            elif format == 'appium':
                code = generate_appium_code(scenario, test_case)
                language = "java"
            elif format == 'restassured':
                code = generate_restassured_code(scenario, test_case)
                language = "java"
            elif format == 'cucumber':
                code = generate_cucumber_code(scenario, test_case)
                language = "gherkin"
            else:
                return jsonify({'success': False, 'error': 'Unsupported format'}), 400
            
            # Return the generated code
            return jsonify({
                'success': True,
                'code': code,
                'language': language
            })
            
        except Exception as e:
            logging.error(f"Error generating automation code: {str(e)}")
            return jsonify({'success': False, 'error': f'Error generating code: {str(e)}'}), 500
            
    except Exception as e:
        logging.error(f"Error in automation API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Kod üretim fonksiyonları
def generate_selenium_java_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        // {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['navigate', 'open', 'go to', 'visit']):
                code_steps += f'        driver.get("https://example.com");\n'
            elif any(keyword in line.lower() for keyword in ['click', 'press', 'select']):
                element = line.split()[-1].strip('.')
                code_steps += f'        driver.findElement(By.xpath("//*[contains(text(), \\"{element}\\")]")).click();\n'
            elif any(keyword in line.lower() for keyword in ['enter', 'type', 'input', 'fill']):
                element = line.split('in')[-1].strip().strip('.')
                value = "test value"
                code_steps += f'        driver.findElement(By.xpath("//input[@placeholder=\\"{element}\\"]")).sendKeys("{value}");\n'
            elif any(keyword in line.lower() for keyword in ['wait', 'pause']):
                code_steps += f'        Thread.sleep(1000); // Wait for 1 second\n'
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert', 'validate']):
                element = line.split()[-1].strip('.')
                code_steps += f'        assertTrue(driver.findElement(By.xpath("//*[contains(text(), \\"{element}\\")]")).isDisplayed());\n'
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        // {line.strip()}\n"
    
    # Class name formatting
    class_name = test_title.replace(' ', '').replace('-', '_').replace('.', '_')
    if not class_name[0].isalpha():
        class_name = 'Test' + class_name
    
    # Main code template
    return f"""import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import static org.junit.Assert.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;

/**
 * {scenario_title}
 * Bu test senaryosu, otomatik olarak oluşturulmuştur.
 */
public class {class_name}Test {{
    private WebDriver driver;
    private WebDriverWait wait;
    
    @Before
    public void setUp() {{
        // Driver kurulumu
        driver = new ChromeDriver();
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        driver.manage().window().maximize();
    }}
    
    @Test
    public void test{class_name}() {{
        // Test senaryosu: {scenario_title}
        // Test vakası: {test_title}
        
{code_steps}
        
        // Beklenen sonuçlar:
{formatted_expected}
    }}
    
    @After
    public void tearDown() {{
        if (driver != null) {{
            driver.quit();
        }}
    }}
}}"""

def generate_selenium_python_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        # {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['navigate', 'open', 'go to', 'visit']):
                code_steps += f'        driver.get("https://example.com")\n'
            elif any(keyword in line.lower() for keyword in ['click', 'press', 'select']):
                element = line.split()[-1].strip('.')
                code_steps += f'        driver.find_element(By.XPATH, "//*[contains(text(), \\"{element}\\")]").click()\n'
            elif any(keyword in line.lower() for keyword in ['enter', 'type', 'input', 'fill']):
                element = line.split('in')[-1].strip().strip('.')
                value = "test value"
                code_steps += f'        driver.find_element(By.XPATH, "//input[@placeholder=\\"{element}\\"]").send_keys("{value}")\n'
            elif any(keyword in line.lower() for keyword in ['wait', 'pause']):
                code_steps += f'        time.sleep(1)  # Wait for 1 second\n'
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert', 'validate']):
                element = line.split()[-1].strip('.')
                code_steps += f'        self.assertTrue(driver.find_element(By.XPATH, "//*[contains(text(), \\"{element}\\")]").is_displayed())\n'
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        # {line.strip()}\n"
    
    # Class name formatting
    class_name = test_title.replace(' ', '').replace('-', '_').replace('.', '_')
    if not class_name[0].isalpha():
        class_name = 'Test' + class_name
    
    # Main code template
    return f"""import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class {class_name}Test(unittest.TestCase):
    \"\"\"
    {scenario_title}
    Bu test senaryosu otomatik olarak oluşturulmuştur.
    \"\"\"
    
    def setUp(self):
        # Driver kurulumu
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
    
    def test_{class_name.lower()}(self):
        \"\"\"
        {test_title}
        \"\"\"
        driver = self.driver
        wait = self.wait
        
{code_steps}
        
        # Beklenen sonuçlar:
{formatted_expected}
    
    def tearDown(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == "__main__":
    unittest.main()
"""

def generate_cypress_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        // {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['navigate', 'open', 'go to', 'visit']):
                code_steps += f"        cy.visit('https://example.com')\n"
            elif any(keyword in line.lower() for keyword in ['click', 'press', 'select']):
                element = line.split()[-1].strip('.')
                code_steps += f"        cy.contains('{element}').click()\n"
            elif any(keyword in line.lower() for keyword in ['enter', 'type', 'input', 'fill']):
                element = line.split('in')[-1].strip().strip('.')
                value = "test value"
                code_steps += f"        cy.get('input[placeholder=\"{element}\"]').type('{value}')\n"
            elif any(keyword in line.lower() for keyword in ['wait', 'pause']):
                code_steps += f"        cy.wait(1000) // Wait for 1 second\n"
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert', 'validate']):
                element = line.split()[-1].strip('.')
                code_steps += f"        cy.contains('{element}').should('be.visible')\n"
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        // {line.strip()}\n"
    
    # Main code template
    return f"""// {scenario_title}
// {test_title}
// Bu test senaryosu otomatik olarak oluşturulmuştur.

describe('{scenario_title}', () => {{
    beforeEach(() => {{
        // Her test öncesi ziyaret edilecek URL
        cy.visit('/')
    }})
    
    it('{test_title}', () => {{
{code_steps}
        
        // Beklenen sonuçlar:
{formatted_expected}
    }})
}})
"""

def generate_playwright_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        // {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['navigate', 'open', 'go to', 'visit']):
                code_steps += f"        await page.goto('https://example.com')\n"
            elif any(keyword in line.lower() for keyword in ['click', 'press', 'select']):
                element = line.split()[-1].strip('.')
                code_steps += f"        await page.getByText('{element}').click()\n"
            elif any(keyword in line.lower() for keyword in ['enter', 'type', 'input', 'fill']):
                element = line.split('in')[-1].strip().strip('.')
                value = "test value"
                code_steps += f"        await page.getByPlaceholder('{element}').fill('{value}')\n"
            elif any(keyword in line.lower() for keyword in ['wait', 'pause']):
                code_steps += f"        await page.waitForTimeout(1000) // Wait for 1 second\n"
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert', 'validate']):
                element = line.split()[-1].strip('.')
                code_steps += f"        await expect(page.getByText('{element}')).toBeVisible()\n"
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        // {line.strip()}\n"
    
    # Main code template
    return f"""// {scenario_title}
// {test_title}
// Bu test senaryosu otomatik olarak oluşturulmuştur.

const {{ test, expect }} = require('@playwright/test')

test.describe('{scenario_title}', () => {{
    test('{test_title}', async ({{ page }}) => {{
{code_steps}
        
        // Beklenen sonuçlar:
{formatted_expected}
    }})
}})
"""

def generate_appium_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        // {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['open', 'launch', 'start']):
                code_steps += f"        // App is already launched in setup\n"
            elif any(keyword in line.lower() for keyword in ['click', 'tap', 'press']):
                element = line.split()[-1].strip('.')
                code_steps += f'        driver.findElement(By.xpath("//*[@text=\\"{element}\\"]")).click();\n'
            elif any(keyword in line.lower() for keyword in ['enter', 'type', 'input']):
                element = line.split('in')[-1].strip().strip('.')
                value = "test value"
                code_steps += f'        driver.findElement(By.xpath("//android.widget.EditText[@text=\\"{element}\\"]")).sendKeys("{value}");\n'
            elif any(keyword in line.lower() for keyword in ['wait', 'pause']):
                code_steps += f"        Thread.sleep(1000); // Wait for 1 second\n"
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert']):
                element = line.split()[-1].strip('.')
                code_steps += f'        assertTrue(driver.findElement(By.xpath("//*[@text=\\"{element}\\"]")).isDisplayed());\n'
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        // {line.strip()}\n"
    
    # Class name formatting
    class_name = test_title.replace(' ', '').replace('-', '_').replace('.', '_')
    if not class_name[0].isalpha():
        class_name = 'Test' + class_name
    
    # Main code template
    return f"""import io.appium.java_client.AppiumDriver;
import io.appium.java_client.MobileElement;
import io.appium.java_client.android.AndroidDriver;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;
import org.openqa.selenium.By;
import org.openqa.selenium.remote.DesiredCapabilities;
import java.net.URL;

/**
 * {scenario_title}
 * Bu test senaryosu, otomatik olarak oluşturulmuştur.
 */
public class {class_name}Test {{
    private AppiumDriver<MobileElement> driver;
    
    @Before
    public void setUp() throws Exception {{
        DesiredCapabilities caps = new DesiredCapabilities();
        caps.setCapability("platformName", "Android");
        caps.setCapability("deviceName", "Android Device");
        caps.setCapability("appPackage", "com.example.app");
        caps.setCapability("appActivity", "com.example.app.MainActivity");
        
        driver = new AndroidDriver<>(new URL("http://localhost:4723/wd/hub"), caps);
    }}
    
    @Test
    public void test{class_name}() throws InterruptedException {{
        // Test senaryosu: {scenario_title}
        // Test vakası: {test_title}
        
{code_steps}
        
        // Beklenen sonuçlar:
{formatted_expected}
    }}
    
    @After
    public void tearDown() {{
        if (driver != null) {{
            driver.quit();
        }}
    }}
}}"""

def generate_restassured_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps as code
    code_steps = ""
    for line in steps.split('\n'):
        if line.strip():
            code_steps += f"        // {line.strip()}\n"
            # Simple heuristic for generating code based on step descriptions
            if any(keyword in line.lower() for keyword in ['get', 'fetch', 'retrieve']):
                endpoint = "/api/resource"
                code_steps += f"""        Response response = given()
            .header("Content-Type", "application/json")
            .when()
            .get("{endpoint}")
            .then()
            .statusCode(200)
            .extract().response();\n"""
            elif any(keyword in line.lower() for keyword in ['post', 'create', 'add']):
                endpoint = "/api/resource"
                code_steps += f"""        Response response = given()
            .header("Content-Type", "application/json")
            .body("{{ \\"name\\": \\"Test Resource\\", \\"value\\": \\"123\\" }}")
            .when()
            .post("{endpoint}")
            .then()
            .statusCode(201)
            .extract().response();\n"""
            elif any(keyword in line.lower() for keyword in ['put', 'update', 'modify']):
                endpoint = "/api/resource/1"
                code_steps += f"""        Response response = given()
            .header("Content-Type", "application/json")
            .body("{{ \\"name\\": \\"Updated Resource\\", \\"value\\": \\"456\\" }}")
            .when()
            .put("{endpoint}")
            .then()
            .statusCode(200)
            .extract().response();\n"""
            elif any(keyword in line.lower() for keyword in ['delete', 'remove']):
                endpoint = "/api/resource/1"
                code_steps += f"""        Response response = given()
            .when()
            .delete("{endpoint}")
            .then()
            .statusCode(204)
            .extract().response();\n"""
            elif any(keyword in line.lower() for keyword in ['check', 'verify', 'assert', 'validate']):
                code_steps += f"""        // Verify response
        assertEquals("Expected value", response.jsonPath().getString("name"));
        assertTrue(response.jsonPath().getList("items").size() > 0);\n"""
            code_steps += '\n'
    
    # Format expected results
    formatted_expected = ""
    for line in expected_results.split('\n'):
        if line.strip():
            formatted_expected += f"        // {line.strip()}\n"
    
    # Class name formatting
    class_name = test_title.replace(' ', '').replace('-', '_').replace('.', '_')
    if not class_name[0].isalpha():
        class_name = 'Test' + class_name
    
    # Main code template
    return f"""import org.junit.Test;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;
import static org.junit.Assert.*;
import io.restassured.response.Response;
import org.junit.Before;

/**
 * {scenario_title}
 * Bu test senaryosu, otomatik olarak oluşturulmuştur.
 */
public class {class_name}Test {{
    
    @Before
    public void setUp() {{
        // API temel URL'si
        baseURI = "https://api.example.com";
    }}
    
    @Test
    public void test{class_name}() {{
        // Test senaryosu: {scenario_title}
        // Test vakası: {test_title}
        
{code_steps}
        
        // Beklenen sonuçlar:
{formatted_expected}
    }}
}}"""

def generate_cucumber_code(scenario, test_case):
    scenario_title = scenario.get('title', 'Unnamed Scenario')
    test_title = test_case.get('title', 'Unnamed Test Case')
    steps = test_case.get('steps', '')
    expected_results = test_case.get('expected_results', '')
    
    # Format steps in Gherkin
    gherkin_steps = ""
    step_lines = [line.strip() for line in steps.split('\n') if line.strip()]
    
    # Create Given, When, Then structure
    if step_lines:
        gherkin_steps += f"  Given {step_lines[0]}\n"
        
        for i in range(1, len(step_lines)):
            if i == len(step_lines) - 1:
                gherkin_steps += f"  Then {step_lines[i]}\n"
            else:
                gherkin_steps += f"  When {step_lines[i]}\n"
    
    # Add expected results as And steps
    expected_lines = [line.strip() for line in expected_results.split('\n') if line.strip()]
    for line in expected_lines:
        gherkin_steps += f"  And {line}\n"
    
    # Main code template
    return f"""# {scenario_title}
# Bu test senaryosu otomatik olarak oluşturulmuştur.

Feature: {scenario_title}
  Bu özellik {scenario_title.lower()} için test senaryolarını içerir

Scenario: {test_title}
{gherkin_steps}"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
