from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

class AccountTaxTemplate(models.Model):
    """ Add fields used to define some lebanese taxes """
    _inherit = 'account.tax.template'

    vat_tax = fields.Boolean(string="Is VAT Tax")

class AccountTaxInherited(models.Model):
    _inherit = 'account.tax'

    vat_tax = fields.Boolean(string="Is VAT Tax")
