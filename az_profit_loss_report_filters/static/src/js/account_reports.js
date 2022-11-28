odoo.define('az_divisions_reports.account_report', function (require) {
'use strict';

var core = require('web.core');
var AccountReport = require('account_reports.account_report');
var RelationalFields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var _t = core._t;
var Widget = require('web.Widget');
var QWeb = core.qweb;

var M2MFilters = Widget.extend(StandaloneFieldManagerMixin, {
    /**
     * @constructor
     * @param {Object} fields
     */
    init: function (parent, fields) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.fields = fields;
        this.widgets = {};
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        _.each(this.fields, function (field, fieldName) {
            defs.push(self._makeM2MWidget(field, fieldName));
        });
        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var $content = $(QWeb.render("m2mWidgetTable", {fields: this.fields}));
        self.$el.append($content);
        _.each(this.fields, function (field, fieldName) {
            self.widgets[fieldName].appendTo($content.find('#'+fieldName+'_field'));
        });
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method will be called whenever a field value has changed and has
     * been confirmed by the model.
     *
     * @private
     * @override
     * @returns {Promise}
     */
    _confirmChange: function () {
        var self = this;
        var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
        var data = {};
        _.each(this.fields, function (filter, fieldName) {
            data[fieldName] = self.widgets[fieldName].value.res_ids;
        });
        this.trigger_up('value_changed', data);
        return result;
    },
    /**
     * This method will create a record and initialize M2M widget.
     *
     * @private
     * @param {Object} fieldInfo
     * @param {string} fieldName
     * @returns {Promise}
     */
    _makeM2MWidget: function (fieldInfo, fieldName) {
        var self = this;
        var options = {};
        options[fieldName] = {
            options: {
                no_create_edit: true,
                no_create: true,
            }
        };
        return this.model.makeRecord(fieldInfo.modelName, [{
            fields: [{
                name: 'id',
                type: 'integer',
            }, {
                name: 'display_name',
                type: 'char',
            }],
            name: fieldName,
            relation: fieldInfo.modelName,
            type: 'many2many',
            value: fieldInfo.value,
        }], options).then(function (recordID) {
            self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                fieldName,
                self.model.get(recordID),
                {mode: 'edit',}
            );
            self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
        });
    },
});

AccountReport.include({
	 custom_events: {
	        'value_changed': function(ev) {
	            var self = this;
	            self.report_options.division_ids = ev.data.division_ids;
				self.report_options.end_user_ids = ev.data.end_user_ids;
				self.report_options.partner_ids = ev.data.partner_ids;
	            self.report_options.partner_categories = ev.data.partner_categories;
	            self.report_options.analytic_accounts = ev.data.analytic_accounts;
	            self.report_options.analytic_tags = ev.data.analytic_tags;
	            return self.reload().then(function () {
	            	self.$searchview_buttons.find('.account_partner_filter').click();
	               /* self.$searchview_buttons.find('.account_analytic_filter').click();
 					self.$searchview_buttons.find('.cost_center_filter').click();*/
	            });
	    	},
	  },
	    
	  render_searchview_buttons: function() {

            if (!this.M2MFilters1) {
                var fields1 = {};
                
                if (this.report_options.division_ids) {
                    fields1['division_ids'] = {
                        label: _t('Divisions'),
                        modelName: 'azk_sales_division.division',
                        value: this.report_options.division_ids.map(Number),
                    };
                }
                if (!_.isEmpty(fields1)) {
                    this.M2MFilters1 = new M2MFilters(this, fields1);
                    this.M2MFilters1.appendTo(this.$searchview_buttons.find('.js_divisions_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_divisions_m2m').append(this.M2MFilters1.$el);
            }

			if (!this.M2MFilters2) {
                var fields2 = {};
                
                if (this.report_options.end_user_ids) {
                    fields2['end_user_ids'] = {
                        label: _t('End User'),
                        modelName: 'res.partner',
                        value: this.report_options.end_user_ids.map(Number),
                    };
                }
                if (!_.isEmpty(fields2)) {
                    this.M2MFilters2 = new M2MFilters(this, fields2);
                    this.M2MFilters2.appendTo(this.$searchview_buttons.find('.js_end_users_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_end_users_m2m').append(this.M2MFilters2.$el);
            }
	        
	        this._super.apply(this, arguments);
	  },
    
});

});