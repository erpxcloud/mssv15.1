# -*- coding: utf-8 -*-
# from odoo import http


# class AzCustomSoDivision(http.Controller):
#     @http.route('/az_custom_so_division/az_custom_so_division/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/az_custom_so_division/az_custom_so_division/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('az_custom_so_division.listing', {
#             'root': '/az_custom_so_division/az_custom_so_division',
#             'objects': http.request.env['az_custom_so_division.az_custom_so_division'].search([]),
#         })

#     @http.route('/az_custom_so_division/az_custom_so_division/objects/<model("az_custom_so_division.az_custom_so_division"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('az_custom_so_division.object', {
#             'object': obj
#         })
