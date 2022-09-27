odoo.define('pos_blackbox_be.ProductScreen', function(require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeProductScreen = ProductScreen => class extends ProductScreen {
        _setValue(val) {
            if (this.currentOrder.get_selected_orderline()) {
                // Do not allow to sent line with a quantity of 5 numbers.
                if (this.env.pos.useBlackBoxBe() && this.state.numpadMode === 'quantity' && val > 9999) {
                    val = 9999;
                }
            }
            super._setValue(val);
        }
    }

    Registries.Component.extend(ProductScreen, PosBlackboxBeProductScreen);

    return ProductScreen;
});
