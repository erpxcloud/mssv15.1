# -*- coding:utf-8 -*-
{
    'name': 'Lebanese Payroll With Accounting',
    'category': 'Accounting',
    'depends': ['base',
#                 'lb_hr_payroll',
#                 'hr_payroll_account'
               ],
    'description': """
Lebanese Payroll With Accounting.
    """,
    'author': "Azkatech",
    'website': "http://www.azka.tech",
    'data': [
#         'data/account.account.csv',
#         'data/hr.salary.rule.csv',

        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/hr_payroll_account_views.xml',                
    ],
}
