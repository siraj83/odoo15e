odoo.define('pos_blackbox_be.ReprintReceiptButton', function(require) {
    'use strict';

    const ReprintReceiptButton = require('point_of_sale.ReprintReceiptButton');
    const Registries = require('point_of_sale.Registries');
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const { useContext } = owl.hooks;
    const contexts = require('point_of_sale.PosContext');
    const { Gui } = require('point_of_sale.Gui');
    var core    = require('web.core');
    var _t      = core._t;

    const PosBlackboxBeReprintReceiptButton = ReprintReceiptButton =>
        class extends ReprintReceiptButton {
            constructor() {
                super(...arguments);
                this.orderManagementContext = useContext(contexts.orderManagement);
            }

            async _onClick() {
                if(this.env.pos.useBlackBoxBe()) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t("Fiscal Data Module Restriction"),
                        body: this.env._t("You are not allowed to reprint a ticket when using the fiscal data module."),
                    });
                    return;
                }
                super._onClick();
            }
        };

    Registries.Component.extend(ReprintReceiptButton, PosBlackboxBeReprintReceiptButton);

    return PosBlackboxBeReprintReceiptButton;
});
