# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

DEFAULT_PRIMARY = '#000000'
DEFAULT_SECONDARY = '#000000'


class BaseDocumentLayout(models.TransientModel):
    """
    Customise the company document layout and display a live preview
    """

    _inherit = 'base.document.layout'

    footer_logo = fields.Binary(related='company_id.footer_logo', readonly=False)
    preview_footer_logo = fields.Binary(related='footer_logo', string="Preview footer logo")