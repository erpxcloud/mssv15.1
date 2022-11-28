from odoo import api, fields, models, _

class AccountAnalyticGroup(models.Model):
    _inherit = 'account.analytic.group'

    sequence_no = fields.Char(string='Sequence No.', required=True, copy=False, readonly=True,
        index=True, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        print(vals)
        if vals.get('sequence_no', _('New')) == _('New'):
            if 'company_id' in vals:
                code = self.env['res.company'].search([('id', '=', vals['company_id'])]).sequence
                vals['sequence_no'] = str(code) + self.env['ir.sequence'].next_by_code(
                    'analytic.group.sequence') or _('New')
            else:
                vals['sequence_no'] = self.env['ir.sequence'].next_by_code('analytic.group.sequence') or _('New')
        result = super(AccountAnalyticGroup, self).create(vals)
        return result