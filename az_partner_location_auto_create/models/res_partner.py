from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging 
log = logging.getLogger(__name__)
class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_foc_location = fields.Many2one('stock.location')
    customer_real_stock_location = fields.Many2one('stock.location')
    customer_consignment_stock_location = fields.Many2one('stock.location')
    customer_demo_stock_location = fields.Many2one('stock.location')
    customer_tender_stock_location = fields.Many2one('stock.location')
    
    def _create_main_partner_locations(self):
        if(not self.customer_foc_location):
            self.customer_foc_location = self._create_main_location("customer_foc_location")
        if(not self.customer_real_stock_location):
            self.customer_real_stock_location = self._create_main_location("customer_real_stock_location")
        if(not self.customer_consignment_stock_location):
            self.customer_consignment_stock_location = self._create_main_location("customer_consignment_stock_location")
        if(not self.customer_demo_stock_location):
            self.customer_demo_stock_location = self._create_main_location("customer_demo_stock_location")
        if(not self.customer_tender_stock_location):
            self.customer_tender_stock_location = self._create_main_location("customer_tender_stock_location")
            
      

    def _create_main_location(self, usage):
        self.ensure_one()
        if(usage == "customer_foc_location"):
            parent = self.company_id.defualt_customer_foc_location and self.company_id.defualt_customer_foc_location or self.env.company.defualt_customer_foc_location 
        if(usage == "customer_real_stock_location"):
            parent = self.company_id.defualt_customer_real_stock_location and self.company_id.defualt_customer_real_stock_location or self.env.company.defualt_customer_real_stock_location
        if(usage == "customer_consignment_stock_location"):
            parent = self.company_id.defualt_customer_consignment_stock_location and self.company_id.defualt_customer_consignment_stock_location or self.env.company.defualt_customer_consignment_stock_location
        if(usage == "customer_demo_stock_location"):
            parent = self.company_id.defualt_customer_demo_stock_location and self.company_id.defualt_customer_demo_stock_location or self.env.company.defualt_customer_demo_stock_location
        if(usage == "customer_tender_stock_location"):
            parent = self.company_id.defualt_customer_tender_stock_location and self.company_id.defualt_customer_tender_stock_location or self.env.company.defualt_customer_tender_stock_location
        
        return self.env['stock.location'].create({
            'name': self.name,
            'usage': parent.usage,
            'company_id': self.company_id and self.company_id.id or self.env.company.id,
            'location_id': parent.id,
            'is_partner_location': True,
        })
        
    def _check_default_locations(self):
        company = self.company_id and self.company_id or self.env.company
        if (not company.defualt_customer_real_stock_location):
            raise ValidationError(_('Fill Company Default Customer Locations'))
        if (not company.defualt_customer_foc_location):
            raise ValidationError(_('Fill Company Default Customer Locations'))
        if (not company.defualt_customer_consignment_stock_location):
            raise ValidationError(_('Fill Company Default Customer Locations'))
        if (not company.defualt_customer_demo_stock_location):
            raise ValidationError(_('Fill Company Default Customer Locations'))
        if (not company.defualt_customer_tender_stock_location):
            raise ValidationError(_('Fill Company Default Customer Locations'))
            
    
    def customer_location_open_quants(self):
        self.ensure_one()
        action = self.env.ref('stock.location_open_quants').read()[0]
        action['domain'] = [
            ('location_id', 'in', (self.customer_foc_location.id, self.customer_real_stock_location.id, self.customer_consignment_stock_location.id, self.customer_demo_stock_location.id, self.customer_tender_stock_location.id)),
        ]
        action['context'] = {'search_default_locationgroup':1}
        return action



    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)
        partner._check_default_locations()
        if vals.get('is_company', False):
            partner._create_main_partner_locations()

        return partner

    def write(self, vals):
        
        res = super(ResPartner, self).write(vals)
        self._check_default_locations()

        for partner in self:
            if (partner.is_company):
                partner._create_main_partner_locations()

        return res
