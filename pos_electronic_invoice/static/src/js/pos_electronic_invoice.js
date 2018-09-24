odoo.define('pos_electronic_invoice', function(require){
    'use strict'
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');


    console.log("Pos js Loaded" , models)
    screens.PaymentScreenWidget.include({
        validate_order: function (force_validate) {
            debugger;
            var below_limit = this.pos.get_order().get_total_with_tax() <= this.pos.config.l10n_es_simplified_invoice_limit;
            if (this.pos.config.iface_l10n_es_simplified_invoice) {
                var order = this.pos.get_order();
                if (below_limit) {
                    order.set_simple_inv_number();
                } else {
                    // Force invoice above limit. Online is needed.
                    order.to_invoice = true;
                }
            }
            this._super(force_validate);
        }
    });

});