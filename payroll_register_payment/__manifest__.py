
{
    'name': 'Payroll Register Payment ',
    'version': '2.0',

    'depends': ['account','hr_payroll'],
    'sequence': "-400",
    'data': [
        'views/register_payment_payroll.xml',

    ],

    'application': True,
    'auto install': False,
    'license': 'LGPL-3',
}
