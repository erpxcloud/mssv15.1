# -*- coding: utf-8 -*-
{
    'name' : 'Lebanese Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting',
    'author': "Azkatech",
    'version': "13.0.0.0.5",
    'website': "http://www.azka.tech",
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant', 'account_reports', 'lb_accounting'],
    'data': [
        'views/report_financial.xml',
        'views/search_template_view.xml',
        'views/res_partner_view.xml',
        'views/res_config_settings.xml',
        'views/account_move_line_views.xml',
        'wizard/amount_currency_wizard.xml'
    ],
    'qweb': [
    ],
    'auto_install': True,
    'installable': True,
}
