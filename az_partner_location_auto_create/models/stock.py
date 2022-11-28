from odoo import api, fields, models
import logging 
log = logging.getLogger(__name__)



class StockPicking(models.Model):
    _inherit = 'stock.picking'
    expiry_date = fields.Date()
    show_expiry_date = fields.Boolean(compute = "_compute_expiry_date_to_show")
    
    def _compute_expiry_date_to_show(self):
        for line in self:
            if line.picking_type_code == "internal" and  (line.picking_type_id.default_location_dest_id == self.env.company.defualt_customer_demo_stock_location 
                                                          or line.picking_type_id.default_location_dest_id == self.env.company.defualt_customer_consignment_stock_location):
                line.show_expiry_date = True
            else:
                line.show_expiry_date = False
            
    def button_validate(self):
        for picking in self:
            if picking.picking_type_code == "incoming" and picking.partner_id and (picking.partner_id.is_company or (picking.sale_id)):
                if picking.sale_id:
                    location = picking.location_dest_id
                    source_location = picking.location_id
                    if self.company_id.defualt_customer_real_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_real_stock_location:
                        source_location = picking.sale_id.partner_id.customer_real_stock_location
                    if self.company_id.defualt_customer_foc_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_foc_location:
                        source_location = picking.sale_id.partner_id.customer_foc_location
                    if self.company_id.defualt_customer_tender_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_tender_stock_location:
                        source_location = picking.sale_id.partner_id.customer_tender_stock_location
                    if self.company_id.defualt_customer_consignment_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_consignment_stock_location:
                        location = picking.sale_id.partner_id.customer_consignment_stock_location
                        source_location = picking.sale_id.partner_id.customer_real_stock_location
                        
                        picking.location_dest_id = location
                        for move in picking.move_lines:
                            move.location_dest_id = location
                        for move_line in picking.move_line_ids:
                            move_line.location_dest_id = location
                    picking.location_id = source_location
                    for move in picking.move_lines:
                        move.location_id = source_location
                    for move_line in picking.move_line_ids:
                        move_line.location_id = source_location
                else:
                    source_location = False
                    if self.company_id.defualt_customer_real_stock_location and picking.location_id and picking.location_id == self.company_id.defualt_customer_real_stock_location:
                        source_location = picking.partner_id.customer_real_stock_location
                    if self.company_id.defualt_customer_foc_location and picking.location_id and picking.location_id == self.company_id.defualt_customer_foc_location:
                        source_location = picking.partner_id.customer_foc_location
                    if self.company_id.defualt_customer_tender_stock_location and picking.location_id and picking.location_id == self.company_id.defualt_customer_tender_stock_location:
                        source_location = picking.partner_id.customer_tender_stock_location
                    if self.company_id.defualt_customer_consignment_stock_location and picking.location_id and picking.location_id == self.company_id.defualt_customer_consignment_stock_location:
                        source_location = picking.partner_id.customer_consignment_stock_location
                    
                    if source_location:
                        picking.location_id = source_location
                        for move in picking.move_lines:
                            move.location_id = source_location
                        for move_line in picking.move_line_ids:
                            move_line.location_id = source_location

                        
            if picking.picking_type_code == "outgoing" and picking.partner_id and (picking.partner_id.is_company or (picking.sale_id)):
                if picking.sale_id:
                    dest_location = picking.location_dest_id
                    location = picking.location_id
                    if self.company_id.defualt_customer_real_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_real_stock_location:
                        dest_location = picking.sale_id.partner_id.customer_real_stock_location
                    if self.company_id.defualt_customer_foc_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_foc_location:
                        dest_location = picking.sale_id.partner_id.customer_foc_location
                    if self.company_id.defualt_customer_tender_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_tender_stock_location:
                        dest_location = picking.sale_id.partner_id.customer_tender_stock_location
                    if self.company_id.defualt_customer_consignment_stock_location and picking.sale_id.sale_order_type and picking.sale_id.sale_order_type.default_stok_location == self.company_id.defualt_customer_consignment_stock_location:
                        location = picking.sale_id.partner_id.customer_consignment_stock_location
                        dest_location = picking.sale_id.partner_id.customer_real_stock_location
                        
                        picking.location_id = location
                        for move in picking.move_lines:
                            move.location_id = location
                        for move_line in picking.move_line_ids:
                            move_line.location_id = location
                    
                    picking.location_dest_id = dest_location
                    for move in picking.move_lines:
                        move.location_dest_id = dest_location
                    for move_line in picking.move_line_ids:
                        move_line.location_dest_id = dest_location
                else:
                    dest_location = picking.location_dest_id
                    if self.company_id.defualt_customer_real_stock_location and picking.location_dest_id and picking.location_dest_id == self.company_id.defualt_customer_real_stock_location:
                        dest_location = picking.partner_id.customer_real_stock_location
                    if self.company_id.defualt_customer_foc_location and picking.location_dest_id and picking.location_dest_id == self.company_id.defualt_customer_foc_location:
                        dest_location = picking.partner_id.customer_foc_location
                    if self.company_id.defualt_customer_tender_stock_location and picking.location_dest_id and picking.location_dest_id == self.company_id.defualt_customer_tender_stock_location:
                        dest_location = picking.partner_id.customer_tender_stock_location
                    if self.company_id.defualt_customer_consignment_stock_location and picking.location_dest_id and picking.location_dest_id == self.company_id.defualt_customer_consignment_stock_location:
                        dest_location = picking.partner_id.customer_consignment_stock_location
                    
                    if dest_location:
                        picking.location_dest_id = dest_location
                        for move in picking.move_lines:
                            move.location_dest_id = dest_location
                        for move_line in picking.move_line_ids:
                            move_line.location_dest_id = dest_location


                    
            
            if(picking.picking_type_code == "internal" and  picking.picking_type_id.default_location_dest_id == picking.company_id.defualt_customer_demo_stock_location 
               and picking.partner_id and picking.partner_id.is_company and picking.partner_id.customer_demo_stock_location and picking.partner_id.customer_demo_stock_location != picking.location_id):
                picking.location_dest_id = picking.partner_id.customer_demo_stock_location
                for move in picking.move_lines:
                    move.location_dest_id = picking.partner_id.customer_demo_stock_location
                for move_line in picking.move_line_ids:
                    move_line.location_dest_id = picking.partner_id.customer_demo_stock_location
                    
            if(picking.picking_type_code == "internal" and  picking.picking_type_id.default_location_dest_id == picking.company_id.defualt_customer_consignment_stock_location 
               and picking.partner_id and picking.partner_id.is_company and picking.partner_id.customer_consignment_stock_location and picking.partner_id.customer_consignment_stock_location != picking.location_id):
                picking.location_dest_id = picking.partner_id.customer_consignment_stock_location
                for move in picking.move_lines:
                    move.location_dest_id = picking.partner_id.customer_consignment_stock_location
                for move_line in picking.move_line_ids:
                    move_line.location_dest_id = picking.partner_id.customer_consignment_stock_location
                    
            
                
        return super(StockPicking,self).button_validate()            

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        res = super(StockPicking,self).onchange_picking_type()
        if (self.picking_type_id and self.partner_id):
            if(self.picking_type_code == "internal" and  self.picking_type_id.default_location_dest_id == self.company_id.defualt_customer_demo_stock_location 
               and self.partner_id and self.partner_id.is_company and self.partner_id.customer_demo_stock_location and self.partner_id.customer_demo_stock_location != self.location_id):
                self.location_dest_id = self.partner_id.customer_demo_stock_location
            if(self.picking_type_code == "internal" and  self.picking_type_id.default_location_dest_id == self.company_id.defualt_customer_consignment_stock_location 
               and self.partner_id and self.partner_id.is_company and self.partner_id.customer_consignment_stock_location and self.partner_id.customer_consignment_stock_location != self.location_id):
                self.location_dest_id = self.partner_id.customer_consignment_stock_location
        if self.picking_type_id:
            if self.picking_type_code == "internal" and  self.picking_type_id.default_location_dest_id == self.company_id.defualt_customer_demo_stock_location or self.picking_type_id.default_location_dest_id == self.company_id.defualt_customer_consignment_stock_location:
                self.show_expiry_date = True
            else:
                self.show_expiry_date = False
        return res
            