# -*- coding: utf-8 -*-
{
    'name': 'Lebanon - Accounting Localization',
    'author': "Azkatech",
    'website': "http://www.azka.tech",
    'category': 'Localization',
     'version': '0.1',
    'description': """
Lebanese accounting chart and localization.
=======================================================

    """,
    'depends': ['base', 'account', 'lb_accounting'],
    'data': [
             'data/account_data.xml',
             'data/l10n_lb_chart_data.xml',
             'data/account.group.csv',
             'data/account.account.template.csv',
             'data/account_tax_template_data.xml',
             'data/l10n_lb_chart_post_data.xml',
             'data/account_chart_template_data.xml',
    ],
    'auto_install ': False,
}
