from odoo import fields, models, api
import logging
from passlib.tests.utils import limit

log = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    division_id = fields.Many2one('azk_sales_division.division', string='Division', help='Division')
    
    def action_new_quotation(self):
        action = super(CrmLead, self).action_new_quotation()
        
        action['context']['default_division_id'] = self.division_id.id
        action['context']['default_user_id'] = self.user_id.id
        
        log.debug("Returning for %s action.context: %s", self, action['context'])
        
        return action
    
    @api.onchange('division_id')
    def division_change(self): 
        #Get the original defined domain in order to preserve original function 
        salesperson_domain = self.env['crm.lead'].fields_get(['user_id'], ['domain']).get('user_id',{}).get('domain', [])
        log.info(f'\n\n\n{type(salesperson_domain)}\n\n\n\n.')
        if self.division_id:
            #check if there is a domain previously defined and append to it
            
            if salesperson_domain:
                salesperson_domain.insert(0, '&')
                salesperson_domain.append(('id', 'in', self.division_id.salesperson_ids.mapped('id')))
            else:
                salesperson_domain = [('id', 'in', self.division_id.salesperson_ids.mapped('id'))]
        
        rt_value = {
             'domain': {
                 'user_id': salesperson_domain
                 }
            }
        if self.user_id and not self.user_id in self.env['res.users'].search(salesperson_domain):
            self.user_id = False

        log.debug("Called on change: %s and returned: %s", self, rt_value)
        return rt_value
