# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.account.analytic.line",
        inverse_name="odoo_id",
        copy=False,
        string="Worklog Bindings",
        context={"active_test": False},
    )
    # fields needed to display JIRA issue link in views
    jira_issue_key = fields.Char(
        string="Original JIRA Issue Key",
        compute="_compute_jira_references",
        store=True,
    )
    jira_issue_url = fields.Char(
        string="Original JIRA issue Link",
        compute="_compute_jira_references",
        compute_sudo=True,
        store=True,
    )
    jira_epic_issue_key = fields.Char(
        compute="_compute_jira_references",
        string="Original JIRA Epic Key",
        store=True,
    )
    jira_epic_issue_url = fields.Char(
        string="Original JIRA Epic Link",
        compute="_compute_jira_references",
        compute_sudo=True,
        store=True,
    )

    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Original JIRA Issue Type",
        compute="_compute_jira_references",
        store=True,
    )

    @api.depends(
        "jira_bind_ids",
        "jira_bind_ids.jira_issue_key",
        "jira_bind_ids.jira_issue_url",
        "jira_bind_ids.jira_issue_type_id",
        "jira_bind_ids.jira_epic_issue_key",
        "jira_bind_ids.jira_epic_issue_url",
    )
    def _compute_jira_references(self):
        """Compute the various references to JIRA.

        We assume that we have only one external record for a line
        """
        with_bind = self.filtered("jira_bind_ids")
        for record in with_bind:
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_key = main_binding.jira_issue_key
            record.jira_issue_url = main_binding.jira_issue_url
            record.jira_issue_type_id = main_binding.jira_issue_type_id
            record.jira_epic_issue_key = main_binding.jira_epic_issue_key
            record.jira_epic_issue_url = main_binding.jira_epic_issue_url
        no_bind = self - with_bind
        if no_bind:
            no_bind.update(
                {
                    "jira_issue_key": "",
                    "jira_issue_url": "",
                    "jira_issue_type_id": False,
                    "jira_epic_issue_key": "",
                    "jira_epic_issue_url": "",
                }
            )

    @api.model
    def _get_connector_jira_fields(self):
        return [
            "jira_bind_ids",
            "project_id",
            "task_id",
            "user_id",
            "employee_id",
            "name",
            "date",
            "unit_amount",
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
                    _("Timesheet can not be created in project linked to JIRA!")
                )

    def _connector_jira_write_validate(self, vals):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            fields = list(vals.keys())
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
                        _("Timesheet linked to JIRA Worklog can not be modified!")
                    )

    def _connector_jira_unlink_validate(self):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            raise exceptions.UserError(
                _("Timesheet linked to JIRA Worklog can not be deleted!")
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

    def action_open_refresh_worklogs_from_jira_wizard(self):
        return {
            "name": _("Refresh Worklogs from Jira"),
            "type": "ir.actions.act_window",
            "target": "new",
            "view_mode": "form",
            "res_model": "jira.account.analytic.line.import",
            "context": {"default_analytic_line_ids": [fields.Command.set(self.ids)]},
        }
