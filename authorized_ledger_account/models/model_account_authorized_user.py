from odoo import models, fields


class AccountNonAuthUser(models.Model):
    _name = 'account.nonauthorized.user'
    _description = 'account.nonauthorized.user'
    
    user_id = fields.Many2one('res.users', string="User", required=True,  domain=lambda self: [('groups_id', 'in', [self.env.ref('account.group_account_user').id, #Accountant
                                                                                                                    self.env.ref('account.group_account_manager').id, #Advisor
                                                                                                                    self.env.ref('account.group_account_invoice').id #Billing
                                                                                                                    ])])
    
    allow_create_journal = fields.Boolean(string="Allow Create Journal Item", help="User is allowed to create a journal item")

    account_id = fields.Many2one('account.account', string="Account", required=True)

    _sql_constraints = [
        ('unique_non_auth_user_account', 'unique(user_id, account_id)',
         'The combination of user and account must be unique!'),
    ]

