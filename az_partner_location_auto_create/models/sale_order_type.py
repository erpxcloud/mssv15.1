import logging

from odoo import fields, models,api

log = logging.getLogger(__name__)


class SaleOrderType(models.Model):
    _name = "sale.order.type"
    _description = "Sale Order Type"
    
    def _get_default_company(self):
        selected_companies = self.env['res.company'].browse(self._context.get('allowed_company_ids'))
        if selected_companies and selected_companies[0]:
            comapny = selected_companies[0]
        else:
             comapny = self.env.user.company_id
        return comapny
    
    name = fields.Char(required=True, index=True)
    default_stok_location = fields.Many2one("stock.location")
    set_price_to_zero = fields.Boolean(default=False)
    related_to_transfer = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=_get_default_company)
    active = fields.Boolean(default=True, help="If unchecked, it will allow you to hide the quotation type without removing it.")
    
    
    @api.model
    def search(self, domain, *args, **kwargs):
        selected_companies = self.env['res.company'].browse(self._context.get('allowed_company_ids'))
        domain += [('company_id', 'in', selected_companies.ids)]
        return super(SaleOrderType, self).search(domain, *args, **kwargs)