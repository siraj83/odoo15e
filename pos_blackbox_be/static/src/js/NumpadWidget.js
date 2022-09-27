odoo.define('pos_blackbox_be.NumpadWidget', function(require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxNumpadWidget = NumpadWidget => class extends NumpadWidget {
        get hasPriceControlRights() {
            if (this.env.pos.useBlackBoxBe()) {
                return false;
            } else {
                return super.hasPriceControlRights;
            }
        }
    };

    Registries.Component.extend(NumpadWidget, PosBlackBoxNumpadWidget);

    return NumpadWidget;
 });
