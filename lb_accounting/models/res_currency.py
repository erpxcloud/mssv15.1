import logging
from odoo import api, fields, models, tools, _

log = logging.getLogger(__name__)

class Currency(models.Model):
    _inherit = "res.currency"
    
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits='Currency Rate',
                        help='The rate of the currency to the currency of rate 1.')
    rounding = fields.Float(string='Rounding Factor', digits='Currency Rate', default=0.01)
    
    
    def amount_to_text(self, amount):
        amount_words = super(Currency, self).amount_to_text(amount)
        amount_words = amount_words.replace(" And ", " ")
        
        return amount_words
    
class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    rate = fields.Float(digits='Currency Rate', default=1.0, help='The rate of the currency to the currency of rate 1')