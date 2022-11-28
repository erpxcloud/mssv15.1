# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, RedirectWarning
import logging
from odoo.tools.float_utils import float_is_zero

log = logging.getLogger(__name__)


class AccountInvoiceInherited(models.Model):
    _inherit = 'account.move'
    
    @api.model
    def _auto_init(self):
        self._cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS invoice_currency_rate NUMERIC DEFAULT 1
        """)
        self._cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS say_of_currency_rate NUMERIC DEFAULT 1
        """)
        self._cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS tax_say_of_currency_rate NUMERIC DEFAULT 1
        """)
        
        return super(AccountInvoiceInherited, self)._auto_init()
           
    @api.depends('invoice_date', 'currency_id', 'invoice_line_ids', 'line_ids')
    def _compute_sayof_currency_rate(self):
        """
        Compute invoice currency rate, say of currency and tax say of currency rate
        """
        for res in self:
            date_invoice = res.invoice_date or fields.Date.today()
            if date_invoice:
                rate = res.currency_id._get_rates(res.company_id, date_invoice)
                say_of_default_currency_rate_id = self.env['res.currency.rate'].sudo().search([('company_id','=',res.company_id.id), ('name','<=',date_invoice),
                                                                                           ('currency_id','=',res.company_id.say_of_default_currency.id)], 
                                                                                            limit=1, order="name desc")
                
                tax_say_of_default_currency_rate_id = self.env['res.currency.rate'].sudo().search([('company_id','=',res.company_id.id), ('name','<=',date_invoice),
                                                                                           ('currency_id','=',res.company_id.tax_say_of_default_currency.id)], 
                                                                                            limit=1, order="name desc")
                
                log.info("Adding invoice currency rate to : %s, sayof currency rate: %s, tax sayof currency rate: %s", 
                         rate.get(res.currency_id.id), say_of_default_currency_rate_id.rate, tax_say_of_default_currency_rate_id.rate)
                
                res.invoice_currency_rate = rate.get(res.currency_id.id)
                res.say_of_currency_rate = say_of_default_currency_rate_id.rate
                res.tax_say_of_currency_rate = tax_say_of_default_currency_rate_id.rate
        
    remarks = fields.Text()
    invoice_currency_rate = fields.Float(compute="_compute_sayof_currency_rate", copy=False, store=True)
    say_of_currency_rate = fields.Float(compute="_compute_sayof_currency_rate", copy=False, store=True)
    tax_say_of_currency_rate = fields.Float(compute="_compute_sayof_currency_rate",copy=False, store=True)
    
    def amount_to_text(self, currency_id, amount):
        return currency_id.amount_to_text(amount)
