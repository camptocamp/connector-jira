# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ProjectProject(models.Model):
    _inherit = "project.project"
    _rec_names_search = ["jira_key"]

    jira_bind_ids = fields.One2many(
        comodel_name="jira.project.project",
        inverse_name="odoo_id",
        copy=False,
        string="Project Bindings",
        context={"active_test": False},
    )
    jira_key = fields.Char(
        string="JIRA Key",
        compute="_compute_jira_key",
        store=True,
    )

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_key(self):
        for project in self:
            project.jira_key = ", ".join(project.jira_bind_ids.mapped("jira_key"))

    # pylint: disable=W8110
    @api.depends("jira_key")
    def _compute_display_name(self):
        super()._compute_display_name()
        for project in self.filtered("jira_key"):
            project.display_name = f"[{project.jira_key}] {project.display_name}"

    def create_and_link_jira(self):
        self.ensure_one()
        xmlid = "connector_jira.open_project_link_jira"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["context"] = dict(self.env.context, default_project_id=self.id)
        return action
