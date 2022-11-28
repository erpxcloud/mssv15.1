odoo.define('lb_account_reports.account_report', function (require) {
'use strict';

var core = require('web.core');
var AccountReport = require('account_reports.account_report');
var Widget = require('web.Widget');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var RelationalFields = require('web.relational_fields');
var QWeb = core.qweb;
var _t = core._t;

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
    
	events: {
        'input .o_account_reports_filter_input': 'filter_accounts',
        'click .o_account_reports_summary': 'edit_summary',
        'click .js_account_report_save_summary': 'save_summary',
        'click .o_account_reports_footnote_icons': 'delete_footnote',
        'click .js_account_reports_add_footnote': 'add_edit_footnote',
        'click .js_account_report_foldable': 'fold_unfold',
        'click [action]': 'trigger_action',
        'click .o_account_reports_load_more span': 'load_more',
        'click .search_account_range': '_searchAccountRange',
        'click .search_account_range_clear': 'clearFilter',
    },
    
	 custom_events: {
	        'value_changed': function(ev) {
	            var self = this;
	            self.report_options.account_ids = ev.data.account_ids;
				self.report_options.partner_ids = ev.data.partner_ids;
	            self.report_options.partner_categories = ev.data.partner_categories;
	            self.report_options.analytic_accounts = ev.data.analytic_accounts;
	            self.report_options.analytic_tags = ev.data.analytic_tags;
	            return self.reload().then(function () {
	            	self.$searchview_buttons.find('.account_partner_filter').click();
	                self.$searchview_buttons.find('.account_analytic_filter').click();
	            });
	    	},
	    },
    	render_searchview_buttons: function() {
			if ('search_values' in this.report_options){
	    		var values = this.report_options.search_values;
	    		for (let x in values) {
	    			$('.bootstrap-tagsinput input').val(values[x]);
	    			$('.o_account_reports_filter_from_input').val(values[x]).tagsinput();
	    		}
	  			
	    	}
			// partner filter
	        if (this.report_options.partner || this.report_options.accounts) {
	            if (!this.M2MFilters) {
	                var fields = {};
					if (this.report_options.partner){
		                if ('partner_ids' in this.report_options) {
		                    fields['partner_ids'] = {
		                        label: _t('Partners'),
		                        modelName: 'res.partner',
		                        value: this.report_options.partner_ids.map(Number),
		                    };
		                }
		                if ('partner_categories' in this.report_options) {
		                    fields['partner_categories'] = {
		                        label: _t('Tags'),
		                        modelName: 'res.partner.category',
		                        value: this.report_options.partner_categories.map(Number),
		                    };
		                }
					}
					
					if (this.report_options.accounts){
						if ('account_ids' in this.report_options) {
		                    fields['account_ids'] = {
		                        label: _t('Accounts'),
		                        modelName: 'account.account',
		                        value: this.report_options.account_ids.map(Number),
		                    };
		                }
					}
					
	                if (!_.isEmpty(fields)) {
	                    this.M2MFilters = new M2MFilters(this, fields);
	                    this.M2MFilters.appendTo(this.$searchview_buttons.find('.js_account_partner_m2m'));
	                }
	            } else {
	                this.$searchview_buttons.find('.js_account_partner_m2m').append(this.M2MFilters.$el);
	            }
	        }
		this._super.apply(this, arguments);
	},

    _add_line_classes: function() {
        /* Pure JS to improve performance in very cornered case (~200k lines)
         * Jquery code:
         *  this.$('.o_account_report_line').filter(function () {
         *      return $(this).data('unfolded') === 'True';
         *  }).parent().addClass('o_js_account_report_parent_row_unfolded');
         */
        var el = this.$el[0];
        var report_lines = el.getElementsByClassName('o_account_report_line');
        for (var l=0; l < report_lines.length; l++) {
            var line = report_lines[l];
            var unfolded = line.dataset.unfolded;
            if (unfolded === 'True') {
                line.parentNode.classList.add('o_js_account_report_parent_row_unfolded');
            }
        }
        // This selector is not adaptable in pure JS
        this.$('tr[data-parent-id]').addClass('o_js_account_report_inner_row');
        
        if (this.report_options['filter_accounts_ledger']){
            console.log("Getting filter by account ledger from trial balance");
            this.$el.find('.o_account_reports_filter_input').val(this.report_options['filter_accounts_ledger']);
            this.$el.find('.o_account_reports_filter_input').trigger('input');
        }
        
     },
    
	filter_accounts: function(e) {
        var self = this;
        var query = e.target.value.trim().toLowerCase();
        this.filterOn = false;
        var availableTags = [];
        
        this.$('.o_account_reports_table').find('tbody').find('tr').each(function(index, el) {
            var $accountReportLineFoldable = $(el);
            var line_id = $accountReportLineFoldable.find('.o_account_report_line').data('id');
            var $childs = self.$('tr[data-parent-id="'+line_id+'"]');
            
            var lineText = '';
            
            if($accountReportLineFoldable.find('.o_account_reports_domain_line_2').length > 0){
            	var lineText = $accountReportLineFoldable.find('.o_account_reports_domain_line_2')
                // Only the direct text node, not text situated in other child nodes
                .contents().get(0).nodeValue
                .trim();
            }else if($accountReportLineFoldable.find('.account_report_line_name').length > 0){
            	var lineText = $accountReportLineFoldable.find('.account_report_line_name')
                // Only the direct text node, not text situated in other child nodes
                .contents().get(0).nodeValue
                .trim();
            }
            
            // The python does this too
            var queryFound = lineText.split('  ').some(function (str) {
            	var str_found = str.toLowerCase().includes(query);
            	if(str_found && availableTags.indexOf(str) == -1){
            		availableTags.push(str)
            	}
                return str_found
            });
            
            $accountReportLineFoldable.toggleClass('o_account_reports_filtered_lines', !queryFound);
            $childs.toggleClass('o_account_reports_filtered_lines', !queryFound);

            if (!queryFound) {
                self.filterOn = true;
            }
        });
        
        $(".o_account_reports_filter_input").autocomplete({
        	source: availableTags,
        	select: function( event, ui ) {
        		self.$('.o_account_reports_table').find('tbody').find('tr').each(function(index, el) {
                    var $accountReportLineFoldable = $(el);
                    var line_id = $accountReportLineFoldable.find('.o_account_report_line').data('id');
                    var $childs = self.$('tr[data-parent-id="'+line_id+'"]');
                    
                    var lineText = '';
                    
                    if($accountReportLineFoldable.find('.o_account_reports_domain_line_2').length > 0){
                    	var lineText = $accountReportLineFoldable.find('.o_account_reports_domain_line_2')
                        // Only the direct text node, not text situated in other child nodes
                        .contents().get(0).nodeValue
                        .trim();
                    }else if($accountReportLineFoldable.find('.account_report_line_name').length > 0){
                    	var lineText = $accountReportLineFoldable.find('.account_report_line_name')
                        // Only the direct text node, not text situated in other child nodes
                        .contents().get(0).nodeValue
                        .trim();
                    }
                    
                    var q = ui.item.value
                	query = q.trim().toLowerCase();
                    
                    // The python does this too
                    var queryFound = lineText.split('  ').some(function (str) {
                    	var str_found = str.toLowerCase().includes(query);
                    	if(str_found && availableTags.indexOf(str) == -1){
                    		availableTags.push(str)
                    	}
                        return str_found
                    });
                    
                    $accountReportLineFoldable.toggleClass('o_account_reports_filtered_lines', !queryFound);
                    $childs.toggleClass('o_account_reports_filtered_lines', !queryFound);

                    if (!queryFound) {
                        self.filterOn = true;
                    }
                });
	    		
            },
            focus: function( event, ui ) {
            	if (ui.item != undefined){
            		var q = ui.item.value
            		
            		query = q.trim().toLowerCase();
                	
                	if (self.filterOn) {
                		self.$('.o_account_reports_level1.total').hide();
                    }
                    else {
                    	self.$('.o_account_reports_level1.total').css({'display': 'table-row'});
                    }
                    
                	self.report_options['filter_accounts'] = query;
                	self.render_footnotes();
            	}
            }
	    });
        
        if (this.filterOn) {
            this.$('.o_account_reports_level1.total').hide();
        }
        else {
            this.$('.o_account_reports_level1.total').css({'display': 'table-row'});
        }
        
        this.report_options['filter_accounts'] = query;
        this.render_footnotes();
    },
    
    _searchAccountRange: function(e) {
        var self = this;
        this.filterOn = false;
    	
        var account_from_value_list = $(".o_account_reports_filter_from_input").tagsinput('items');
       
		 this._rpc({
        	model: this.report_model,
            method: 'get_search_data',
            args: [self.financial_id, account_from_value_list],
        }).then(function(result){
        	 self.reload();
        });
    },
    
    clearFilter: function(){
    	var self = this;
    	this._rpc({
        	model: this.report_model,
            method: 'clear_data',
            args: [self.financial_id],
        }).then(function(result){
        	self.reload();
        });
    },
    
    unfold: function(line) {
        var self = this;
        var line_id = line.data('id');
        line.toggleClass('folded');
        self.report_options.unfolded_lines.push(line_id);
        var $lines_in_dom = this.$el.find('tr[data-parent-id="'+line_id+'"]');
        if ($lines_in_dom.length > 0) {
            $lines_in_dom.find('.js_account_report_line_footnote').removeClass('folded');
        	$lines_in_dom.show();
        	$lines_in_dom.css({'display': 'table-row'});
            line.find('.fa-caret-right').toggleClass('fa-caret-right fa-caret-down');
            line.data('unfolded', 'True');
            this._add_line_classes();
            return true;
        }else {
            return this._rpc({
                    model: this.report_model,
                    method: 'get_html',
                    args: [self.financial_id, self.report_options, line.data('id')],
                    context: self.odoo_context,
                })
                .then(function(result){
                    $(line).parent('tr').replaceWith(result);
                    self._add_line_classes();
                });
        }
        
    },

});

});