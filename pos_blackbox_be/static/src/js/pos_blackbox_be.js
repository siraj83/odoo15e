/* global Sha1 */
odoo.define('pos_blackbox_be.pos_blackbox_be', function (require) {
    var models = require('point_of_sale.models');
    const { Gui } = require('point_of_sale.Gui');
    var core    = require('web.core');
    var Class = require('web.Class');
    var devices = require('point_of_sale.devices');
    var _t      = core._t;

    var posModelSuper = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        useBlackBoxBe: function() {
            return this.config.iface_fiscal_data_module;
        },
        check_if_user_clocked: function() {
            if(this.env.pos.config.module_pos_hr)
                return this.pos_session.employees_clocked_ids.find(elem => elem === this.get_cashier().id);
            else
                return this.pos_session.users_clocked_ids.find(elem => elem === this.user.id);
        },
        disallowLineQuantityChange() {
            let result = posModelSuper.disallowLineQuantityChange.apply(this, arguments);
            return this.useBlackBoxBe() || result;
        },
        push_pro_forma_order: async function(order) {
            order.receipt_type = "PS";
            await this.env.pos.push_single_order(order);
            order.receipt_type = false;
        },
        push_single_order: async function (order, opts) {
            if (this.useBlackBoxBe() && order) {
                if(!order.receipt_type) {
                    order.receipt_type = order.get_total_with_tax() >= 0 ? 'NS' : 'NR';
                }
                try {
                    order.blackbox_tax_category_a = order.get_specific_tax(21);
                    order.blackbox_tax_category_b = order.get_specific_tax(12);
                    order.blackbox_tax_category_c = order.get_specific_tax(6);
                    order.blackbox_tax_category_d = order.get_specific_tax(0);
                    let data = await this.push_order_to_blackbox(order);
                    if(data.value.error && data.value.error.errorCode != "000000")
                        throw data.value.error;
                    this.set_data_for_push_order_from_blackbox(order, data);
                    this.last_order = order.receipt_type === 'NS'? order: false;
                    return await posModelSuper.push_single_order.apply(this, [order, opts]);
                } catch(err) {
                    throw {
                        code: 701,
                        error: err,
                    }
               }
            } else {
                return await posModelSuper.push_orders.apply(this, arguments);
            }
        },
        push_order_to_blackbox: async function(order) {
            var fdm = this.iot_device_proxies.fiscal_data_module;
            var data = {
                'date': moment(order.creation_date).format("YYYYMMDD"),
                'ticket_time': moment(order.creation_date).format("HHmmss"),
                'insz_or_bis_number': this.config.module_pos_hr ? this.get_cashier().insz_or_bis_number : this.user.insz_or_bis_number,
                'ticket_number': order.sequence_number.toString(),
                'type': order.receipt_type,
                'receipt_total': Math.abs(order.get_total_with_tax()).toFixed(2).toString().replace(".",""),
                'vat1': order.blackbox_tax_category_a? Math.abs(order.blackbox_tax_category_a).toFixed(2).replace(".","") : "",
                'vat2': order.blackbox_tax_category_b? Math.abs(order.blackbox_tax_category_b).toFixed(2).replace(".","") : "",
                'vat3': order.blackbox_tax_category_c? Math.abs(order.blackbox_tax_category_c).toFixed(2).replace(".","") : "",
                'vat4': order.blackbox_tax_category_d? Math.abs(order.blackbox_tax_category_d).toFixed(2).replace(".","") : "",
                'plu': order.get_plu(),
                'clock': order.clock? order.clock : false,
            }
            return new Promise(async (resolve, reject) => {
                fdm.add_listener(data => {
                    fdm.remove_listener();
                    if(data.status.status === "connected")
                        resolve(data);
                    else
                        reject(data);
                });
                await fdm.action({
                    action: 'registerReceipt',
                    high_level_message: data,
                });
            });
        },
        set_data_for_push_order_from_blackbox: function(order, data) {
            order.blackbox_signature = data.value.signature;
            order.blackbox_unit_id = data.value.vsc;
            order.blackbox_pos_production_id = this.version.server_serie;
            order.blackbox_plu_hash = order.get_plu();
            order.blackbox_vsc_identification_number = data.value.vsc;
            order.blackbox_unique_fdm_production_number = data.value.fdm_number;
            order.blackbox_ticket_counter = data.value.ticket_counter;
            order.blackbox_total_ticket_counter = data.value.total_ticket_counter;
            order.blackbox_ticket_counters = order.receipt_type + " " + data.value.ticket_counter + "/" + data.value.total_ticket_counter;
            order.blackbox_time = data.value.time.replace(/(\d{2})(\d{2})(\d{2})/g, '$1:$2:$3');
            order.blackbox_date = data.value.date.replace(/(\d{4})(\d{2})(\d{2})/g, '$3-$2-$1');
        },
        push_and_invoice_order: async function (order) {
            if(this.useBlackBoxBe()) {
                try {
                    order.receipt_type = order.get_total_with_tax() >= 0 ? 'NS' : 'NR';
                    let data = await this.push_order_to_blackbox(order);
                    this.set_data_for_push_order_from_blackbox(order, data);
                } catch (err) {
                    return Promise.reject({code:400, message:'Blackbox error', data:{}, status: err.status});
                }
            }
            return posModelSuper.push_and_invoice_order.apply(this, [order]);
        },
        after_load_server_data: function () {
            if (this.useBlackBoxBe() && !this.work_in_product) {
                let products = this.db.product_by_id;
                for (let id in products) {
                    if (products[id].display_name === 'WORK IN') {
                        this.work_in_product = products[id];
                    } else if (products[id].display_name === 'WORK OUT') {
                        this.work_out_product = products[id];
                    }
                }
            }

            return posModelSuper.after_load_server_data.apply(this, arguments);
        },
        sync_from_server: function(table, table_orders, order_ids) {
            posModelSuper.sync_from_server.apply(this, arguments);
            if(this.useBlackBoxBe() && !table) {
                table_orders.forEach(order => {
                    if(order.orderlines.length > 0)
                        this.push_pro_forma_order(order);
                });
            }
        },
        transfer_order_to_different_table: function () {
            if(this.useBlackBoxBe())
                this.push_pro_forma_order(this.get_order());
            posModelSuper.transfer_order_to_different_table.apply(this, arguments);
        },
    });


    var order_model_super = models.Order.prototype;
    models.Order = models.Order.extend({
        get_specific_tax: function(amount) {
            var tax = this.get_tax_details().find(tax => tax.tax.amount === amount);
            if(tax)
                return tax.amount;
            return false;
        },
        add_product: async function (product, options) {
            if (this.pos.useBlackBoxBe() && product.taxes_id.length === 0) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("Product has no tax associated with it."),
                });
            } else if(this.pos.useBlackBoxBe() && !this.pos.check_if_user_clocked() && product !== this.pos.work_in_product) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("User must be clocked in."),
                });
            } else if (this.pos.useBlackBoxBe() && !this.pos.taxes_by_id[product.taxes_id[0]].identification_letter) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("Product has an invalid tax amount. Only 21%, 12%, 6% and 0% are allowed."),
                });
            } else if (this.pos.useBlackBoxBe() && product.id === this.pos.work_in_product.id && !options.force) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("This product is not allowed to be sold"),
                });
            } else if (this.pos.useBlackBoxBe() && product.id === this.pos.work_out_product.id && !options.force) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("This product is not allowed to be sold"),
                });
            } else {
                return order_model_super.add_product.apply(this, arguments);
            }
        },
        wait_for_push_order: function () {
            var result = order_model_super.wait_for_push_order.apply(this,arguments);
            return Boolean(this.pos.useBlackBoxBe() || result);
        },
        export_as_JSON: function () {
            var json = order_model_super.export_as_JSON.bind(this)();

            if(this.pos.useBlackBoxBe()) {
                json = _.extend(json, {
                    'receipt_type': this.receipt_type,
                    'blackbox_unit_id': this.blackbox_unit_id,
                    'blackbox_pos_receipt_time': this.blackbox_pos_receipt_time,
                    'blackbox_ticket_counters': this.blackbox_ticket_counters,
                    'blackbox_total_ticket_counter': this.blackbox_total_ticket_counter,
                    'blackbox_signature': this.blackbox_signature,
                    'blackbox_tax_category_a': this.blackbox_tax_category_a,
                    'blackbox_tax_category_b': this.blackbox_tax_category_b,
                    'blackbox_tax_category_c': this.blackbox_tax_category_c,
                    'blackbox_tax_category_d': this.blackbox_tax_category_d,
                    'blackbox_date': this.blackbox_date,
                    'blackbox_time': this.blackbox_time,
                    'blackbox_unique_fdm_production_number': this.blackbox_unique_fdm_production_number,
                    'blackbox_vsc_identification_number': this.blackbox_vsc_identification_number,
                    'blackbox_plu_hash': this.get_plu(),
                    'blackbox_pos_production_id': this.pos.version.server_serie,
                    'blackbox_pos_version': this.pos.version.server_serie,
                });
             }
            return json;
        },
        get_plu: function() {
            let order_str = "";
            this.get_orderlines().forEach(function (current, index, array) {
                order_str += current.generate_plu_line();
            });
            let sha1 = Sha1.hash(order_str);
            return sha1.slice(sha1.length - 8);
        }
    });

    var orderline_super = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        can_be_merged_with: function(orderline) {
            // The Blackbox doesn't allow lines with a quantity of 5 numbers.
            if (!this.pos.useBlackBoxBe() || (this.pos.useBlackBoxBe() && (this.get_quantity() + orderline.get_quantity()) <= 9999)) {
                return orderline_super.can_be_merged_with.apply(this,arguments);
            } else {
                return false;
            }
        },
        _generate_translation_table: function () {
            var replacements = [
                ["ÄÅÂÁÀâäáàã", "A"],
                ["Ææ", "AE"],
                ["ß", "SS"],
                ["çÇ", "C"],
                ["ÎÏÍÌïîìí", "I"],
                ["€", "E"],
                ["ÊËÉÈêëéè", "E"],
                ["ÛÜÚÙüûúù", "U"],
                ["ÔÖÓÒöôóò", "O"],
                ["Œœ", "OE"],
                ["ñÑ", "N"],
                ["ýÝÿ", "Y"]
            ];

            var lowercase_to_uppercase = _.range("a".charCodeAt(0), "z".charCodeAt(0) + 1).map(function (lowercase_ascii_code) {
                return [String.fromCharCode(lowercase_ascii_code), String.fromCharCode(lowercase_ascii_code).toUpperCase()];
            });
            replacements = replacements.concat(lowercase_to_uppercase);

            var lookup_table = {};

            _.forEach(replacements, function (letter_group) {
                _.forEach(letter_group[0], function (special_char) {
                    lookup_table[special_char] = letter_group[1];
                });
            });

            return lookup_table;
        },
        generate_plu_line: function () {
            // |--------+-------------+-------+-----|
            // | AMOUNT | DESCRIPTION | PRICE | VAT |
            // |      4 |          20 |     8 |   1 |
            // |--------+-------------+-------+-----|

            // steps:
            // 1. replace all chars
            // 2. filter out forbidden chars
            // 3. build PLU line

            var amount = this._get_amount_for_plu();
            var description = this.get_product().display_name;
            var price_in_eurocent = this.get_display_price() * 100;
            var vat_letter = this.get_vat_letter();

            amount = this._prepare_number_for_plu(amount, 4);
            description = this._prepare_description_for_plu(description);
            price_in_eurocent = this._prepare_number_for_plu(price_in_eurocent, 8);

            return amount + description + price_in_eurocent + vat_letter;
        },
        _prepare_number_for_plu: function (number, field_length) {
            number = Math.abs(number);
            number = Math.round(number);

            var number_string = number.toFixed(0);

            number_string = this._replace_hash_and_sign_chars(number_string);
            number_string = this._filter_allowed_hash_and_sign_chars(number_string);

            // get the required amount of least significant characters
            number_string = number_string.substr(-field_length);

            // pad left with 0 to required size
            while (number_string.length < field_length) {
                number_string = "0" + number_string;
            }

            return number_string;
        },

        _prepare_description_for_plu: function (description) {
            description = this._replace_hash_and_sign_chars(description);
            description = this._filter_allowed_hash_and_sign_chars(description);

            // get the 20 most significant characters
            description = description.substr(0, 20);

            // pad right with SPACE to required size of 20
            while (description.length < 20) {
                description = description + " ";
            }

            return description;
        },

        _get_amount_for_plu: function () {
            // three options:
            // 1. unit => need integer
            // 2. weight => need integer gram
            // 3. volume => need integer milliliter

            var amount = this.get_quantity();
            var uom = this.get_unit();

            if (uom.is_unit) {
                return amount;
            } else {
                if (uom.category_id[1] === "Weight") {
                    var uom_gram = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Weight" && unit.name === "g";
                    });
                    amount = (amount / uom.factor) * uom_gram.factor;
                } else if (uom.category_id[1] === "Volume") {
                    var uom_milliliter = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Volume" && unit.name === "Milliliter(s)";
                    });
                    amount = (amount / uom.factor) * uom_milliliter.factor;
                }

                return amount;
            }
        },
        get_vat_letter: function () {
            var taxes = this.get_taxes()[0];
            taxes = this._map_tax_fiscal_position(taxes);

            return taxes[0].identification_letter;
        },
        _replace_hash_and_sign_chars: function (str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var translation_table = this._generate_translation_table();

            var replaced_char_array = _.map(str, function (char, index, str) {
                var translation = translation_table[char];
                if (translation) {
                    return translation;
                } else {
                    return char;
                }
            });

            return replaced_char_array.join("");
        },

        // for hash and sign the allowed range for DATA is:
        //   - A-Z
        //   - 0-9
        // and SPACE as well. We filter SPACE out here though, because
        // SPACE will only be used in DATA of hash and sign as description
        // padding
        _filter_allowed_hash_and_sign_chars: function (str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var filtered_char_array = _.filter(str, function (char) {
                var ascii_code = char.charCodeAt(0);

                if ((ascii_code >= "A".charCodeAt(0) && ascii_code <= "Z".charCodeAt(0)) ||
                    (ascii_code >= "0".charCodeAt(0) && ascii_code <= "9".charCodeAt(0))) {
                    return true;
                } else {
                    return false;
                }
            });

            return filtered_char_array.join("");
        },
        export_as_JSON: function () {
            var json = orderline_super.export_as_JSON.bind(this)();

            if(this.pos.useBlackBoxBe()) {
                json = _.extend(json, {
                    'vat_letter': this.get_vat_letter(),
                });
            }

            return json;
        },
        export_for_printing: function() {
            let line = orderline_super.export_for_printing.apply(this,arguments);
            if(this.pos.useBlackBoxBe())
                line.vat_letter = this.get_vat_letter();
            return line;
        },
    });

    models.load_fields("res.users", "insz_or_bis_number");
    models.load_fields("hr.employee", "insz_or_bis_number");
    models.load_fields("account.tax", "identification_letter");
    models.load_fields("res.company", "street");
    models.load_fields("pos.session", "users_clocked_ids");
    models.load_fields("pos.session", "employees_clocked_ids");
    models.load_fields("pos.config", "certifiedBlackboxIdentifier");
});
