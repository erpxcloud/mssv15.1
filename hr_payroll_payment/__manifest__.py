# Part of Hibou Suite Professional. See LICENSE_PROFESSIONAL file for full copyright and licensing details.

{
    'name': 'Payroll Payments',
    'author': 'Hibou Corp. <hello@hibou.io>',
    'category': 'Human Resources',
    'sequence': 95,
    'summary': 'Register payments for Payroll Payslips',
    'description': """
    """,
    'depends': [
        'hr_payroll_account',
        'account_batch_payment',
    ],
    'data': [
        #'wizard/hr_payroll_register_payment_views.xml',
        'views/account_views.xml',
        'views/hr_payslip_views.xml',
    ],

}
