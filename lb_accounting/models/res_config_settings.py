from odoo import api, fields, models, _
import logging
import string
import re

log = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    temporary_receivable_account = fields.Many2one('account.account', related='company_id.temporary_receivable_account', readonly=False,
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_receivable').id), ('deprecated', '=', False)], 
        string="Receivable Account",
        help="Account is used as a temporary receivable account.")
    
    temporary_payable_account = fields.Many2one('account.account', related='company_id.temporary_payable_account', readonly=False,
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_payable').id), ('deprecated', '=', False)], 
        string="Payable Account",
        help="Account is used as a temporary payable account.")

    company_second_currency = fields.Many2one(related="company_id.second_currency_id")
    company_third_currency = fields.Many2one(related="company_id.third_currency_id")
    
    say_of_default_currency = fields.Many2one(related="company_id.say_of_default_currency", readonly=False)
    tax_say_of_default_currency = fields.Many2one(related="company_id.tax_say_of_default_currency", readonly=False)
    
    show_say_of_default_currency = fields.Boolean(related="company_id.show_say_of_default_currency", readonly=False, string='Display counter value in local currency for invoice, sales order, purchase order', help="Display say-of on printing for invoice, sales order in default currency")
    show_tax_say_of_default_currency = fields.Boolean(related="company_id.show_tax_say_of_default_currency", readonly=False, string='Display tax counter value in local currency for invoice, sales order, purchase order', help="Display tax say-of on printing for invoice, sales order in default currency")
    use_contact_group = fields.Boolean(related="company_id.use_contact_group", readonly=False, store=True)
    external_letter_head_report_layout_id = fields.Many2one(related="company_id.external_letter_head_report_layout_id", readonly=False)
    
    group_show_say_of_default_currency = fields.Boolean('Display counter value in local currency for invoice, sales order, purchase order', implied_group='lb_accounting.group_show_say_of_default_currency',
        help="Display say-of on printing for invoice, sales order in default currency")
    group_show_tax_say_of_default_currency = fields.Boolean('Display tax counter value in local currency for invoice, sales order, purchase order', implied_group='lb_accounting.group_show_tax_say_of_default_currency',
        help="Display tax say-of on printing for invoice, sales order in default currency")
    
    def execute(self):
        res = super(ResConfigSettings, self).execute()
        if self.use_contact_group:
            modules = self.env['ir.module.module'].sudo().search([('name', '=', 'hide_contact_group'),('state', '=', 'installed')])
            modules_show = self.env['ir.module.module'].sudo().search([('name', '=', 'show_contact_group')])
            companies = self.env['res.company'].sudo().search([])
            for company in companies:
                company.sudo().use_contact_group = True
            for rec in self:
                rec.use_contact_group = True
            if modules:
                modules.button_immediate_uninstall()
            if modules_show:
                modules_show.button_immediate_install()
            
        else:
            modules = self.env['ir.module.module'].sudo().search([('name', '=', 'hide_contact_group')])
            modules_show = self.env['ir.module.module'].sudo().search([('name', '=', 'show_contact_group'),('state', '=', 'installed')])
            companies = self.env['res.company'].sudo().search([])
            for company in companies:
                company.sudo().use_contact_group = False
            for rec in self:
                rec.use_contact_group = False
            if modules_show:
                modules_show.button_immediate_uninstall()
            if modules:
                modules.button_immediate_install()
            
                
                
    def edit_letter_external_header(self):
        if not self.external_letter_head_report_layout_id:
            return False
        return self._prepare_report_view_action(self.external_letter_head_report_layout_id.key)
    
    
    def change_report_letter_head_template(self):
        self.ensure_one()
        template = self.env.ref('lb_accounting.view_company_letter_head_template_form')
        return {
            'name': _('Choose Your Letter Head Layout'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.env.company.id,
            'res_model': 'res.company',
            'views': [(template.id, 'form')],
            'view_id': template.id,
            'target': 'new',
        }