{
    'name': "Authorized Ledger Accounts",

    'summary': """
    Mask certain ledger accounts for non authorized users.
    """,

    'description': """
      A user may not be authorized to view certain Ledger accounts in the accounting reports. Therefore, these ledger accounts and the auxiliary accounts used with them must be hidden in the main accounting reports.
    """,

    'author': "Azkatech SAL",
    'website': "http://www.azka.tech",

    'category': "Accounting",
    'version': '1.0.0',
    'license': "AGPL-3",

    'support': "support+odoo@azka.tech",

    'price': 0,

    'currency': "USD",

    'depends': ['base', 'account', 'account_reports'],

    
    'data': [
        'views/view_account_account.xml',
#         'views/report_journal.xml',
        'views/search_template_view.xml',
        'views/account_analytic_group.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
    ],
}
