from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = ['account.account', 'mail.thread']

    name = fields.Char(track_visibility='always')
    code = fields.Char(track_visibility='always')

    user_type_id = fields.Many2one(track_visibility='always')
    non_auth_user_ids = fields.One2many('account.nonauthorized.user', 'account_id', string="Non Authorized Users",
                                        help='Users not allowed to view this account',track_visibility='always')
    #can_view_account = fields.Boolean(compute="_compute_can_view_account")
    
#     @api.depends('non_auth_user_ids.user_id')
#     def _compute_can_view_account(self):
#         for account in self:
#             res = self.env['account.nonauthorized.user'].search([('account_id', '=', account.id), ('user_id', '=', self.env.user.id)])
#             if res:
#                 account.can_view_account = False
#             else:
#                 account.can_view_account = True
                
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        result = super(AccountAccount, self).name_search(name=name, args=args, operator=operator, limit=limit)
        
        for rec in result:
            if rec[1] == "*****":
                result.remove(rec)
            
        return result
    
    def read(self, records):
        res = super(AccountAccount, self).read(records)
        for rec in res:
            non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', rec['id']), ('user_id', '=', self.env.user.id)])
            
            if non_auth and ((non_auth.allow_create_journal and self.env.context.get('item_id') is not False) or \
                             not non_auth.allow_create_journal):
                
                rec['name'] = rec['code'] = "*****"
            
                if('group_id' in rec and rec['group_id'] is not False):
                    rec['group_id'] = "*****"
                
        return res
    
    def name_get(self):
        result = []
        account_names = super(AccountAccount, self).name_get()
        for res in account_names:
            non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', res[0]), ('user_id', '=', self.env.user.id)])

            if non_auth:
                if non_auth.allow_create_journal and self.env.context.get('item_id') is False:
                    result.append((res))
                else:
                    result.append((res[0], "*****"))
            else:
                result.append((res))
                
        return result
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):

        result = super(AccountAccount, self).search_read(domain, fields, offset, limit, order)
        #Added here not in domain because it is a non-stored field
        if not domain == []:
            for rec in result:
                non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', rec.get('id')), ('user_id', '=', self.env.user.id)])
                
                if non_auth and not non_auth.allow_create_journal and self.env.context.get('item_id') is False:
                    result.remove(rec)
            
        return result
