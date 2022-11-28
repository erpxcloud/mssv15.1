{
    'name': 'Second and Third Currency',
    'sequence': -102,
    'category': 'Account',
    'depends': [
        'base','account','account_reports',
    ],
    'data': [
        'views/view.xml',
        'views/trial_balance.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'second_third_currency/static/src/js/account_reports.js',
        ],
    }

}
