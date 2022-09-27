odoo.define('pos_blackbox_be.PosBlackBoxBeSaleDetailsButton', function(require) {
    'use strict';

    const SaleDetailsButton = require('point_of_sale.SaleDetailsButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeSaleDetailsButton = SaleDetailsButton => class extends SaleDetailsButton {
        async onClick() {
            if(this.env.pos.useBlackBoxBe()) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t("Fiscal Data Module Restriction"),
                    body: this.env._t("You are not allowed to print a sales report details when using the fiscal data module."),
                });
                return;
            }
            return super.onClick();
        }
    }
    Registries.Component.extend(SaleDetailsButton, PosBlackboxBeSaleDetailsButton);

    return PosBlackboxBeSaleDetailsButton;
});
