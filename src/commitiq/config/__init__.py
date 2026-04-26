# config/__init__.py
from .manager import ConfigManager

config = ConfigManager.get_instance()