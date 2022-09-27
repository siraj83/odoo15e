odoo.define('pos_blackbox_be.PrintBillButton', function(require) {
    'use strict';

    const PrintBillButton = require('pos_restaurant.PrintBillButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxPrintBillButton = PrintBillButton => class extends PrintBillButton {
        async onClick() {
            let order = this.env.pos.get_order();
            if (this.env.pos.useBlackBoxBe() && order.get_orderlines().length > 0) {
                await this.env.pos.push_pro_forma_order(order);
            }
            super.onClick();
        }
    };

    Registries.Component.extend(PrintBillButton, PosBlackBoxPrintBillButton);

    return PrintBillButton;
 });
