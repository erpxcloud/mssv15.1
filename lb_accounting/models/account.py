from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang

import logging
import json

log = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Main Currency", readonly=True,
        help='Utility field to express amount currency', store=True)

    company_second_currency_id = fields.Many2one('res.currency', related='company_id.second_currency_id', string="Second Company Currency", readonly=True,
        help='Utility field to express amount currency', store=True)

    company_third_currency_id = fields.Many2one('res.currency', related='company_id.third_currency_id', string="Third Company Currency", readonly=True,
        help='Utility field to express amount currency', store=True)


class AccountInherited(models.Model):
    _inherit = 'account.account'
    
    automatic = fields.Boolean(string="automatic", default=False)
    def unlink(self):
        #Checking whether the account is set as a vat receivable / payable account  for any partner
        for record in self:
            partner_vat_receivable = self.env['res.partner'].search([('vat_receivable', '=', record.id)], limit=1)
            if partner_vat_receivable:
                raise ValidationError('You cannot remove/deactivate an account which is set as vat receivable account on a customer.')
            partner_vat_payable = self.env['res.partner'].search([('vat_payable', '=', record.id)], limit=1)
            if partner_vat_payable:
                raise ValidationError('You cannot remove/deactivate an account which is set as vat payable account on a vendor.')
        
        return super(AccountInherited, self).unlink()