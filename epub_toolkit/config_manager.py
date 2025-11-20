#!/usr/bin/env python3
"""
Unified Config Manager 
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ConfigPaths:
    """Manage config file paths"""
    root_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    config_dir: Path = field(init=False)
    main_config: Path = field(init=False)
    
    def __post_init__(self):
        self.config_dir = self.root_dir / "config"
        self.main_config = self.config_dir / "ai_models_config.yaml"

class UnifiedConfigManager:
    """Unified configuration manager - maintains existing functions, removes hardcoding"""
    
    _instance = None
    _config_data = None
    _last_modified = None
    
    def __new__(cls):
        """Singleton pattern: only one instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialization - run only on first call"""
        if not hasattr(self, 'initialized'):
            # ✅ 1. Load environment variables (highest priority)
            self._load_environment()
            
            # 2. Load YAML configuration
            self.paths = ConfigPaths()
            self.initialized = True
            self._load_config()
    
    def _load_environment(self) -> None:
        """Load environment variables, including .env files (graceful)"""
        try:
            from dotenv import load_dotenv
            
            # Search for .env in current and project root directories
            current_dir = Path.cwd()
            project_root = Path(__file__).parent.parent
            
            env_paths = [
                current_dir / ".env",
                project_root / ".env",
                current_dir / ".env.local",
                project_root / ".env.local"
            ]
            
            loaded_files = []
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path, override=True)
                    loaded_files.append(env_path.name)
            
            if loaded_files:
                logger.debug(f"✅ .env files loaded: {', '.join(loaded_files)}")
            else:
                logger.debug(".env files not found - using system environment variables only")
                
        except ImportError:
            logger.warning("⚠️ python-dotenv not installed - using system environment variables only")
            logger.warning("💡 Install: pip install python-dotenv")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load .env files: {e}")
    
    def _load_config(self) -> None:
        """Load config file and handle hot reload"""
        config_file = self.paths.main_config
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file is required: {config_file}")
        
        # Check modification time for hot reload
        current_modified = config_file.stat().st_mtime
        if (self._last_modified is None or 
            current_modified > self._last_modified):
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
            
            self._last_modified = current_modified
            logger.debug(f"Config reloaded: {config_file}")
            
            # Apply environment variable overrides
            self._apply_env_overrides()
    
    def _apply_env_overrides(self) -> None:
        """Override config values with environment variables"""
        env_mappings = {
            'DEFAULT_AI_MODEL': 'ai_behavior.default_provider',
            'MAX_FILE_SIZE_MB': 'file_processing.max_file_size_mb',
            'TARGET_WCAG_LEVEL': 'processing_defaults.target_wcag_level',
            'BACKUP_ENABLED': 'processing_defaults.create_backup',
            'QUIET_MODE': 'logging_settings.quiet_mode',
            'LOG_LEVEL': 'logging_settings.level',
            'OUTPUT_SUFFIX': 'output_settings.output_suffix',
            'REPORT_FORMAT': 'output_settings.report_format',
            'API_TIMEOUT': 'api_settings.timeout',
            'MAX_RETRIES': 'ai_behavior.max_retries',
        }
        
        for env_key, config_path in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                self._set_nested_value(config_path, self._convert_env_value(env_value))
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to an appropriate type"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    
    def _set_nested_value(self, path: str, value: Any) -> None:
        """Set value in nested dictionary by dot-separated path"""
        keys = path.split('.')
        current = self._config_data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by nested path (maintains existing behavior)"""
        self._load_config()
        
        keys = path.split('.')
        current = self._config_data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    # ✅ New debugging method
    def debug_api_keys(self) -> Dict[str, Any]:
        """API key debugging information (for development)"""
        debug_info = {
            "env_files_checked": [],
            "api_keys_found": {},
            "api_keys_valid": {}
        }
        
        # Check .env files
        current_dir = Path.cwd()
        project_root = Path(__file__).parent.parent
        
        env_paths = [
            current_dir / ".env",
            project_root / ".env",
            current_dir / ".env.local",
            project_root / ".env.local"
        ]
        
        for env_path in env_paths:
            debug_info["env_files_checked"].append({
                "path": str(env_path),
                "exists": env_path.exists(),
                "size": env_path.stat().st_size if env_path.exists() else 0
            })
        
        # Check API keys
        models = self.get('models', {})
        for provider, config in models.items():
            env_var = config.get('env_var', f'{provider.upper()}_API_KEY')
            api_key = os.getenv(env_var)
            
            debug_info["api_keys_found"][provider] = {
                "env_var": env_var,
                "has_key": bool(api_key),
                "key_length": len(api_key) if api_key else 0,
                "key_prefix": api_key[:10] + "..." if api_key and len(api_key) > 10 else api_key
            }
            
            # Key format validation
            if api_key:
                expected_prefix = config.get('key_prefix', '')
                debug_info["api_keys_valid"][provider] = api_key.startswith(expected_prefix) if expected_prefix else True
            else:
                debug_info["api_keys_valid"][provider] = False
        
        return debug_info
    
    # =============================================================================
    # New centralized config access functions
    # =============================================================================
    
    def get_app_info(self, key: str = None) -> Union[Dict[str, Any], str]:
        """Get application info (removes hardcoding)"""
        app_info = self.get('app_info', {})
        if key:
            return app_info.get(key, "")
        return app_info
    
    def get_ai_model_config(self, provider: str, key: str = None) -> Any:
        """Get AI model configuration for a provider (removes hardcoding)"""
        model_config = self.get(f'models.{provider}', {})
        if key:
            return model_config.get(key, "")
        return model_config
    
    def get_external_tool_config(self, tool: str, key: str = None) -> Any:
        """Get external tool configuration (removes hardcoding)"""
        tool_config = self.get(f'external_tools.{tool}', {})
        if key:
            return tool_config.get(key, "")
        return tool_config
    
    def get_message(self, category: str, key: str) -> str:
        """Get a message string from config (removes hardcoding)"""
        return self.get(f'messages.{category}.{key}', f"[{category}.{key}]")
    
    def get_prompt_template(self, template_name: str) -> str:
        """Get a prompt template from config (removes hardcoding)"""
        return self.get(f'prompts.{template_name}', '')
    
    def get_cli_help(self, section: str) -> List[str]:
        """Get CLI help section from config (removes hardcoding)"""
        return self.get(f'cli_help.{section}', [])
    
    def get_standard_info(self, standard: str, key: str = None) -> Any:
        """Get standard information from config (removes hardcoding)"""
        standard_info = self.get(f'standards.{standard}', {})
        if key:
            return standard_info.get(key, "")
        return standard_info
    
    # =============================================================================
    # Preserve existing functions (ensure compatibility)
    # =============================================================================
    
    def get_ai_config(self, provider: str = None) -> Dict[str, Any]:
        """Get settings for a specific AI provider (backward-compatible)"""
        provider = provider or self.get('ai_behavior.default_provider')
        
        return {
            'models': self.get(f'models.{provider}'),
            'api_settings': self.get('api_settings'),
            'prompts': self.get('prompts'),
            'fallback': self.get('fallback'),
            'processing_defaults': self.get('processing_defaults'),
        }
    
    def get_all_ai_providers(self) -> List[str]:
        """Return list of all available AI providers (backward-compatible)"""
        models = self.get('models', {})
        return list(models.keys())
    
    def get_model_for_provider(self, provider: str) -> str:
        """Get default model for a provider (backward-compatible)"""
        return self.get(f'models.{provider}.default', 'default-model')
    
    def get_fallback_models(self, provider: str) -> List[str]:
        """Get fallback models for a provider (backward-compatible)"""
        return self.get(f'models.{provider}.fallbacks', [])
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Return consolidated processing-related settings (backward-compatible)"""
        return {
            'wcag_level': self.get('processing_defaults.target_wcag_level'),
            'max_file_size_mb': self._get_with_env('file_processing.max_file_size_mb', 'MAX_FILE_SIZE_MB'),
            'create_backup': self.get('processing_defaults.create_backup'),
            'preserve_original': self.get('processing_defaults.preserve_original'),
            'language': self.get('processing_defaults.language'),
            'timezone': self.get('processing_defaults.timezone'),
        }
    
    def get_output_config(self) -> Dict[str, Any]:
        """Return consolidated output-related settings (backward-compatible)"""
        return {
            'validate_output': self.get('output_settings.validate_output'),
            'generate_report': self.get('output_settings.generate_report'),
            'output_suffix': self.get('output_settings.output_suffix'),
            'report_format': self.get('output_settings.report_format'),
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Return consolidated logging settings (backward-compatible)"""
        return {
            'level': self.get('logging_settings.level'),
            'quiet_mode': self.get('logging_settings.quiet_mode'),
        }
    
    def _get_with_env(self, config_path: str, env_var: str) -> Any:
        """Get config value but prefer environment variable (backward-compatible)"""
        env_value = os.getenv(env_var)
        if env_value is not None:
            return self._convert_env_value(env_value)
        return self.get(config_path)
    
    def check_api_keys(self) -> Dict[str, bool]:
        """Check existence of API keys (backward-compatible)"""
        api_key_status = {}
        models = self.get('models', {})
        
        for provider, config in models.items():
            env_var = config.get('env_var', f'{provider.upper()}_API_KEY')
            api_key = os.getenv(env_var)
            api_key_status[provider] = bool(api_key and len(api_key.strip()) > 10)
        
        return api_key_status
    
    def get_available_providers_by_api_key(self) -> List[str]:
        """Return providers that have API keys set (backward-compatible)"""
        api_status = self.check_api_keys()
        return [provider for provider, has_key in api_status.items() if has_key]
    
# Global instance creation (same as before)
config_manager = UnifiedConfigManager()

# Convenience functions (preserve existing ones)
def get_default_ai() -> str:
    """Return default AI provider"""
    return config_manager.get('ai_behavior.default_provider')

def get_max_file_size() -> int:
    """Return maximum file size"""
    return config_manager._get_with_env('file_processing.max_file_size_mb', 'MAX_FILE_SIZE_MB')

def get_ai_model(provider: str) -> str:
    """Return default model for a specific AI provider"""
    return config_manager.get_model_for_provider(provider)

def setup_logging_from_config():
    """Configure logging from config"""
    log_config = config_manager.get_logging_config()
    
    level = getattr(logging, log_config['level'].upper(), logging.INFO)
    
    if log_config['quiet_mode']:
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(
            level=level,
            format=config_manager.get('logging_settings.format')
        )

# ✅ New debugging convenience function
def debug_api_keys():
    """Print API key debugging information (for development)"""
    debug_info = config_manager.debug_api_keys()
    
    print("🔍 API key debugging information")
    print("=" * 50)
    
    print("📁 .env files checked:")
    for file_info in debug_info["env_files_checked"]:
        status = "✅" if file_info["exists"] else "❌"
        size_info = f"({file_info['size']}bytes)" if file_info["exists"] else ""
        print(f"  {status} {file_info['path']} {size_info}")
    
    print("\n🔑 API key status:")
    for provider, key_info in debug_info["api_keys_found"].items():
        has_key = "✅" if key_info["has_key"] else "❌"
        valid = "✅" if debug_info["api_keys_valid"].get(provider) else "❌"
        length = f"({key_info['key_length']} chars)" if key_info["has_key"] else ""
        print(f"  {has_key} {provider.upper()}: {key_info['env_var']} {length} (format: {valid})")
        if key_info["has_key"] and key_info["key_prefix"]:
            print(f"      Preview: {key_info['key_prefix']}")

if __name__ == "__main__":
    """Run tests"""
    print("🧪 Config Manager test")
    debug_api_keys()