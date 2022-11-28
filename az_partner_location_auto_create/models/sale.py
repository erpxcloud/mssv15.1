from odoo import fields, models, api
import logging

log = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    sale_order_type = fields.Many2one('sale.order.type')
    read_only_price_unit = fields.Boolean(default=False)
    transfer = fields.Many2one("stock.picking")
    related_to_transfer = fields.Boolean(related='sale_order_type.related_to_transfer')
    partner_location_demo = fields.Many2one(related='partner_id.customer_demo_stock_location')
    
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('foc_approval', 'FOC Approval'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')
    
    
    def write(self, values):
        rec = super(SaleOrder, self).write(values)
        for record in self:
            if (self.sale_order_type.set_price_to_zero):
                for line in self.order_line:
                    line.price_unit = 0
                    line.read_only_price_unit = True
            else:
                for line in self.order_line:
                    line.read_only_price_unit = False
        return rec
    
    @api.model
    def create(self, vals):
        rec = super(SaleOrder, self).create(vals)
        for record in rec:
            if (rec.sale_order_type.set_price_to_zero):
                for line in rec.order_line:
                    line.price_unit = 0
                    line.read_only_price_unit = True
            else:
                for line in rec.order_line:
                    line.read_only_price_unit = False
        return rec
        
    @api.onchange('sale_order_type')
    def onchange_sale_order_type(self):
        if (self.sale_order_type.set_price_to_zero):
            for line in self.order_line:
                line.price_unit = 0
                line.read_only_price_unit = True
        else:
            for line in self.order_line:
                line.read_only_price_unit = False
    
    @api.onchange('order_line')
    def onchange_order_line(self):
        try:
            res = super(SaleOrder, self).onchange_order_line()
        except:
            res = True
        if (self.sale_order_type.set_price_to_zero):
            for line in self.order_line:
                line.price_unit = 0
                line.read_only_price_unit = True
        else:
            for line in self.order_line:
                line.read_only_price_unit = False
    
    def action_sale_ok(self):
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id
        partner_foc_ids = [partner_id.customer_foc_location.id]
        for partner in partner_id.child_ids:
            partner_foc_ids.append(partner.customer_foc_location.id)
        
        product_ids=[]
        for line in self.order_line:
            product_ids.append(lien.product_id)
        domain = [
            ('location_id', 'in', partner_foc_ids),
            ('product_id', 'in', product_ids),
            ('quantity', '>', 0)]
        if self.sale_order_type.set_price_to_zero:
            products = self.env['stock.quant'].search(domain,limit=1)
            if products:
                    imd = self.env['ir.model.data']
                    wiz_id = self.env['customer.foc.wizard'].create({})
                    action = imd.xmlid_to_object('az_partner_location_auto_create.action_customer_foc_wizard')
                    form_view_id = imd.xmlid_to_res_id('az_partner_location_auto_create.view_customer_foc_wizard_form_foc')
                    return {
                            'name': action.name,
                            'help': action.help,
                            'type': action.type,
                            'views': [(form_view_id, 'form')],
                            'view_id': form_view_id,
                            'target': action.target,
                            'context': action.context,
                            'res_model': action.res_model,
                            'res_id':wiz_id.id,
                        }
            else:
                self.action_confirm()
        else:
            self.action_confirm()
            

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    read_only_price_unit = fields.Boolean(default=False)