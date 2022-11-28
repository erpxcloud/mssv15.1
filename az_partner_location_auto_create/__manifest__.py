{
    'name': 'MSS',
    'version': '13.0.0.1.0',
    'author': 'Azkatech',
    'category': 'Warehouse',
    'license': 'AGPL-3',
    'complexity': 'normal',
    'images': [],
    'website': 'http://www.azka.tech',
    'depends': [
        'sale_stock',
    ],
    'demo': [],
    'data': [
        "security/ir.model.access.csv",
        'views/slae_order_type_view.xml',
        'views/stock_picking_view.xml',
        'views/sale_order_views.xml',
        'security/security.xml',
        'wizard/customer_foc_confirm.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        
    ],
    'test': [],
    'auto_install': False,
    'installable': True,
}
