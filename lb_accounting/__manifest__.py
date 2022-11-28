# -*- coding: utf-8 -*-
{
    'name': "Lebanese Accounting",

    'summary': """
        Lebanese Accounting
    """,

    'description': """
        Lebanese Accounting
    """,

    'author': "Azkatech",
    'website': "http://www.azka.tech",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.0.0.0.6',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'account_accountant', 'contacts', 'account_check_printing'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/lb_accounting_security.xml',
        
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/closing_voucher.xml',
        'views/account_move.xml',
        'views/tax_views.xml',
        'views/report_templates.xml',
        'views/res_config_settings_views.xml',
        
        'views/account_invoice.xml',
        
        
        'views/report_invoice.xml',

        
        'views/report_journal.xml',
        'views/report_payment_receipt_templates.xml',
        
                
        'views/diff_exchange_voucher.xml',
        'wizard/wizard_diff_exchange_voucher_view.xml', 

        'report/account_journal_report.xml',
        'report/account_invoice_report.xml',
        'report/letter_head_report.xml',

        'wizard/wizard_closing_voucher.xml',

        'data/report_layout.xml', 
        'data/decimal_precision_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'qweb': [
    ],
    "css": [],
    #Whether a user should be able to install the module from the Web UI or not.
    'installable': True,
    #If True, this module will automatically be installed if all of its dependencies are installed.
    'auto_install ': False,
    #If False then it will be a technical module that doesn't show on the dashboard
    'application': True,
    #First item in the home list of apps
    'sequence': 1,
}
