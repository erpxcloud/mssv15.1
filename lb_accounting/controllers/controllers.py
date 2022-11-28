# -*- coding: utf-8 -*-
from odoo import http

# class LbAccounting(http.Controller):
#     @http.route('/lb_accounting/lb_accounting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lb_accounting/lb_accounting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('lb_accounting.listing', {
#             'root': '/lb_accounting/lb_accounting',
#             'objects': http.request.env['lb_accounting.lb_accounting'].search([]),
#         })

#     @http.route('/lb_accounting/lb_accounting/objects/<model("lb_accounting.lb_accounting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lb_accounting.object', {
#             'object': obj
#         })