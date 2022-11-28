from odoo import api, fields, models


class customer_foc_wizard(models.TransientModel):
    _name = "customer.foc.wizard"
    _description = 'Customer FOC Wizard'
    
    def set_foc_state(self):
        order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        order_id.state = 'foc_approval'
        return True