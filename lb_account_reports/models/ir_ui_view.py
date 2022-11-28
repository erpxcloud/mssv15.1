
from odoo import api, models
from odoo.http import request
import time
class View(models.Model):
    
    _inherit = 'ir.ui.view'
    
    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company_id = self.env['res.company'].sudo().browse(company_ids[0])
        
        values.update(
            res_company=company_id,
        )
        
        return super(View, self).render_template(template, values, engine)
