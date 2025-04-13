"""
Configuration manager for application settings
"""

import os
import json
import logging
from typing import Any, Dict, Union, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Configuration manager for application settings and API keys
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file if config_file is not None else os.path.join(os.path.dirname(__file__), 'config.json')
        
        # Önce API anahtarlarını güvenli şekilde al
        openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY', '')
        
        self.config = {
            'api_keys': {
                'openai': openai_api_key,
                'azure_openai': azure_openai_api_key
            },
            'endpoints': {
                'azure_openai': os.environ.get('AZURE_OPENAI_ENDPOINT', 'https://api-url.openai.azure.com/'),
                'azure_region': os.environ.get('AZURE_REGION', 'eastus')
            },
            'defaults': {
                'service': 'azure_openai',
                'model': 'gpt-4o',
                'max_tokens': 4000,
                'temperature': 0.7,
                'show_extracted_images': True
            },
            'ui': {
                'theme': 'dark',
                'language': 'tr',
                'notification_level': 'info'
            },
            'features': {
                'neuraagent_basic_enabled': True,
                'advanced_document_parsing': True,
                'image_recognition': True,
                'table_extraction': True
            }
        }
        
        # Try to load config file if it exists
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file if exists"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update config with loaded values
                    for section, values in loaded_config.items():
                        if section in self.config:
                            self.config[section].update(values)
                    logger.info(f"Loaded configuration from {self.config_file}")
            else:
                logger.info(f"Configuration file {self.config_file} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get_api_key(self, service: str) -> str:
        """
        Get API key for service
        
        Args:
            service: Service name (e.g. 'openai', 'azure_openai')
            
        Returns:
            API key string or empty string if not found
        """
        # Önce direkt ortam değişkenlerinden çek (en güncel değeri alabilmek için)
        env_key = ""
        if service == "openai":
            env_key = os.environ.get('OPENAI_API_KEY', '')
        elif service == "azure_openai":
            env_key = os.environ.get('AZURE_OPENAI_API_KEY', '')
            
        # Eğer ortam değişkeninde varsa onu kullan
        if env_key:
            # Ayrıca config'i de güncelle
            self.config['api_keys'][service] = env_key
            return env_key
            
        # Yoksa config'den çek
        if service in self.config['api_keys']:
            return self.config['api_keys'][service]
        return ''
    
    def set_api_key(self, service: str, api_key: str) -> None:
        """
        Set API key for service
        
        Args:
            service: Service name (e.g. 'openai', 'azure_openai')
            api_key: API key string
        """
        if service not in self.config['api_keys']:
            self.config['api_keys'][service] = {}
        
        self.config['api_keys'][service] = api_key
        self._save_config()
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get setting value
        
        Args:
            section: Section name (e.g. 'defaults', 'ui')
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default
    
    def update_setting(self, section: str, key: str, value: Any) -> None:
        """
        Update setting value
        
        Args:
            section: Section name (e.g. 'defaults', 'ui')
            key: Setting key
            value: New value
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        self._save_config()
    
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name (e.g. 'defaults', 'ui')
            
        Returns:
            Configuration section dictionary
        """
        if section in self.config:
            return self.config[section]
        return {}