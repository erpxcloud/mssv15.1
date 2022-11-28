# -*- coding:utf-8 -*-
from odoo import api, fields, models, _


class Employee(models.Model):
    _inherit = "hr.employee"
    
    employee_account = fields.One2many("hr.employee.account", "employee_id")
    
class EmployeeAccount(models.Model):
    _name = "hr.employee.account"
    _description = "Employee Accounts"
    
    employee_id = fields.Many2one("hr.employee")
    salary_rule = fields.Many2one("hr.salary.rule")
    credit_account = fields.Many2one("account.account")
    debit_account = fields.Many2one("account.account")    