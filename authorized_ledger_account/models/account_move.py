from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import datetime

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        
        if(self.invoice_date is not False):
            currentYear = datetime.now().year
            invoicedate = datetime.strptime(str(self.invoice_date), "%Y-%m-%d").strftime("%Y")
            if(int(invoicedate) != int(currentYear)):
                return {
                    'warning': {
                        'title': 'Invoice Date warning',
                        'message': "Invoice date year is different from current"
                    }
                }

    @api.model
    def create(self, vals):
        move = super(AccountMove, self).create(vals)
        if move.type == "out_refund" and self.env.user.has_group('authorized_ledger_account.group_creditnote'):
            raise UserError("You don't have the permission to create credit note!")

        return move

    def write(self, vals):
        for move in self:
            if move.type == "out_refund" and self.env.user.has_group('authorized_ledger_account.group_creditnote'):
                raise UserError("You don't have the permission to edit credit note!")
        return super(AccountMove, self).write(vals)

    def unlink(self):
        for move in self:
            if move.type == "out_refund" and self.env.user.has_group('authorized_ledger_account.group_creditnote'):
                raise UserError("You don't have the permission to delete credit note!")
        return super(AccountMove, self).unlink()