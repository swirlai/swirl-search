'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging

from swirl.mixers.relevancy import *
from swirl.mixers.date import *
from swirl.mixers.stack import *

logger = logging.getLogger(__name__)

# Mixer used when the requested name is unknown to this deployment.
# Every Swirl install ships RelevancyMixer, so it is a safe baseline.
_DEFAULT_MIXER_NAME = 'RelevancyMixer'


def alloc_mixer(mixer):
    if not mixer:
        logger.error("blank mixer")
        return None
    cls = globals().get(mixer)
    if cls is None:
        # Unknown mixer name (e.g. an enterprise-only class like
        # RelevancyConfidenceMixer requested by a UI that wasn't told the
        # backend lacks it). Falling back keeps a single bad query from
        # turning into a 500 + client-side retry round-trip.
        logger.warning(
            f"alloc_mixer: unknown mixer {mixer!r}; falling back to "
            f"{_DEFAULT_MIXER_NAME!r}"
        )
        cls = globals().get(_DEFAULT_MIXER_NAME)
    return cls


# Add new mixers here!