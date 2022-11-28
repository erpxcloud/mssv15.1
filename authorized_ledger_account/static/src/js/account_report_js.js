 odoo.define('authorized_ledger_account.account_report_js', function (require) {
'use strict';

var core = require('web.core');
var AccountReport = require('account_reports.account_report');
var session = require('web.session')
var QWeb = core.qweb;
var _t = core._t;

var accountReportExtended = AccountReport.include({
	
   	render_searchview_buttons: function() {
        var parent = this.$searchview_buttons;
		
    	self = this;
        this.$searchview_buttons.find('.selectalljournals').click(function (event) {
			parent.find('.js_account_report_choice_filter').each(function(){
				var option_value = $(this).data('filter');
	            var option_id = $(this).data('id');
	            _.filter(self.report_options[option_value], function(el) {
	                el.selected = true;
	                return el;
	            });
			});
			self.reload();
        });
        
         this.$searchview_buttons.find('.deselectalljournals').click(function (event) {
			parent.find('.js_account_report_choice_filter').each(function(){
				var option_value = $(this).data('filter');
	            var option_id = $(this).data('id');
	            _.filter(self.report_options[option_value], function(el) {
	                el.selected = false;
	                return el;
	            });
			});
			self.reload();
        });
       
        this._super.apply(this, arguments);
	},
});

core.action_registry.add('account_report_js', accountReportExtended);

return accountReportExtended;

});
  