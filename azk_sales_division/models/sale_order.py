from odoo import fields, models, api
import logging

log = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    division_id = fields.Many2one('azk_sales_division.division', string='Division', help='Division')
    
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res["division_id"] = self.division_id
        return res
    
#     @api.onchange('division_id')
#     def division_change(self): 
#         #Get the original defined domain in order to preserve original function

#         salesperson_domain = self.env['sale.order'].fields_get(['user_id'], ['domain']).get('user_id',{}).get('domain', [])
        
#         if self.division_id:
#             #check if there is a domain previously defined and append to it
#             if salesperson_domain:
#                 salesperson_domain = list(salesperson_domain)
#                 salesperson_domain.insert(0, '&')
#                 salesperson_domain.append(('id', 'in', self.division_id.salesperson_ids.mapped('id')))
#             else:
#                 salesperson_domain = [('id', 'in', self.division_id.salesperson_ids.mapped('id'))]
            
#         rt_value = {
#              'domain': {
#                  'user_id': salesperson_domain
#                  }
#             }
      
#         if self.user_id and not self.user_id in self.env['res.users'].search(salesperson_domain):
#             self.user_id = False
            
#         log.debug("Called on change: %s and returned: %s", self, rt_value)
#         return rt_value
    
#     @api.onchange('partner_id')
#     def onchange_partner_id(self):
#         result = super(SaleOrder,self).onchange_partner_id()
#         self.division_change()
#         log.debug("Called onchange_partner_id: %s", self)
        
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.onchange('product_id', 'product_template_id')
    def _adjust_product_template_domain(self):
        #Get the original defined domain in order to preserve original function 
        product_template_domain = self.env['sale.order.line'].fields_get(['product_template_id'], ['domain']).get('product_template_id', {}).get('domain', [])
        product_domain = self.env['sale.order.line'].fields_get(['product_id'], ['domain']).get('product_id',{}).get('domain', [])
        
        if self.order_id.division_id:
            #check if there is a domain previously defined and append to it
            if product_template_domain:
                product_template_domain = list(product_template_domain)
                product_template_domain.append(('id', 'in', self.order_id.division_id.product_ids.mapped('id')))
            else:
                product_template_domain = [('id', 'in', self.order_id.division_id.product_ids.mapped('id'))]
              
            if product_domain:
                product_domain = eval(product_domain, {'company_id': self.company_id}) 
                product_domain.insert(0, '&')
                product_domain.append(('id', 'in', self.env['product.product'].search([('product_tmpl_id', 'in', 
                                                                                        self.order_id.division_id.product_ids.mapped('id'))
                                                                                        ]
                                                                                    ).mapped('id')
                                    )
                )
            else:
                product_domain = [('id', 'in', self.env['product.product'].search([('product_tmpl_id', 'in', 
                                                                                        self.order_id.division_id.product_ids.mapped('id'))
                                                                                        ]
                                                                                    ).mapped('id'))] 
        rt_value = {
             'domain': {
                 'product_template_id': product_template_domain,
                 'product_id': product_domain,
                 },
             }
        
        log.debug("Called _adjust_product_template_domain on %s and return %s", self, rt_value)  
        
        return rt_value
    
