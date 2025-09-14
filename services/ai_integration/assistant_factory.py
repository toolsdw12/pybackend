from typing import Dict, Type
from .base_assistant import BaseAssistant
from .providers.openai_assistant import OpenAIAssistant
from .providers.gemini_assistant import GeminiAssistant
import logging

logger = logging.getLogger(__name__)

class AssistantFactory:
    """Factory class for creating AI assistant instances"""
    
    _assistants: Dict[str, Type[BaseAssistant]] = {
        "openai": OpenAIAssistant,
        "gemini": GeminiAssistant,
        # Add more assistant implementations here as they are created
    }
    
    @classmethod
    def get_assistant(cls, assistant_type: str) -> BaseAssistant:
        """
        Get an instance of the specified AI assistant
        
        Args:
            assistant_type: The type of assistant to create (e.g., "openai", "gemini")
            
        Returns:
            An instance of the specified AI assistant
            
        Raises:
            ValueError: If the specified assistant type is not supported
        """
        assistant_class = cls._assistants.get(assistant_type.lower())
        if not assistant_class:
            supported_types = ", ".join(cls._assistants.keys())
            raise ValueError(
                f"Unsupported assistant type: {assistant_type}. "
                f"Supported types are: {supported_types}"
            )
            
        try:
            return assistant_class()
        except Exception as e:
            logger.error(f"Error creating {assistant_type} assistant: {str(e)}")
            raise 