# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
import logging

log = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.depends('date_order', 'pricelist_id', 'order_line')
    def _compute_sayof_currency_rate(self):
        """
        Compute sale order currency rate, say of currency and tax say of currency rate
        """
        for res in self:
            confirmation_date = res.date_order or fields.Date.today()
            if confirmation_date:
                rate = res.pricelist_id.currency_id._get_rates(res.company_id, confirmation_date)
                say_of_default_currency_rate_id = self.env['res.currency.rate'].sudo().search([('company_id','=',res.company_id.id), ('name','<=',confirmation_date),
                                                                                           ('currency_id','=',res.company_id.say_of_default_currency.id)], 
                                                                                            limit=1, order="name desc")
                
                tax_say_of_default_currency_rate_id = self.env['res.currency.rate'].sudo().search([('company_id','=',res.company_id.id), ('name','<=',confirmation_date),
                                                                                           ('currency_id','=',res.company_id.tax_say_of_default_currency.id)], 
                                                                                            limit=1, order="name desc")
                
                log.info("Adding sale order currency rate to : %s, sayof currency rate: %s, tax sayof currency rate: %s", 
                         rate.get(res.pricelist_id.currency_id.id), say_of_default_currency_rate_id.rate, tax_say_of_default_currency_rate_id.rate)
                
                res.so_currency_rate = rate.get(res.pricelist_id.currency_id.id)
                res.say_of_currency_rate = say_of_default_currency_rate_id.rate
                res.tax_say_of_currency_rate = tax_say_of_default_currency_rate_id.rate
                
    remarks = fields.Text()
    so_currency_rate = fields.Float(compute="_compute_sayof_currency_rate", copy=False, store=True)
    say_of_currency_rate = fields.Float(compute="_compute_sayof_currency_rate", copy=False, store=True)
    tax_say_of_currency_rate = fields.Float(compute="_compute_sayof_currency_rate", copy=False, store=True)
    
    def amount_to_text(self, currency_id, amount):
        return currency_id.amount_to_text(amount)