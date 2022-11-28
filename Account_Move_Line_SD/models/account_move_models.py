from odoo import _, api, fields, models

class AccountMoveL(models.Model):
    _inherit = 'account.move.line'

    second_debit = fields.Float(string='Second Debit',  readonly=False)
    second_credit = fields.Float(string='Second Credit',  readonly=False)
    second_balance = fields.Float(string='Second Balance',  readonly=False)
    third_debit = fields.Float(string='Third Debit',  readonly=False)
    third_credit = fields.Float(string='Third Credit',  readonly=False)
    third_balance = fields.Float(string='Third Balance',  readonly=False)
    company_second_currency_id = fields.Many2one("res.currency", string=' Second Currency', readonly=False)
    company_third_currency_id = fields.Many2one("res.currency", string=' Second Currency', readonly=False)
