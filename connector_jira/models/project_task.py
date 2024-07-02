# Copyright 2016-2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models
from odoo.osv import expression


class ProjectTask(models.Model):
    _inherit = "project.task"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.project.task",
        inverse_name="odoo_id",
        copy=False,
        string="Task Bindings",
        context={"active_test": False},
    )
    jira_issue_type = fields.Char(
        compute="_compute_jira_issue_type",
        string="JIRA Issue Type",
        store=True,
    )
    jira_compound_key = fields.Char(
        compute="_compute_jira_compound_key",
        string="JIRA Key",
        store=True,
    )
    jira_epic_link_task_id = fields.Many2one(
        comodel_name="project.task",
        compute="_compute_jira_epic_link_task_id",
        string="JIRA Epic",
        store=True,
    )
    jira_parent_task_id = fields.Many2one(
        comodel_name="project.task",
        compute="_compute_jira_parent_task_id",
        string="JIRA Parent",
        store=True,
    )
    jira_issue_url = fields.Char(
        string="JIRA issue",
        compute="_compute_jira_issue_url",
    )

    @api.depends("jira_bind_ids.jira_issue_type_id.name")
    def _compute_jira_issue_type(self):
        for record in self:
            types = record.mapped("jira_bind_ids.jira_issue_type_id.name")
            record.jira_issue_type = ",".join([t for t in types if t])

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_compound_key(self):
        for record in self:
            keys = record.mapped("jira_bind_ids.jira_key")
            record.jira_compound_key = ",".join([k for k in keys if k])

    @api.depends("jira_bind_ids.jira_epic_link_id.odoo_id")
    def _compute_jira_epic_link_task_id(self):
        for record in self:
            tasks = record.mapped("jira_bind_ids.jira_epic_link_id.odoo_id")
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks

    @api.depends("jira_bind_ids.jira_parent_id.odoo_id")
    def _compute_jira_parent_task_id(self):
        for record in self:
            tasks = record.mapped("jira_bind_ids.jira_parent_id.odoo_id")
            if len(tasks) == 1:
                record.jira_parent_task_id = tasks

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA.

        We assume that we have only one external record.
        """
        for record in self:
            if not record.jira_bind_ids:
                record.jira_issue_url = False
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_url = main_binding.jira_issue_url

    # pylint: disable=W8110
    @api.depends("jira_compound_key")
    def _compute_display_name(self):
        super()._compute_display_name()
        for task in self.filtered("jira_compound_key"):
            task.display_name = f"[{task.jira_compound_key}] {task.display_name}"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        res = super().name_search(name, args, operator, limit)
        if not name:
            return res
        domain = [
            "|",
            ("jira_compound_key", "=ilike", name + "%"),
            ("id", "in", [x[0] for x in res]),
        ]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = ["&", "!"] + domain[1:]
        tasks = self.search(domain + (args or []), limit=limit)
        return [(t.id, t.display_name) for t in tasks.sudo()]

    @api.model
    def _get_connector_jira_fields(self):
        return [
            "jira_bind_ids",
            "name",
            "date_deadline",
            "user_id",
            "description",
            "active",
            "project_id",
            "planned_hours",
            "stage_id",
        ]

    @api.model
    def _connector_jira_create_validate(self, vals):
        ProjectProject = self.env["project.project"]
        project_id = vals.get("project_id")
        if project_id:
            project_id = ProjectProject.sudo().browse(project_id)
            if (
                not self.env.context.get("connector_jira")
                and project_id.mapped("jira_bind_ids")._is_linked()
            ):
                raise exceptions.UserError(
                    _("Task can not be created in project linked to JIRA!")
                )

    def _connector_jira_write_validate(self, vals):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            fields = list(vals.keys())
            self._update_cache(vals)
            new_values = self._convert_to_write(
                vals,
            )
            for old_values in self.read(fields, load="_classic_write"):
                old_values = self._convert_to_write(
                    old_values,
                )
                for field in self._get_connector_jira_fields():
                    if field not in fields:
                        continue
                    if new_values[field] == old_values[field]:
                        continue
                    raise exceptions.UserError(
                        _("Task linked to JIRA Issue can not be modified!")
                    )

    def _connector_jira_unlink_validate(self):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            raise exceptions.UserError(
                _("Task linked to JIRA Issue can not be deleted!")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._connector_jira_create_validate(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._connector_jira_write_validate(vals)
        return super().write(vals)

    def unlink(self):
        self._connector_jira_unlink_validate()
        return super().unlink()

    def create_and_link_jira(self):
        self.ensure_one()
        backends = self.project_id.jira_bind_ids.backend_id
        xmlid = "connector_jira.open_task_link_jira"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["context"] = dict(
            self.env.context,
            default_task_id=self.id,
            default_linked_backend_ids=[fields.Command.set(backends.ids)],
            default_backend_id=backends.id if len(backends) == 1 else False,
        )
        return action
