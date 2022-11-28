from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from lib2to3.fixes.fix_input import context

log = logging.getLogger(__name__)


class CompanyInherited(models.Model):
    _inherit = 'res.company'

    digits_number = fields.Integer(string="Contact Account Digits", help="Specify the number of the contact account.", required=True, default='4')

    temporary_receivable_account = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_receivable').id), ('deprecated', '=', False)], 
        string="Temporary Receivable account",
        help="Account is used as a temporary receivable account.")
    
    temporary_payable_account = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_payable').id), ('deprecated', '=', False)], 
        string="Temporary Payable account",
        help="Account is used as a temporary payable account.")
    
    second_currency_id = fields.Many2one('res.currency', string="Second Currency")
    third_currency_id = fields.Many2one('res.currency', string="Third Currency")
    
    checks_transit_journal_id = fields.Many2one('account.journal', string='Post-dated Checks Journal',  help="The accounting journal where post-dated checks will be registered", domain=[('type', '=', 'bank')])
    
    capital = fields.Monetary(default=0.0, currency_field='capital_currency_id')
    capital_currency_id = fields.Many2one('res.currency', string="Capital Currency", help='Utility field to express capital currency')
    
    commercial_reg_label = fields.Char(string="Commercial Registry Label")
    vat_label = fields.Char()
    capital_label = fields.Char()
    use_contact_group = fields.Boolean(default = False)
    fax = fields.Char()

    footer_logo = fields.Binary(string="Footer Logo")
    external_letter_head_report_layout_id = fields.Many2one('ir.ui.view', 'Letter Head Template')
    
    say_of_default_currency = fields.Many2one('res.currency', string="Select Say-of Local Currency", default=lambda self: self.env.company.currency_id.id)
    tax_say_of_default_currency = fields.Many2one('res.currency', string="Select Tax Say-of Local Currency", default=lambda self: self.env.company.currency_id.id)
    show_say_of_default_currency = fields.Boolean()
    show_tax_say_of_default_currency = fields.Boolean()
    
    @api.constrains('digits_number')
    def _check_digits_number(self):
        
        for record in self:
            if record.digits_number <= 0:
                raise ValidationError("Number of digits should be greater than 0")

