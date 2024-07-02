# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class ProjectProjectListener(Component):
    _name = "project.project.listener"
    _inherit = ["base.connector.listener"]
    _apply_on = ["project.project"]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if fields == ["jira_bind_ids"] or fields == ["message_follower_ids"]:
            # When vals is esb_bind_ids:
            # Binding edited from the record's view. When only this field has
            # been modified, an other job has already been delayed for the
            # binding record so can exit this event early.

            # When vals is message_follower_ids:
            # MailThread.message_subscribe() has been called, this
            # method does a write on the field message_follower_ids,
            # we never want to export that.
            return
        for binding in record.jira_bind_ids:
            if binding.sync_action == "export":
                binding.with_delay(priority=10).export_record(fields=fields)
