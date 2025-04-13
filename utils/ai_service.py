import os
import json
import logging
import requests
from utils.openai_service import generate_with_openai
from utils.ollama_service import generate_with_ollama
from utils.deepseek_service import generate_with_deepseek

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def is_ollama_available():
    """
    Ollama'nın kullanılabilir olup olmadığını kontrol eder
    
    Returns:
        bool: Ollama API'si erişilebilirse True, değilse False
    """
    # OLLAMA_SKIP_CHECK çevre değişkeni ayarlanmışsa, kullanılabilirlik kontrolünü atla
    if os.environ.get("OLLAMA_SKIP_CHECK", "false").lower() == "true":
        logger.info("OLLAMA_SKIP_CHECK true olarak ayarlandığı için Ollama bağlantı kontrolü atlanıyor")
        return True
        
    # Ollama API endpoint'ini al
    api_endpoint = os.environ.get("OLLAMA_API_ENDPOINT", "http://localhost:11434")
    
    try:
        # Ollama sunucusuna basit bir ping isteği gönder
        response = requests.get(api_endpoint, timeout=2)
        # 2xx, 3xx durum kodları başarılı kabul edilir
        return response.status_code < 400
    except requests.exceptions.RequestException:
        return False

def get_demo_response():
    """
    Returns a canned demo response for when real AI services aren't available
    
    Returns:
        dict: Sample test scenarios in the correct format
    """
    demo_response = {
        "summary": "Bu belge, bir web tabanlı uygulama için test senaryoları ve kullanım durumlarıdır. Demo modunda gösterilen örnek bir yanıttır.",
        "scenarios": [
            {
                "title": "Kullanıcı Kaydı",
                "description": "Yeni kullanıcıların sisteme kaydolmasını test eder.",
                "test_cases": [
                    {
                        "title": "Geçerli Kullanıcı Kaydı",
                        "steps": "1. Kayıt sayfasını aç\n2. Geçerli bir e-posta adresi gir\n3. Geçerli ve güçlü bir şifre gir\n4. Kayıt düğmesine tıkla",
                        "expected_results": "Kullanıcı başarıyla kaydedilmeli ve gösterge paneline yönlendirilmelidir."
                    },
                    {
                        "title": "Geçersiz E-posta ile Kayıt",
                        "steps": "1. Kayıt sayfasını aç\n2. Geçersiz bir e-posta biçimi gir\n3. Geçerli bir şifre gir\n4. Kayıt düğmesine tıkla",
                        "expected_results": "Sistem geçersiz e-posta hatası göstermeli ve kullanıcı kaydedilmemelidir."
                    }
                ]
            },
            {
                "title": "Belge İşleme",
                "description": "Farklı belgelerin sistem tarafından işlenmesini test eder.",
                "test_cases": [
                    {
                        "title": "PDF Belge Yükleme",
                        "steps": "1. Belge yükleme sayfasını aç\n2. Bir PDF dosyası seç\n3. Yükle düğmesine tıkla",
                        "expected_results": "PDF belge başarıyla yüklenmeli ve işlenmelidir."
                    },
                    {
                        "title": "Büyük Boyutlu Belge Yükleme",
                        "steps": "1. Belge yükleme sayfasını aç\n2. 16MB üzerinde bir belge seç\n3. Yükle düğmesine tıkla",
                        "expected_results": "Sistem 'Dosya çok büyük' hatası göstermelidir."
                    }
                ]
            },
            {
                "title": "Test Senaryosu Oluşturma",
                "description": "AI kullanarak test senaryoları oluşturma sürecini test eder.",
                "test_cases": [
                    {
                        "title": "Ollama ile Test Senaryosu Oluşturma",
                        "steps": "1. Ana sayfada bir belge yükle\n2. Ollama'yı seç\n3. 'Test Senaryoları Oluştur' düğmesine tıkla",
                        "expected_results": "Sistem belgeyi işlemeli ve Ollama API'si ile test senaryoları oluşturmalıdır."
                    },
                    {
                        "title": "OpenAI ile Test Senaryosu Oluşturma",
                        "steps": "1. Ana sayfada bir belge yükle\n2. OpenAI'yi seç\n3. 'Test Senaryoları Oluştur' düğmesine tıkla",
                        "expected_results": "Sistem belgeyi işlemeli ve OpenAI API'si ile test senaryoları oluşturmalıdır."
                    }
                ]
            }
        ]
    }
    
    return demo_response

def generate_test_scenarios(document_text, ai_provider="openai", document_structure=None, enhanced_context=True, azure_model=None):
    """
    Generate test scenarios and use cases from document text using the specified AI provider
    
    Args:
        document_text (str): The extracted text from the document
        ai_provider (str): The AI provider to use (ollama, openai, deepseek, azure)
        document_structure (dict, optional): Document structure and metadata from document_analyzer
        enhanced_context (bool): Whether to provide enhanced context about document structure to AI
        
    Returns:
        dict: Structured test scenarios and use cases
    """
    logger.info(f"Generating test scenarios using {ai_provider}")
    
    # Gelişmiş AI işlemciyi kullan (eğer mevcutsa)
    try:
        from utils.advanced_ai_processor import advanced_processor
        logger.info("Gelişmiş AI işlemci kullanılıyor")
        
        # İşleme seçeneklerini ayarla
        options = {
            "preserve_all_content": True,  # Tüm içeriği koru (müşteri talebi)
            "detailed_processing": True,  # Detaylı işleme (görsel, tablo)
            "use_multi_model": True,  # Çoklu model kullan (görsel=4o, sınıflandırma=o3-mini, teknik=o1)
            "complete_processing": True,  # Tüm belgeyi işle - kesinlikle kesme yapma 
            "high_verbosity": True,  # Ayrıntılı loglama
            "rich_content_focus": True  # Zengin içerik odaklı işleme - görsel analiz ve tablo analiz
        }
        
        # Müşteri özel bir model seçtiyse kullan
        preferred_model = azure_model if ai_provider == "azure" else None
        
        # Doküman yapısı yoksa boş sözlük kullan
        doc_structure = document_structure if document_structure else {}
        
        # Daha fazla log ekle
        logger.info(f"Belge işleme başlatılıyor. Boyut: {len(document_text)} karakter, "
                   f"AI sağlayıcı: {ai_provider}, Model: {preferred_model or 'otomatik seçim'}")
                   
        # Belge içeriği hakkında ek bilgi
        logger.info(f"Doküman boyutu: {len(document_text)} karakter")
        
        # Belge yapısı hakkında detaylı log ekle
        if "images" in doc_structure:
            logger.info(f"Dokümanda {len(doc_structure['images'])} görsel mevcut")
            # İlk 3 görseli logla
            for i, img in enumerate(doc_structure['images'][:3]):
                if isinstance(img, dict) and "description" in img:
                    logger.info(f"Görsel {i+1}: {img['description'][:100]}...")
        if "tables" in doc_structure:
            logger.info(f"Dokümanda {len(doc_structure['tables'])} tablo mevcut")
            # İlk 3 tabloyu logla
            for i, tbl in enumerate(doc_structure['tables'][:3]):
                if isinstance(tbl, dict) and "caption" in tbl:
                    logger.info(f"Tablo {i+1}: {tbl['caption'][:100]}...")
        
        # Belgeyi gelişmiş işlemci ile işle
        result = advanced_processor.process_document(
            document_text=document_text,
            document_structure=doc_structure,
            preferred_model=preferred_model,
            options=options
        )
        
        if isinstance(result, dict) and "error" not in result:
            logger.info("Gelişmiş AI işlemci başarıyla sonuç üretti")
            return result
        else:
            logger.warning(f"Gelişmiş AI işlemci hatası, standart işlemeye dönülüyor: {result.get('error', 'Bilinmeyen hata')}")
            # Hata durumunda standart işlemeye devam et
    except ImportError:
        logger.info("Gelişmiş AI işlemci mevcut değil, standart işleme kullanılıyor")
    except Exception as e:
        logger.error(f"Gelişmiş AI işlemci hatası: {str(e)}")
    
    # Standart işleme - geriye dönük uyumluluk için
    
    # Check if we should use NeuraAgent Basic (if enabled and available)
    try:
        # Önce NeuraAgent eklentisini yükle (eksik metodları ekler)
        import utils.neuraagent_ext
        # Şimdi NeuraAgent Basic sınıfını içe aktar
        from utils.neuraagent import NeuraAgentBasic
        neuraagent_enabled = os.environ.get("NEURAAGENT_BASIC_ENABLED", "true").lower() == "true"
        if neuraagent_enabled and document_structure:
            logger.info("Using NeuraAgent Basic for enhanced document processing")
            try:
                # Create NeuraAgent instance
                agent = NeuraAgentBasic()
                
                # Process document with NeuraAgent - detailed processing with full content
                # Müşteri talebi: Tüm içerikleri sayfa sayfa, tablo tablo, resim resim analiz et
                if hasattr(agent, 'process_document_for_scenarios'):
                    logger.info("Müşteri talebi: Tüm içerik ayrıntılı işleniyor (sayfa sayfa, görsel görsel)...")
                    optimized_content = agent.process_document_for_scenarios(
                        document_text=document_text,
                        document_structure=document_structure,
                        ai_provider=ai_provider,
                        detailed_processing=True,  # Ayrıntılı işleme modu
                        preserve_all_content=True  # Tüm içeriği koru
                    )
                else:
                    # API değişmişse geriye dönük uyumlu çalış
                    logger.warning("NeuraAgent API istenilen detay seviyesini desteklemiyor, temel işleme kullanılıyor")
                    optimized_content = agent.optimize_for_ai(
                        document_text=document_text,
                        ai_provider=ai_provider
                    )
                
                # Use optimized document structure if available
                if optimized_content and isinstance(optimized_content, dict):
                    logger.info("Using enhanced document analysis with rich content extraction")
                    if "optimized_text" in optimized_content:
                        document_text = optimized_content["optimized_text"]
                    if "enhanced_structure" in optimized_content:
                        document_structure = optimized_content["enhanced_structure"]
            except Exception as e:
                logger.error(f"Error using NeuraAgent Basic: {e}")
                # Continue with original document if NeuraAgent fails
    except ImportError:
        logger.warning("NeuraAgent Basic module not available")
    
    # ÖNEMLİ DEĞİŞİKLİK: Kullanıcı talebi üzerine belge içeriğini kısaltma işlemi devre dışı bırakıldı
    # Müşteri talebi: Tüm içerikleri eksiksiz analiz et, hiçbir veriyi kaybetme
    # truncated_text = truncate_document(document_text, ai_provider)
    
    # Create document context with enhanced information (if available)
    context = {
        "text": document_text,  # Tam belge metni kullan, kısaltma yapma
        "preserve_all": True    # Tüm içeriği koru
    }
    
    # Azure model bilgisini context'e ekle (eğer varsa)
    if azure_model:
        context["azure_model"] = azure_model
    
    if document_structure and enhanced_context:
        logger.info("Adding document structure context to AI prompt")
        # Add document structure to context
        context["structure"] = document_structure
        
        # Add metadata about images, tables, etc.
        context["has_rich_content"] = True
        
        # Add structured content information
        if 'sections' in document_structure:
            context["sections"] = document_structure['sections']
        if 'headings' in document_structure:
            context["headings"] = document_structure['headings']
        
        # Add specific counts and content information for rich elements
        if 'image_count' in document_structure:
            context["image_count"] = document_structure['image_count']
            # Include image descriptions if available
            if 'images' in document_structure:
                context["images"] = document_structure['images']
        
        if 'table_count' in document_structure:
            context["table_count"] = document_structure['table_count']
            # Include table summaries if available
            if 'tables' in document_structure:
                context["tables"] = document_structure['tables']
        
        # Include chart information if available
        if 'charts' in document_structure:
            context["charts"] = document_structure['charts']
            context["chart_count"] = len(document_structure['charts'])
        
        # Include diagram information if available
        if 'diagrams' in document_structure:
            context["diagrams"] = document_structure['diagrams']
            context["diagram_count"] = len(document_structure['diagrams'])
            
        # Add semantic structure summary if available
        if 'semantic_structure' in document_structure:
            context["semantic_structure"] = document_structure['semantic_structure']
        
        # Add document classification information if available
        if 'document_type' in document_structure:
            context["document_type"] = document_structure['document_type']
        if 'document_purpose' in document_structure:
            context["document_purpose"] = document_structure['document_purpose']
    
    try:
        # Check for demo mode
        demo_mode = os.environ.get("DEMO_MODE", "false").lower() == "true"
        
        # First try the selected provider
        try:
            result = None
            
            if ai_provider == "openai":
                result = generate_with_openai(context)
            elif ai_provider == "ollama":
                # In demo mode, use a canned response for Ollama
                if demo_mode:
                    logger.info("Using demo mode for Ollama (canned response)")
                    result = get_demo_response()
                else:
                    result = generate_with_ollama(context)
            elif ai_provider == "deepseek":
                result = generate_with_deepseek(context)
            elif ai_provider == "azure":
                # Check for Azure OpenAI integration
                try:
                    from utils.azure_service import generate_with_azure
                    # api model information ekleniyor
                    # Azure model seçimi varsa contex'e ekleyelim
                    if 'azure_model' in context:
                        logger.info(f"Azure model selected: {context['azure_model']}")
                        
                        # Get api model information from constants if available
                        from app import AI_MODELS
                        if 'azure_model' in context and context['azure_model'] in AI_MODELS:
                            api_model_info = AI_MODELS[context['azure_model']]
                            logger.info(f"Using api AI model configuration: {context['azure_model']}")
                            
                            # Add api model info to context
                            context['api_model_info'] = api_model_info
                            
                    result = generate_with_azure(context)
                except ImportError as e:
                    logger.error(f"Azure service module not found: {str(e)}")
                    raise ValueError("Azure OpenAI service not configured")
            else:
                raise ValueError(f"Unsupported AI provider: {ai_provider}")
                
            # Enhance the result with document context if available
            if result and document_structure and enhanced_context:
                result = enhance_scenarios_with_document_context(result, document_structure)
                
            return result
            
        except Exception as provider_error:
            # If selected provider is Ollama (default) and it fails, try OpenAI as fallback if available
            if ai_provider == "ollama":
                # If in demo mode, return demo data
                if demo_mode:
                    logger.info("Using demo mode (fallback) for Ollama")
                    return get_demo_response()
                    
                # Otherwise try OpenAI fallback
                try:
                    logger.warning(f"Ollama provider failed: {str(provider_error)}. Trying OpenAI as fallback...")
                    result = generate_with_openai(context)
                    
                    # Enhance the result with document context if available
                    if result and document_structure and enhanced_context:
                        result = enhance_scenarios_with_document_context(result, document_structure)
                    
                    return result
                except Exception as openai_error:
                    logger.error(f"OpenAI fallback also failed: {str(openai_error)}")
                    # In case of Replit environment where neither might be available, suggest demo mode
                    new_error = f"{str(provider_error)}\n\nİpucu: Replit ortamında test etmek için DEMO_MODE=true ve OLLAMA_SKIP_CHECK=true ortam değişkenlerini ayarlayın."
                    raise ConnectionError(new_error)
            else:
                # For other providers, just raise the original error
                raise
    except Exception as e:
        logger.error(f"Error generating test scenarios: {str(e)}")
        raise
        
def enhance_scenarios_with_document_context(scenarios_data, document_structure):
    """
    Enhance scenario data with additional context from document structure
    
    Args:
        scenarios_data (dict): The formatted scenario data
        document_structure (dict): Document structure and metadata
        
    Returns:
        dict: Enhanced scenario data
    """
    try:
        if not isinstance(scenarios_data, dict):
            logger.warning("Scenarios data is not a dictionary, cannot enhance")
            return scenarios_data
            
        # Ensure the proper structure exists
        if 'scenarios' not in scenarios_data:
            logger.warning("Scenarios data does not contain 'scenarios' key, cannot enhance")
            return scenarios_data
            
        # Add document metadata
        if 'file_type' in document_structure:
            scenarios_data['document_type'] = document_structure['file_type']
            
        if 'page_count' in document_structure:
            scenarios_data['page_count'] = document_structure['page_count']
            
        # Add enhanced document information if available
        if 'document_purpose' in document_structure:
            scenarios_data['document_purpose'] = document_structure['document_purpose']
            
        if 'document_category' in document_structure:
            scenarios_data['document_category'] = document_structure['document_category']
            
        # Add rich content metadata
        # Add images metadata if available
        if 'image_count' in document_structure and document_structure['image_count'] > 0:
            scenarios_data['contains_images'] = True
            scenarios_data['image_count'] = document_structure['image_count']
            
            # Add detailed image analyses if available
            if 'processed_images' in document_structure and document_structure['processed_images']:
                processed_imgs = document_structure['processed_images']
                scenarios_data['processed_images'] = processed_imgs
                logger.info(f"Senaryolara {len(processed_imgs)} işlenmiş görsel ekleniyor")
                
                # Zenginleştirilmiş görsel analizleri ekle
                images_summary = []
                for img in processed_imgs:
                    if isinstance(img, dict):
                        img_type = img.get('image_type', 'Belirsiz')
                        test_rel = img.get('test_relevance', 'Orta')
                        img_desc = img.get('description', '')
                        summary = f"Görsel {img.get('index', '')}: {img_type} (Test ilişkisi: {test_rel})"
                        
                        # Görsel içeriğine göre tanımlama ekle
                        if img.get('ui_elements'):
                            summary += f" - {len(img.get('ui_elements', []))} UI öğesi içeriyor"
                        if img.get('text_content'):
                            summary += " - Metin içeriyor"
                        if img.get('detected_tables'):
                            summary += f" - {len(img.get('detected_tables', []))} tablo içeriyor"
                        
                        images_summary.append(summary)
                
                if images_summary:
                    scenarios_data['images_summary'] = images_summary
                
                # Görsellerden çıkarılan test senaryolarını mevcut senaryolara doğrudan dahil et
                if 'scenarios' in scenarios_data and isinstance(scenarios_data['scenarios'], list):
                    for img in processed_imgs:
                        if isinstance(img, dict) and img.get('test_scenarios'):
                            # Görsel kaynaklı senaryoları ekle
                            img_scenarios = img.get('test_scenarios', [])
                            if isinstance(img_scenarios, list) and img_scenarios:
                                for img_scenario in img_scenarios:
                                    if isinstance(img_scenario, dict) and 'title' in img_scenario:
                                        # Görsel kaynaklı olduğunu belirt
                                        img_scenario['source'] = 'image'
                                        img_scenario['image_description'] = img.get('description', 'Görsel içerik')
                                        
                                        # Eğer test case'leri yoksa, basit bir test case ekle
                                        if 'test_cases' not in img_scenario or not img_scenario['test_cases']:
                                            img_scenario['test_cases'] = [{
                                                'title': 'Görsel içerik doğrulama testi',
                                                'steps': '1. Görseli ekranda açın\n2. İçeriği inceleyerek doğrulayın',
                                                'expected_results': 'Görselin içeriği beklenen şekilde görüntülenmeli'
                                            }]
                                        
                                        # Senaryoyu ana senaryolara ekle
                                        scenarios_data['scenarios'].append(img_scenario)
            
            # Geleneksel yöntemle image açıklamaları (geriye uyumluluk için)
            elif 'images' in document_structure:
                image_descriptions = []
                for img in document_structure['images']:
                    if isinstance(img, dict):
                        desc = img.get('description', img.get('caption', f"Image on page {img.get('page', 'unknown')}"))
                        if 'analysis' in img:
                            desc += f" - {img['analysis']}"
                        image_descriptions.append(desc)
                    elif isinstance(img, str):
                        image_descriptions.append(img)
                
                if image_descriptions:
                    scenarios_data['image_descriptions'] = image_descriptions[:5]  # Limit to first 5 to avoid overwhelming
            
        # Add tables metadata if available
        if 'table_count' in document_structure and document_structure['table_count'] > 0:
            scenarios_data['contains_tables'] = True
            scenarios_data['table_count'] = document_structure['table_count']
            
            # Add table captions or summaries if available
            if 'tables' in document_structure:
                table_descriptions = []
                tables = document_structure['tables']
                
                for tbl in tables:
                    if isinstance(tbl, dict):
                        desc = tbl.get('caption', f"Table on page {tbl.get('page', 'unknown')}")
                        if 'summary' in tbl:
                            desc += f" - {tbl['summary']}"
                        table_descriptions.append(desc)
                    elif isinstance(tbl, str):
                        table_descriptions.append(tbl)
                
                if table_descriptions:
                    scenarios_data['table_descriptions'] = table_descriptions[:5]  # Limit to first 5
                
                # Tablolardan çıkarılan test senaryolarını doğrudan dahil et
                if 'scenarios' in scenarios_data and isinstance(scenarios_data['scenarios'], list):
                    for tbl in tables:
                        if isinstance(tbl, dict) and tbl.get('test_scenarios'):
                            # Tablo kaynaklı senaryoları ekle
                            tbl_scenarios = tbl.get('test_scenarios', [])
                            if isinstance(tbl_scenarios, list) and tbl_scenarios:
                                for tbl_scenario in tbl_scenarios:
                                    if isinstance(tbl_scenario, dict) and 'title' in tbl_scenario:
                                        # Tablo kaynaklı olduğunu belirt
                                        tbl_scenario['source'] = 'table'
                                        tbl_scenario['table_caption'] = tbl.get('caption', 'Tablo içerik')
                                        
                                        # Eğer test case'leri yoksa, temel bir test case ekle
                                        if 'test_cases' not in tbl_scenario or not tbl_scenario['test_cases']:
                                            tbl_scenario['test_cases'] = [{
                                                'title': 'Tablo içerik doğrulama testi',
                                                'steps': '1. Tabloyu ekranda görüntüleyin\n2. Tablo verilerini kontrol edin',
                                                'expected_results': 'Tablo doğru verileri içeriyor olmalı'
                                            }]
                                        
                                        # Ana senaryolara ekle
                                        scenarios_data['scenarios'].append(tbl_scenario)
        
        # Add chart metadata if available
        if 'charts' in document_structure and len(document_structure['charts']) > 0:
            scenarios_data['contains_charts'] = True
            scenarios_data['chart_count'] = len(document_structure['charts'])
            
            # Add chart descriptions
            chart_descriptions = []
            for chart in document_structure['charts']:
                if isinstance(chart, dict):
                    desc = chart.get('caption', f"{chart.get('chart_type', 'Unknown')} Chart")
                    if 'data_summary' in chart:
                        desc += f" - {chart['data_summary']}"
                    chart_descriptions.append(desc)
                elif isinstance(chart, str):
                    chart_descriptions.append(chart)
            
            if chart_descriptions:
                scenarios_data['chart_descriptions'] = chart_descriptions[:5]  # Limit to first 5
                
        # Add diagram metadata if available
        if 'diagrams' in document_structure and len(document_structure['diagrams']) > 0:
            scenarios_data['contains_diagrams'] = True
            scenarios_data['diagram_count'] = len(document_structure['diagrams'])
            
            # Add diagram descriptions
            diagram_descriptions = []
            for diagram in document_structure['diagrams']:
                if isinstance(diagram, dict):
                    desc = diagram.get('caption', f"{diagram.get('diagram_type', 'Unknown')} Diagram")
                    if 'description' in diagram:
                        desc += f" - {diagram['description']}"
                    diagram_descriptions.append(desc)
                elif isinstance(diagram, str):
                    diagram_descriptions.append(diagram)
            
            if diagram_descriptions:
                scenarios_data['diagram_descriptions'] = diagram_descriptions[:5]  # Limit to first 5
            
        # Check if we need to add rich content references to test cases
        has_rich_content = (
            document_structure.get('image_count', 0) > 0 or 
            document_structure.get('table_count', 0) > 0 or
            ('charts' in document_structure and len(document_structure['charts']) > 0) or
            ('diagrams' in document_structure and len(document_structure['diagrams']) > 0)
        )
        
        # If there's rich content, enhance test cases with references to it
        if has_rich_content:
            for scenario in scenarios_data['scenarios']:
                # Add rich content flag to scenarios with visual elements
                desc_lower = scenario.get('description', '').lower()
                if any(keyword in desc_lower for keyword in ['interface', 'görsel', 'ekran', 'tablo', 'görüntü', 'grafik', 'diyagram']):
                    scenario['may_involve_visual_elements'] = True
                    
                    # Add visual reference to relevant scenarios
                    visual_references = []
                    
                    # Add image references if they appear to be relevant
                    if 'image_descriptions' in scenarios_data and ('görüntü' in desc_lower or 'resim' in desc_lower):
                        visual_references.extend([f"Görsel: {img}" for img in scenarios_data['image_descriptions'][:2]])
                        
                    # Add table references if they appear to be relevant
                    if 'table_descriptions' in scenarios_data and 'tablo' in desc_lower:
                        visual_references.extend([f"Tablo: {tbl}" for tbl in scenarios_data['table_descriptions'][:2]])
                        
                    # Add chart references if they appear to be relevant
                    if 'chart_descriptions' in scenarios_data and ('grafik' in desc_lower or 'çizelge' in desc_lower):
                        visual_references.extend([f"Grafik: {chart}" for chart in scenarios_data['chart_descriptions'][:2]])
                        
                    # Add diagram references if they appear to be relevant
                    if 'diagram_descriptions' in scenarios_data and ('diyagram' in desc_lower or 'şema' in desc_lower):
                        visual_references.extend([f"Diyagram: {diagram}" for diagram in scenarios_data['diagram_descriptions'][:2]])
                    
                    if visual_references:
                        scenario['visual_references'] = visual_references
                
                # Add rich content references to test cases that might involve images/tables/charts/diagrams
                for test_case in scenario.get('test_cases', []):
                    steps = test_case.get('steps', '')
                    steps_lower = steps.lower()
                    
                    # Check for visual content references in the steps
                    if any(keyword in steps_lower for keyword in ['görüntü', 'resim', 'tablo', 'grafik', 'diyagram', 'şema', 'ekran', 'görsel']):
                        test_case['involves_rich_content'] = True
                        
                        # Add relevant content type tags
                        content_types = []
                        if any(keyword in steps_lower for keyword in ['görüntü', 'resim', 'fotoğraf']):
                            content_types.append('image')
                        if any(keyword in steps_lower for keyword in ['tablo', 'sıra', 'kolon', 'hücre']):
                            content_types.append('table')
                        if any(keyword in steps_lower for keyword in ['grafik', 'çizelge', 'çubuk', 'pasta']):
                            content_types.append('chart')
                        if any(keyword in steps_lower for keyword in ['diyagram', 'şema', 'akış']):
                            content_types.append('diagram')
                            
                        if content_types:
                            test_case['rich_content_types'] = content_types
                        
        # Add notes about AI processing for image/table content if appropriate
        if has_rich_content:
            rich_content_note = "Bu belge görsel içerik (resimler, tablolar, grafikler ve/veya diyagramlar) içermektedir. "
            rich_content_note += "Test senaryoları ve gereksinimleri oluştururken bu görsel içerikler dikkate alınmıştır."
            scenarios_data['rich_content_note'] = rich_content_note
            
        return scenarios_data
    except Exception as e:
        logger.error(f"Error enhancing scenarios with document context: {str(e)}")
        return scenarios_data

def truncate_document(document_text, ai_provider):
    """
    Müşteri isteğiyle %100 belgeden feragat etmeme politikası uygulanmaktadır.
    Belge hiçbir şekilde kırpılmayacaktır.
    
    Args:
        document_text (str): Belge metni (kırpılmayacak)
        ai_provider (str): AI sağlayıcı
        
    Returns:
        str: Belge metni (kırpılmamış haliyle)
    """
    # Dokümanı hiçbir şekilde kırpmıyoruz
    # Müşteri isteği üzerine %100 doküman işleme politikası uygulanmaktadır
    # Eğer belge uzunsa çoklu sorgu yapmak yerine tek sorguda tamamını gönderiyoruz
    
    # Yalnızca loglama amaçlı karakter sayısı kontrol ediliyor
    limits = {
        "openai": 15000,  # ~4000 tokens for GPT models
        "ollama": 10000,  # Depends on the model being used
        "deepseek": 12000,  # Depends on the model being used
        "azure": 90000,    # Azure için büyük limit (o1 modeli 128k token destekliyor)
    }
    
    limit = limits.get(ai_provider, 10000)
    
    if len(document_text) > limit:
        logger.info(f"Belge {ai_provider} için karakter sınırını aşıyor ancak kırpılmayacak (müşteri isteği). Uzunluk: {len(document_text)} karakter.")
        # Not ekliyoruz ancak dokümanı kırpmıyoruz
        if ai_provider == "azure":
            # Azure o1 modeli büyük belgeleri destekliyor, tam metni gönderiyoruz
            return document_text
    
    return document_text

def format_test_scenarios(scenarios_data):
    """
    Ensures the test scenarios are in a consistent format regardless of the AI provider
    
    Args:
        scenarios_data (dict or str): The raw scenarios data from the AI
        
    Returns:
        dict: Properly formatted test scenarios
    """
    # Default structure for test scenarios
    default_structure = {
        "summary": "Document analysis and test scenarios",
        "scenarios": []
    }
    
    # If the response is already structured properly, return it
    if isinstance(scenarios_data, dict) and "scenarios" in scenarios_data:
        # Make sure it exactly matches our expected format with conversions if needed
        formatted_result = default_structure.copy()
        formatted_result["summary"] = scenarios_data.get("summary", "Document analysis results")
        
        # Process each scenario to ensure it follows our required structure
        for scenario in scenarios_data.get("scenarios", []):
            # Create properly formatted scenario
            formatted_scenario = {
                "title": scenario.get("title", "Untitled Scenario"),
                "description": scenario.get("description", ""),
                "test_cases": []
            }
            
            # Handle different test case structures or convert steps array to string
            if "test_cases" in scenario:
                # Direct test_cases array, but make sure each has the right format
                for test_case in scenario["test_cases"]:
                    formatted_test_case = {
                        "title": test_case.get("title", "Untitled Test Case"),
                        "steps": test_case.get("steps", ""),
                        "expected_results": test_case.get("expected_results", "")
                    }
                    formatted_scenario["test_cases"].append(formatted_test_case)
            elif "steps" in scenario:
                # The scenario has steps but not test_cases - convert format
                if isinstance(scenario["steps"], list):
                    # Convert steps array to test cases
                    steps_str = ""
                    expected_results_str = ""
                    
                    for i, step in enumerate(scenario["steps"]):
                        step_num = i + 1
                        if isinstance(step, dict):  # If steps are objects with properties
                            steps_str += f"{step_num}. {step.get('action', '')}\n"
                            if "expected_result" in step:
                                expected_results_str += f"{step_num}. {step.get('expected_result', '')}\n"
                        else:  # If steps are just string entries
                            steps_str += f"{step_num}. {step}\n"
                    
                    # Create a single test case from the steps
                    formatted_scenario["test_cases"].append({
                        "title": "Main Flow",
                        "steps": steps_str.strip(),
                        "expected_results": expected_results_str.strip() or "Expected behavior according to requirements"
                    })
                else:
                    # Steps is not an array, use as is
                    formatted_scenario["test_cases"].append({
                        "title": "Main Flow",
                        "steps": str(scenario["steps"]),
                        "expected_results": scenario.get("expected_results", "Expected behavior according to requirements")
                    })
            
            # Add the formatted scenario
            formatted_result["scenarios"].append(formatted_scenario)
            
        return formatted_result
    
    # If it's a string (raw text), try to parse it
    if isinstance(scenarios_data, str):
        import json
        import re
        
        # Try to fix common JSON errors and then parse
        try:
            # Look for curly braces in the text to help locate the JSON content
            match = re.search(r'\{.*\}', scenarios_data, re.DOTALL)
            if match:
                potential_json = match.group(0)
                
                # Fix common issues with JSON format
                # 1. Fix unescaped quotes within strings
                fixed_json = re.sub(r'(?<=[^\\])"(?=.*":)', r'\"', potential_json)
                # 2. Fix new lines in strings
                fixed_json = fixed_json.replace('\\n', ' ').replace('\n', ' ')
                # 3. Handle unmatched quotes
                open_quotes = fixed_json.count('"')
                if open_quotes % 2 != 0:
                    fixed_json = fixed_json.rstrip('}') + '"}'
                
                # Try to parse the fixed JSON
                parsed_data = json.loads(fixed_json)
                if isinstance(parsed_data, dict):
                    # Make sure it has the required structure
                    if "scenarios" not in parsed_data:
                        parsed_data["scenarios"] = []
                    if "summary" not in parsed_data:
                        parsed_data["summary"] = "Generated test scenarios"
                        
                    return parsed_data
            
            # If the above failed, try to parse it as-is
            parsed_data = json.loads(scenarios_data)
            if isinstance(parsed_data, dict) and "scenarios" in parsed_data:
                return parsed_data
                
        except (json.JSONDecodeError, Exception) as e:
            # Not valid JSON, will handle as raw text
            print(f"JSON parsing error: {str(e)}")
        
        # Handle raw text format - very basic parsing
        # This is a fallback for when AI doesn't return structured data
        lines = scenarios_data.strip().split("\n")
        current_scenario = None
        current_test_case = None
        summary_text = ""
        
        result = default_structure.copy()
        
        # First few lines might be a summary
        if len(lines) > 5:
            summary_text = " ".join(lines[:5])
            result["summary"] = summary_text
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to determine if this is a new scenario (often starts with "Scenario" or has a number)
            if re.match(r'^(Scenario|Test Scenario|Use Case|#|\d+\.)', line, re.IGNORECASE):
                # New scenario
                current_scenario = {
                    "title": line,
                    "description": "",
                    "test_cases": []
                }
                result["scenarios"].append(current_scenario)
                current_test_case = None
                
            # Try to detect test case titles (often start with "Test Case" or have numbered sub-points)
            elif current_scenario and re.match(r'^(Test Case|Case|\d+\.\d+\.|\*)', line, re.IGNORECASE):
                # New test case within current scenario
                current_test_case = {
                    "title": line,
                    "steps": "",
                    "expected_results": ""
                }
                current_scenario["test_cases"].append(current_test_case)
                    
            # Detect steps sections
            elif current_test_case and re.search(r'(Steps|Step|Procedure|How to test)', line, re.IGNORECASE):
                # This line and following lines are steps
                current_test_case["steps"] = line
                    
            # Detect expected results sections
            elif current_test_case and re.search(r'(Expected|Result|Outcome|Should|Output)', line, re.IGNORECASE):
                # This line and following lines are expected results
                current_test_case["expected_results"] = line
                
            # If not a special section, add to the current section based on context
            elif current_scenario and current_test_case is None:
                # Part of scenario description
                current_scenario["description"] += line + " "
                
        # Make sure we have at least one scenario and test case
        if not result["scenarios"]:
            # Create a default scenario with some reasonable content
            result["scenarios"].append({
                "title": "Document Analysis",
                "description": "Based on the provided document",
                "test_cases": [
                    {
                        "title": "Basic Functionality Test",
                        "steps": "1. Prepare test environment\n2. Execute test procedure\n3. Verify results",
                        "expected_results": "System should behave according to specifications"
                    }
                ]
            })
                
        return result
    
    # If we get here, the format wasn't recognized, return a default structure
    return default_structure
