# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Registered Cash Register',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Implements the registered cash system, adhering to guidelines by FPS Finance.',
    'description': """
Belgian Registered Cash Register
================================

This module turns the Point Of Sale module into a certified Belgian cash register.

More info:
  * http://www.systemedecaisseenregistreuse.be/
  * http://www.geregistreerdkassasysteem.be/

Legal
-----
**The use of pos_blackbox_be sources is only certified on odoo.com SaaS platform
for version 15.0.** Contact Odoo SA before installing pos_blackbox_be module.

An obfuscated and certified version of the pos_blackbox_be may be provided on
requests for on-premise installations.
No modified version is certified and supported by Odoo SA.
    """,
    'depends': ['pos_restaurant_iot', 'l10n_be', 'web_enterprise', 'pos_hr'],
    'data': [
        'data/pos_blackbox_be_data.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/pos_blackbox_be_views.xml',
        'views/pos_daily_reports.xml',
        'views/pos_order_views.xml',
        'views/pro_forma_views.xml',
        'views/res_users_views.xml'
    ],
    'demo': [
        'data/pos_blackbox_be_demo.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_blackbox_be/static/src/js/pos_blackbox_be.js',
            'pos_blackbox_be/static/src/js/WorkInButton.js',
            'pos_blackbox_be/static/src/js/OrderReceipt.js',
            'pos_blackbox_be/static/src/js/CashMovePopup.js',
            'pos_blackbox_be/static/src/js/ClosePosPopup.js',
            'pos_blackbox_be/static/src/js/HeaderLockButton.js',
            'pos_blackbox_be/static/src/js/NumpadWidget.js',
            'pos_blackbox_be/static/src/js/ReprintButton.js',
            'pos_blackbox_be/static/src/js/SaleDetailsButton.js',
            'pos_blackbox_be/static/src/js/ProductScreen.js',
            'pos_blackbox_be/static/src/js/PrintBillButton.js',
            'pos_blackbox_be/static/src/js/SplitBillScreen.js',
            'pos_blackbox_be/static/src/js/TicketScreen.js',
        ],
        'web.assets_qweb': [
            'pos_blackbox_be/static/src/xml/**/*',
        ],
    },
    'installable': False,
    'license': 'OEEL-1',
}
