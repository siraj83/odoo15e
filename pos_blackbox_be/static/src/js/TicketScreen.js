odoo.define('pos_blackbox_be.TicketScreen', function(require) {
    "use strict";

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    var core    = require('web.core');
    var _t      = core._t;

    const PosBlackboxBeTicketScreen = TicketScreen => class extends TicketScreen {
        _onUpdateSelectedOrderline({ detail }) {
            const buffer = detail.buffer;
            const order = this.getSelectedSyncedOrder();
            if (!order) return NumberBuffer.reset();

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.models.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return NumberBuffer.reset();
            if (this.env.pos.useBlackBoxBe()) {
                if(orderline.product.id === this.env.pos.work_out_product.id || orderline.product.id === this.env.pos.work_in_product.id) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Fiscal Error'),
                        body: this.env._t("You are not allowed to refund this product")
                    });
                    return;
                }
            }
            super._onUpdateSelectedOrderline({ detail });
        }
    };

    Registries.Component.extend(TicketScreen, PosBlackboxBeTicketScreen);

    return PosBlackboxBeTicketScreen;
});
