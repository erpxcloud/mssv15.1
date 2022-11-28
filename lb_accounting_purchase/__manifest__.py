# -*- coding: utf-8 -*-
{
    'name': "Lebanese Accounting Purchase",

    'summary': """
        Lebanese Accounting Purchase
    """,

    'description': """
        Lebanese Accounting Purchase
    """,

    'author': "Azkatech",
    'website': "http://www.azka.tech",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['lb_accounting', 'purchase'],

    # always loaded
    'data': [
        'report/letter_head_report.xml',
        
        'views/purchase_view.xml',
        
        'views/purchase_order_template.xml',
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
