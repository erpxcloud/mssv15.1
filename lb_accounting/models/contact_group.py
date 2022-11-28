from odoo import models, fields, api
from odoo import exceptions
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

 
class ContactGroup(models.Model):
    _name = 'lb_accounting.contact_group'
    _description = 'Contact Group'
    
    
    def _get_receivable_next_number(self):
        if self.receivable_sequence:
            self.receivable_sequence_next = self.receivable_sequence.number_next_actual
        else:
            self.receivable_sequence_next = 1

    
    def _set_receivable_next_number(self):
        if self.receivable_sequence:
            self.receivable_sequence.sudo().number_next_actual = self.receivable_sequence_next
            
    
    def _get_payable_next_number(self):
        if self.payable_sequence:
            self.payable_sequence_next = self.payable_sequence.number_next_actual
        else:
            self.payable_sequence_next = 1

    
    def _set_payable_next_number(self):
        if self.payable_sequence:
            self.payable_sequence.sudo().number_next_actual = self.payable_sequence_next
            
    name = fields.Char(string="Name", required=True)
    contact_type = fields.Selection([('customer', 'Customer'), ('vendor', 'Vendor')], string="Contact Type")
    sequential = fields.Boolean(string="sequential", default=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    
    receivable_code = fields.Char(string="Receivable Code")
    receivable_sequence = fields.Many2one('ir.sequence', 'Receivable Sequence', readonly=True, copy=False, help="Receivable  sequence.")
    receivable_sequence_next = fields.Integer('Next Receivable Sequence', compute='_get_receivable_next_number', inverse='_set_receivable_next_number', help="Next receivable sequence.") 
   
    receivable_group = fields.Many2one('account.group', string="Receivable Group")
    receivable_vat_group = fields.Many2one('account.group', string="Receivable VAT Group")
    
    receivable_account = fields.Many2one('account.account', 
                                         string="Receivable Account", domain=lambda self: [('reconcile', '=', True), 
                                                                                           ('user_type_id.id', '=', self.env.ref('account.data_account_type_receivable').id), 
                                                                                           ('deprecated', '=', False),
                                                                                           ('company_id', '=', self.env.company.id)])
    
    receivable_vat_account = fields.Many2one('account.account', 
                                             string="Receivable VAT Account", 
                                             domain=lambda self: [('deprecated', '=', False),
                                                                  ('company_id', '=', self.env.company.id)]) 
    payable_code = fields.Char(string="Payable Code")
    payable_sequence = fields.Many2one('ir.sequence', 'Payable Sequence', readonly=True, copy=False, help="Payable sequence.")   
    payable_sequence_next = fields.Integer('Next Payable Sequence', compute='_get_payable_next_number', inverse='_set_payable_next_number', help="Next payable sequence.")
   
    payable_group = fields.Many2one('account.group', string="Payable Group")
    payable_vat_group = fields.Many2one('account.group', string="Payable VAT Group")
    
    payable_account = fields.Many2one('account.account', 
                                      string="Payable Account", 
                                      domain=lambda self: [('reconcile', '=', True), 
                                                           ('user_type_id.id', '=', self.env.ref('account.data_account_type_payable').id), 
                                                           ('deprecated', '=', False), 
                                                           ('company_id', '=', self.env.company.id)])
   
    payable_vat_account = fields.Many2one('account.account', 
                                          string="Payable VAT Account", 
                                          domain=lambda self: [('deprecated', '=', False),
                                                               ('company_id', '=', self.env.company.id)])
    
    
    @api.model
    def create(self, vals):
        rec = super(ContactGroup, self).create(vals)
        if not rec.receivable_sequence and rec.receivable_code:
            rec._create_receivable_sequence()
        if not rec.payable_sequence and rec.payable_code:
            rec._create_payable_sequence()
        return rec
    
    
    def write(self, values):
        rec = super(ContactGroup, self).write(values)
        for record in self:
            if not record.receivable_sequence and record.receivable_code:
                record._create_receivable_sequence()
            if not record.payable_sequence and record.payable_code:
                record._create_payable_sequence()
        return rec
    
    
    def unlink(self):
        """ the group can not be deleted if it has contacts """
        for record in self:
            contact_group = self.env['res.partner'].search([['contact_group', '=', record.id]])
            if contact_group:
                raise ValidationError("You cannot perform this action on a group that contains contacts.")
        return super(ContactGroup, self).unlink()
            
    
    def _create_receivable_sequence(self):
        """ Create a group Receivable sequence """
        self.receivable_sequence = self.env['ir.sequence'].sudo().create({
            'name': self.name + " : Receivable Sequence",
            'implementation': 'no_gap',
            'padding': self.company_id.digits_number,
            'number_increment': 1,
            'company_id': self.company_id.id
        })
     
    
    def _create_payable_sequence(self):
        """ Create a group Payable sequence """
        self.payable_sequence = self.env['ir.sequence'].sudo().create({
            'name': self.name + " : Payable Sequence",
            'implementation': 'no_gap',
            'padding': self.company_id.digits_number,
            'number_increment': 1,
            'company_id': self.company_id.id
        })   
        
    @api.model               
    def account_exists(self, new_code):
        """check if the code is not used """
        record = self.env['account.account'].search([('code', '=', new_code), ('company_id', '=', self.company_id.id)], limit=1)     
        if record:
            return True
        return False
      
    @api.model              
    def get_receivable_account(self, partner):
        """ get the receivable account """
        # if partner does not have customer ID (customer sequence), then assign new account, otherwise keep old account
        vals = {}
        customer_sequence = partner.customer_sequence
        if not customer_sequence:
            log.info("Getting receivable account for partner: %s", partner.id)
            # get next sequence number
            if self.receivable_sequence:
                customer_sequence = self.receivable_sequence._next_do()
                vals['customer_sequence'] = customer_sequence
                
                while customer_sequence:
                    if self.receivable_code:
                        #customer_sequence = self.receivable_code + '-' + customer_sequence
                        vals['customer_id'] =  self.receivable_code + '-' + customer_sequence
                        
                    if self.sequential:
                        
                        if self.receivable_group:
                            # if group is sequential, then generate accounts from the parent groups
                            receivable_account_code = self.receivable_group.code_prefix + customer_sequence
                            receivable_account_exists = self.account_exists(receivable_account_code)
                            
                            if not receivable_account_exists:
                                # create the new account as Receivable Account
                                account_vals = {
                                    'name': partner.name,
                                    'currency_id':  False,
                                    'automatic': True,
                                    'code': receivable_account_code,
                                    'user_type_id':  self.env.ref('account.data_account_type_receivable').id,
                                    'company_id': self.company_id.id,
                                    'group_id': self.receivable_group.id,
                                    'reconcile': True
                                }     
                                vals['property_account_receivable_id'] = self.env['account.account'].create(account_vals).id
                                break
                            else:
                                # if account already exists, get next sequence
                                customer_sequence = self.receivable_sequence._next_do()
                                vals['customer_sequence'] = customer_sequence
                    else:
                        # if group is not sequential, then assign same account as the parent account
                        vals['property_account_receivable_id'] = self.receivable_account.id
                        break
        # if contact is not customer, set receivable account to non usable account
        # condition seems wrong  
        if partner.supplier_rank == 0 and not partner.supplier_sequence and not partner.property_account_payable_id :
            vals['property_account_payable_id'] = partner.company_id and partner.company_id.temporary_payable_account or self.env.company.temporary_payable_account.id
            
        return vals
        
    @api.model              
    def get_vat_receivable_account(self, partner, customer_sequence):
        """ get the vat receivable account """
        vals = {}
        
        if self.receivable_sequence and customer_sequence:
            log.info("Getting vat receivable account for partner: %s", partner.id)
            # if partner does have vat receivable account or having the temp account, then assign new account, otherwise keep old account
            if not partner.vat_receivable or partner.vat_receivable.id == self.company_id.temporary_receivable_account.id:
                if self.sequential:
                    
                    if self.receivable_vat_group:
                        # if group is sequential, then generate the new account from the parent group
                        vat_receivable_account_code = self.receivable_vat_group.code_prefix + customer_sequence
                        vat_receivable_account_exists = self.account_exists(vat_receivable_account_code)
                        # if the account already exists then get next sequence, and generate new account code 
                        while vat_receivable_account_exists:
                            customer_sequence = self.receivable_sequence._next_do()
                            vals['customer_sequence'] = customer_sequence
                            vat_receivable_account_code = self.receivable_vat_group.code_prefix + customer_sequence
                            vat_receivable_account_exists = self.account_exists(vat_receivable_account_code)
                        # create the new account as Current Liabilities
                        account_vals = {
                                'name': partner.name + " - VAT",
                                'currency_id':  False,
                                'code': vat_receivable_account_code,
                                'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
                                'company_id': self.company_id.id,
                                'automatic': True,
                                'group_id': self.receivable_vat_group.id,
                                'reconcile': True
                            }     
                        vals['vat_receivable'] = self.env['account.account'].create(account_vals).id
                else:
                    # if group is not sequential, then assign same account as the parent account
                    vals['vat_receivable'] = self.receivable_vat_account.id
                
        return vals
    
    @api.model              
    def get_payable_account(self, partner):
        """ get the vat payable account """
        # if partner does not have supplier ID (supplier sequence), then assign new account, otherwise keep old account
        vals = {}
        supplier_sequence = partner.supplier_sequence
        if not supplier_sequence:
            log.info("Getting payable account for partner: %s", partner.id)
            # get next sequence number
            if self.payable_sequence:
                supplier_sequence = self.payable_sequence._next_do()
                vals['supplier_sequence'] = supplier_sequence
                
                while supplier_sequence:
                    if self.payable_code:
                        #supplier_sequence = self.payable_code + '-' + supplier_sequence
                        vals['supplier_id'] = self.payable_code + '-' + supplier_sequence
                        
                    if self.sequential:
                        
                        if self.payable_group:
                            # if group is sequential, then generate accounts from the parent groups
                            payable_account_code = self.payable_group.code_prefix + supplier_sequence
                            payable_account_exists = self.account_exists(payable_account_code)
                            
                            if not payable_account_exists:
                                # create the new account as Payable Account
                                account_vals = {
                                    'name': partner.name,
                                    'currency_id':  False,
                                    'automatic': True,
                                    'code': payable_account_code,
                                    'user_type_id': self.env.ref('account.data_account_type_payable').id,
                                    'company_id': self.company_id.id,
                                    'group_id': self.payable_group.id,
                                    'reconcile': True
                                }     
                                vals['property_account_payable_id'] = self.env['account.account'].create(account_vals).id
                                break
                            else:
                                # if account already exists, get next sequence
                                supplier_sequence = self.payable_sequence._next_do()
                                vals['supplier_sequence'] = supplier_sequence
                    else:
                        # if group is not sequential, then assign same account as the parent account
                        vals['property_account_payable_id'] = self.payable_account.id
                        break
                    
        # if contact is not customer, set receivable account to non usable account  
        if partner.customer_rank == 0 and not partner.customer_sequence and not partner.property_account_receivable_id :
            #set payable?
            vals['property_account_receivable_id'] = partner.company_id and partner.company_id.temporary_receivable_account or self.env.company.temporary_receivable_account.id
          
        return vals
      
    @api.model              
    def get_vat_payable_account(self, partner, supplier_sequence):
        """ get the vat payable account """
        vals = {}
        if self.payable_sequence and supplier_sequence:
            log.info("Getting vat payable account for partner: %s", partner.id)
            # if partner does vat payable account or have temp account, then assign new account, otherwise keep old account
            if not partner.vat_payable or partner.vat_payable.id == self.company_id.temporary_payable_account.id:
                if self.sequential:

                    if self.payable_vat_group:
                        # if group is sequential, then generate the new account from the parent group
                        vat_payable_account_code = self.payable_vat_group.code_prefix + supplier_sequence
                        vat_payable_account_exists = self.account_exists(vat_payable_account_code)
                        # if the account already exists then get next sequence, and generate new account code
                        while vat_payable_account_exists:
                            supplier_sequence = self.payable_sequence._next_do()
                            vals['supplier_sequence'] = supplier_sequence
                            vat_payable_account_code = self.payable_vat_group.code_prefix + supplier_sequence
                            vat_payable_account_exists = self.account_exists(vat_payable_account_code)
                        # create the new account as Current Liabilities
                        account_vals = {
                                'name': partner.name + " - VAT",
                                'currency_id':  False,
                                'automatic': True,
                                'code': vat_payable_account_code,
                                'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
                                'company_id': self.company_id.id,
                                'group_id': self.payable_vat_group.id,
                                'reconcile': True
                            }     
                        vals['vat_payable'] = self.env['account.account'].create(account_vals).id
                else:
                    # if group is not sequential, then assign same account as the parent account
                    vals['vat_payable'] = self.payable_vat_account.id
                
        return vals
    

    @api.model              
    def get_sequence(self, partner):
        vals = {}
        
        if partner.contact_group:
            vals['has_account_group'] = True
             
            customer_receivable_vals = self.get_receivable_account(partner)
            customer_receivable_vat_vals = self.get_vat_receivable_account(partner, customer_receivable_vals.get('customer_sequence'))
            
            vals.update(customer_receivable_vals)
            vals.update(customer_receivable_vat_vals)
            
            
        if partner.vendor_group:
            vals['has_account_vendor_group'] = True
            
            supplier_payable_vals = self.get_payable_account(partner)
            supplier_payable_vat_vals = self.get_vat_payable_account(partner, supplier_payable_vals.get('supplier_sequence'))
            
            vals.update(supplier_payable_vals)
            vals.update(supplier_payable_vat_vals)
           
        # get receivable account 
#         if partner.customer_rank > 0:
#             
#             
#         # get payable account
#         if partner.supplier_rank > 0:
#             
#             
        return vals