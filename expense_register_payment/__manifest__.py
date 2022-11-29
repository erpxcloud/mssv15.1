
{
    'name': 'Expense Register Payment ',
    'version': '2.0',

    'depends': ['base','account', 'account_reports', 'hr_expense'],
    'sequence': "-400",
    'data': [
        'views/expense_payment_payroll.xml',

    ],

    'application': True,
    'auto install': False,
    'license': 'LGPL-3',
}
