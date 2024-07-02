# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraIssueTypeAdapter(Component):
    _name = "jira.issue.type.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.issue.type"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.issue_type(id_).raw

    def search(self):
        issues = self.client.issue_types()
        return [issue.id for issue in issues]
