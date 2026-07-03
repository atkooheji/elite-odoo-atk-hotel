# -*- coding: utf-8 -*-
import logging
import warnings

# Ignore specific warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*google.generativeai.*")
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*google\._upb\._message\..*uses PyType_Spec.*",
)

_logger = logging.getLogger(__name__)

# Standard imports
from . import models
from . import wizard
from . import report
from . import controllers
from .monkeypatches import patch_safe_many2one_convert_to_read

from .hooks import pre_init_hook, post_init_hook

if patch_safe_many2one_convert_to_read:
    patch_safe_many2one_convert_to_read()
