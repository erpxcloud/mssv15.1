from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def open_lb_partner_ledger(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner Ledger AC'),
            'view_mode': 'form',
            'res_model': 'amount.currency.wizard',
            'context': {'default_partner_id': self.id},
            'target': 'new'
        }
