# -*- coding:utf-8 -*-
{
    'name': 'Lebanese Payroll',
    'category': 'Human Resources',
    'depends': ['hr_payroll'],
    'description': """
Lebanese Payroll Rules.
    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Leaves Management
    * Salary Maj, ONSS, Withholding Tax, Child Allowance, ...
    """,
    'author': "Azkatech",
    'website': "http://www.azka.tech",
    'data': [
#         'data/res_partner.xml',
        'data/hr_payroll_structure_type.xml',
        'data/hr_payroll_structure.xml',
        'data/hr_payslip_input_type.xml',
        'data/hr_salary_rule_category.xml',
        'data/hr_salary_rule.xml',
        'views/hr_payroll_view.xml',
        'views/res_company_views.xml',
        'views/hr_payslip_views.xml',
        'views/report_payslip_templates.xml',
    ],
}
