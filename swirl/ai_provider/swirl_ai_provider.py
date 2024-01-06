from django.conf import settings
from abc import ABCMeta, abstractmethod

import logging
logger = logging.getLogger(__name__)


class SwirlAIClient(metaclass=ABCMeta):
    """
    SwirlAIClient abstracts the AIClient methods used to switch between our internal client and LiteLLM.
    """



    @abstractmethod
    def get_model(super):
        pass

    @abstractmethod
    def get_encoding_model(super):
        pass

    @abstractmethod
    def get_completion(super, system_text, prompt, temperature):
        pass