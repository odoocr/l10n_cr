/****************************************************************************
 *
 *    OpenERP, Open Source Management Solution
 *    Copyright (C) 2016 Aselcis Consulting (http://www.aselcis.com). All Rights Reserved
 *    Copyright (C) 2016 David Gómez Quilón (http://www.aselcis.com). All Rights Reserved
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU Affero General Public License as
 *    published by the Free Software Foundation, either version 3 of the
 *    License, or (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 ******************************************************************************/

odoo.define('cr_electronic_invoice_pos.models', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var models = require('point_of_sale.models');
    var exports = {};

    var _sequence_next = function(seq){
        var idict = {
            'year': moment().format('YYYY'),
            'month': moment().format('MM'),
            'day': moment().format('DD'),
            'y': moment().format('YY'),
            'h12': moment().format('hh')
        };
        var format = function(s, dict){
            s = s || '';
            $.each(dict, function(k, v){
                s = s.replace('%(' + k + ')s', v);
            });
            return s;
        };
        function pad(n, width, z) {
            z = z || '0';
            n = n + '';
            if (n.length < width) {
                n = new Array(width - n.length + 1).join(z) + n;
            }
            return n;
        }
        var num = seq.number_next_actual;
        var prefix = format(seq.prefix, idict);
        var suffix = format(seq.suffix, idict);
        seq.number_next_actual += seq.number_increment;
        return prefix + pad(num, seq.padding) + suffix;
    };

    var PosModelParent = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        load_server_data: function(){
            var self = this;
            // Load POS sequence object
            self.models.push({
                model: 'ir.sequence',
                fields: [],
                ids:    function(self){ return [self.config.FE_sequence_id[0],self.config.TE_sequence_id[0]]; },
                loaded: function(self, sequence){ self.FE_sequence = sequence[0];self.TE_sequence = sequence[1]; },
            });
            //debugger;
            return PosModelParent.load_server_data.apply(this, arguments);
        },
        push_order: function(order, opts) {
            //debugger;
            if (order !== undefined) {
                if (order.get('client') && order.get('client').vat) {
                    order.set({'sequence': this.FE_sequence.number_next_actual});
                    order.set({'number_electronic': _sequence_next(this.FE_sequence)});
                    order.set({'tipo_documento': 'FE'});

                } else {
                    order.set({'sequence': this.TE_sequence.number_next_actual});
                    order.set({'number_electronic': _sequence_next(this.TE_sequence)});
                    order.set({'tipo_documento': 'TE'});
                }
            };
            //debugger;
            //return PosModelParent.push_order.call(order,opts);
            return PosModelParent.push_order.apply(this, arguments);
        }
    });

    var OrderParent = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function(attributes){
            var order = OrderParent.export_for_printing.apply(this, arguments);
            order['number_electronic'] = this.get('number_electronic');
            order['sequence'] = this.get('sequence');
            order['tipo_documento'] = this.get('tipo_documento');
            //debugger;
            return order;
        },
        export_as_JSON: function() {
            var order = OrderParent.export_as_JSON.apply(this, arguments);
            order['number_electronic'] = this.get('number_electronic');
            order['sequence'] = this.get('sequence');
            order['tipo_documento'] = this.get('tipo_documento');
            //debugger;
            return order;
        }
    });

    //models.load_fields('res.company', ['street', 'city', 'state_id', 'zip']);
    //models.load_fields('res.partner', ['identification_id'])

    return exports;
});
