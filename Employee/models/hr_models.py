from odoo import _, api, fields, models

class hr_models(models.Model):
    _inherit = 'hr.employee'

    dependent_children = fields.Integer('Dependent children')
    dependent_juniors = fields.Integer('Dependent juniors')
    dependent_seniors = fields.Integer('Dependent Seniors')