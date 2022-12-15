{
    'name': "Payment with Currency",

    'author': "erp cloud llc",
    'website': "https://erpxcloud.com",
    'version': '13.0.0.0.4',
    'category': '',

    'depends': ['account_accountant', 'account_batch_payment','hr','base'],

    'data': [
        'views/account_payment.xml',
        'views/account_payment_wizard.xml',
        'views/account_batch_payment_views.xml',
        'data/updating_journal_items.xml'
    ],
}
