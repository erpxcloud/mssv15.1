from odoo import models, fields, api
from odoo import exceptions
from odoo.exceptions import ValidationError
import logging
from docutils.nodes import field
from vobject.base import readOne
from email.policy import default

log = logging.getLogger(__name__)

class ContactsInherited(models.Model):
    _inherit = 'res.partner'

    use_contact_group = fields.Boolean(compute='_compute_contact_group', default=lambda self: self.env.company.use_contact_group)
    vat_receivable = fields.Many2one('account.account',
                                     string="VAT Receivable",
                                     company_dependent=True,
                                     domain=lambda self: [('deprecated', '=', False)])
    vat_payable = fields.Many2one('account.account',
                                  string="VAT Payable",
                                  company_dependent=True,
                                  domain=lambda self: [('deprecated', '=', False)])
    
    is_vat = fields.Boolean()
    
    contact_group = fields.Many2one('lb_accounting.contact_group', 
                                    string="Contact Group",
                                    company_dependent=True,
                                    domain=lambda self: [('contact_type','=','customer'), ('company_id', '=', self.env.company.id)])
    
    vendor_group = fields.Many2one('lb_accounting.contact_group', 
                                    string="Vendor Group",
                                    company_dependent=True,
                                    domain=lambda self: [('contact_type','=','vendor'), ('company_id', '=', self.env.company.id)])
    
    has_account_group = fields.Boolean(company_dependent=True)
    has_account_vendor_group = fields.Boolean(company_dependent=True)
    
    customer_sequence = fields.Char(company_dependent=True, copy=False)
    customer_id = fields.Char(string="Customer ID", company_dependent=True)
    
    supplier_sequence = fields.Char(company_dependent=True)
    supplier_id = fields.Char(string="Supplier ID", company_dependent=True)

    official_name = fields.Char(string="Official Name")
    
    def _compute_contact_group(self):
        if self.env.company.use_contact_group:
            for partner in self:
                partner.use_contact_group = True
        else:
            for partner in self:
                partner.use_contact_group = False
            
    @api.model
    def create(self, values):        
        create_contact = super(ContactsInherited, self).create(values)
        
        if not create_contact.parent_id:
            
            if create_contact.contact_group:
                log.info("Creating contact group for %s", create_contact.name)
                contact_group_values = create_contact.contact_group.get_sequence(create_contact)
                super(ContactsInherited, create_contact.with_context(contact_group_update=True)).write(contact_group_values)
                
            if create_contact.vendor_group:
                log.info("Creating vendor group for %s", create_contact.name)
                vendor_group_values = create_contact.vendor_group.get_sequence(create_contact)
                super(ContactsInherited, create_contact.with_context(contact_group_update=True)).write(vendor_group_values)
              
        return create_contact
   
    
    def write(self, values):
        write_contact = super(ContactsInherited, self).write(values)
        for record in self:
            if not record.parent_id:
                # in case of assigning a contact group to an existing contact
                if values.get('contact_group') and not self._context.get('contact_group_update'):
                    log.info("Updating contact group for customer: %s", record.id)
                    contact_group = self.env['lb_accounting.contact_group'].browse([values.get('contact_group')])
                    contact_group_values = contact_group.get_sequence(record)
                    super(ContactsInherited, self.with_context(contact_group_update=True)).write(contact_group_values)
                    
                if values.get('vendor_group') and not self._context.get('contact_group_update'):
                    log.info("Updating vendor group for customer: %s", record.id)
                    vendor_group = self.env['lb_accounting.contact_group'].browse([values.get('vendor_group')])
                    vendor_group_values = vendor_group.get_sequence(record)
                    super(ContactsInherited, self.with_context(contact_group_update=True)).write(vendor_group_values)
        
#                 # in case the contact already has a contact group but assigned as supplier or customer
#                 if record.contact_group and record.customer_rank > 0:
#                     values.update(record.contact_group.get_sequence(record))  
#                      
#                 if record.vendor_group and record.supplier_rank > 0:
#                     values.update(record.vendor_group.get_sequence(record))  
                
        return write_contact

    @api.onchange('name')
    def onchange_name_val(self):
        if not self.official_name:
            self.official_name = self.name