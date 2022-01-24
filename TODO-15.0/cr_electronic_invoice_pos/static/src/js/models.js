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
    var rpc = require('web.rpc');

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
                ids:    function(self){ 
                    return [
                        self.config.FE_sequence_id[0],
                        self.config.TE_sequence_id[0]
                    ]; 
                },
                loaded: function(self, sequence){
                    self.FE_sequence = sequence[0];
                    self.TE_sequence = sequence[1]; 
                },
            });
            return PosModelParent.load_server_data.call(this, arguments);
        }
    });

    var OrderParent = models.Order;
    models.Order = models.Order.extend({
        /* initialize: function
         * Declare
         * sequence: Stores the last electronic sequence
         * number_electronic: Stores the last number electronic
         * tipo_documento: Stores the doc type
         */
        initialize: function(attr,options){
            OrderParent.prototype.initialize.call(this, attr, options);

            // Initialize the variables
            this.sequence;
            this.number_electronic;
            this.tipo_documento;
        },
        export_for_printing: function(attributes){
            var self = this;
            var order = OrderParent.prototype.export_for_printing.call(this);

            if(this.get_client()){
                if(this.get_client().vat){
                    var model = 'ir.sequence';
                    var domain = [['id', '=', this.pos.config.FE_sequence_id[0]]];
                    var fields = [];
                    // Get the last FE POS sequence
                    rpc.query({
                        model: model,
                        method: 'search_read',
                        args: [domain, fields],
                    }).then(function (data) {
                        self.sequence = data[0].number_next_actual;
                        self.number_electronic = _sequence_next(data[0]);
                        self.tipo_documento = 'FE'
                    });
                }
                else{
                    var model = 'ir.sequence';
                    var domain = [['id', '=', this.pos.config.TE_sequence_id[0]]];
                    var fields = [];
                    // Get the last TE POS sequence
                    rpc.query({
                        model: model,
                        method: 'search_read',
                        args: [domain, fields],
                    }).then(function (data) {
                        self.sequence = data[0].number_next_actual;
                        self.number_electronic = _sequence_next(data[0]);
                        self.tipo_documento = 'TE'
                    });
                }
            }
            // If the partner is not set, the information will be for tickets
            else{
                var model = 'ir.sequence';
                var domain = [['id', '=', self.pos.config.TE_sequence_id[0]]];
                var fields = [];
                // Get the last TE POS sequence
                rpc.query({
                    model: model,
                    method: 'search_read',
                    args: [domain, fields],
                }).then(function (data) {
                    self.sequence = data[0].number_next_actual;
                    self.number_electronic = _sequence_next(data[0]);
                    self.tipo_documento = 'TE'
                });
            }
            
            // Set the "global" information updated with RPC
            order['sequence'] = self.sequence;
            order['number_electronic'] = self.number_electronic;
            order['tipo_documento'] = self.tipo_documento;

            return order;
        },
        export_as_JSON: function() {
            var self = this;
            var order = OrderParent.prototype.export_as_JSON.call(this);

            if(this.get_client()){
                if(this.get_client().vat){
                    var model = 'ir.sequence';
                    var domain = [['id', '=', this.pos.config.FE_sequence_id[0]]];
                    var fields = [];
                    // Get the last FE POS sequence
                    rpc.query({
                        model: model,
                        method: 'search_read',
                        args: [domain, fields],
                    }).then(function (data) {
                        self.sequence = data[0].number_next_actual;
                        self.number_electronic = _sequence_next(data[0]);
                        self.tipo_documento = 'FE'
                    });
                }
                else{
                    var model = 'ir.sequence';
                    var domain = [['id', '=', this.pos.config.TE_sequence_id[0]]];
                    var fields = [];
                    // Get the last TE POS sequence
                    rpc.query({
                        model: model,
                        method: 'search_read',
                        args: [domain, fields],
                    }).then(function (data) {
                        self.sequence = data[0].number_next_actual;
                        self.number_electronic = _sequence_next(data[0]);
                        self.tipo_documento = 'TE'
                    });
                }
            }
            // If the partner is not set, the information will be for tickets
            else{
                var model = 'ir.sequence';
                var domain = [['id', '=', self.pos.config.TE_sequence_id[0]]];
                var fields = [];
                // Get the last TE POS sequence
                rpc.query({
                    model: model,
                    method: 'search_read',
                    args: [domain, fields],
                }).then(function (data) {
                    self.sequence = data[0].number_next_actual;
                    self.number_electronic = _sequence_next(data[0]);
                    self.tipo_documento = 'TE'
                });
            }
            
            // Set the "global" information updated with RPC
            order['sequence'] = self.sequence;
            order['number_electronic'] = self.number_electronic;
            order['tipo_documento'] = self.tipo_documento;

            return order;
        }
    });

    return exports;
});
