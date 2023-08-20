import logging
import os

from lxml import etree

from odoo.loglevels import ustr
from odoo.tools import misc, view_validation

_logger = logging.getLogger(__name__)

_threed_view_validator = None


@view_validation.validate("threedview")
def schema_threedview(arch, **kwargs):
    """Check the threedview view against its schema

    :type arch: etree._Element
    """
    global _threed_view_validator

    if _threed_view_validator is None:
        with misc.file_open(os.path.join("web_threed", "rng", "web_threed.rng")) as f:
            _threed_view_validator = etree.RelaxNG(etree.parse(f))

    if _threed_view_validator.validate(arch):
        return True

    for error in _threed_view_validator.error_log:
        _logger.error(ustr(error))
    return False
