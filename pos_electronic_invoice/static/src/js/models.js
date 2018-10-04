odoo.define('pos_electronic_invoice.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');


    var pos_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (attributes, options) {
            pos_super.initialize.apply(this, arguments);
            return this
        },
        get_simple_inv_next_number: function () {
            ++this.config.ticket_hacienda_number;
            console.log(this.config.ticket_hacienda_number);
            return this.config.ticket_hacienda_prefix+this.get_padding_simple_inv(this.config.ticket_hacienda_number);
        },
        get_padding_simple_inv: function (number) {
            var diff = this.config.ticket_hacienda_padding - number.toString().length;
            var result = '';
            if (diff <= 0) {
                result = number;
            } else {
                for (var i = 0; i < diff; i++) {
                    result += '0';
                }
                result += number;
            }
            return result;
        },
        formatDate: function(d){
            var month = d.getMonth();
            var day = d.getDate().toString();
            var year = d.getFullYear();
            year = year.toString().substr(-2);
            month = (month + 1).toString();
            if (month.length === 1) {
                month = "0" + month;
            }
            if (day.length === 1){
                day = "0" + day;
            }
            return  day + month + year;
        }
    });

    var order_super = models.Order.prototype;
    models.Order = models.Order.extend({
        set_simple_inv_number: function () {
            var fullDate = new Date();
            this.dni = this.pos.company.vat;
            var next = this.pos.get_simple_inv_next_number();
            this.consecutivo = '00'+next;
            var clave = '506'+this.pos.formatDate(fullDate)+'000'+this.dni+this.consecutivo+'100006645';
            console.log(clave);
            this.ticket_hacienda = clave;

        },
        init_from_JSON: function (json) {
            order_super.init_from_JSON.apply(this, arguments);
            this.to_invoice = json.to_invoice;
            this.ticket_hacienda = json.ticket_hacienda;
            this.consecutivo = json.consecutivo
        },
        export_as_JSON: function () {
            var res = order_super.export_as_JSON.apply(this, arguments);
            res.to_invoice = this.is_to_invoice();
            if (!res.to_invoice) {
                res.ticket_hacienda= this.ticket_hacienda;
                res.consecutivo = this.consecutivo
            }
            return res;
        }
    });

    models.load_fields('res.company', ['street', 'city', 'state_id', 'zip']);

});
