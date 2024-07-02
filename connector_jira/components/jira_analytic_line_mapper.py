# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from pytz import timezone, utc

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

from .common import (
    iso8601_to_naive_date,
    iso8601_to_utc_datetime,
    whenempty,
)

_logger = logging.getLogger(__name__)


class JiraAnalyticLineMapper(Component):
    _name = "jira.analytic.line.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.account.analytic.line"]

    direct = [(whenempty("comment", _("missing description")), "name")]

    @mapping
    def issue(self, record):
        issue = self.options.linked_issue
        assert issue
        refs = {
            "jira_issue_id": record["issueId"],
            "jira_issue_key": issue["key"],
        }
        task_mapper = self.component(
            usage="import.mapper",
            model_name="jira.project.task",
        )
        issue_type_dict = task_mapper.issue_type(issue)
        refs.update(issue_type_dict)
        epic_field_name = self.backend_record.epic_link_field_name
        if epic_field_name and epic_field_name in issue["fields"]:
            refs["jira_epic_issue_key"] = issue["fields"][epic_field_name]
        if self.backend_record.epic_link_on_epic:
            issue_type = self.env["jira.issue.type"].browse(
                issue_type_dict.get("jira_issue_type_id")
            )
            if issue_type.name == "Epic":
                refs["jira_epic_issue_key"] = issue.get("key")
        return refs

    @mapping
    def date(self, record):
        mode = self.backend_record.worklog_date_timezone_mode
        started = record["started"]
        if not mode or mode == "naive":
            return {"date": iso8601_to_naive_date(started)}
        started = iso8601_to_utc_datetime(started).replace(tzinfo=utc)
        if mode == "user":
            tz = timezone(record["author"]["timeZone"])
        elif mode == "specific":
            tz = timezone(self.backend_record.worklog_date_timezone)
        return {"date": started.astimezone(tz).date()}

    @mapping
    def duration(self, record):
        spent = float(record["timeSpentSeconds"])
        # amount is in float in odoo... 2h30 = 2.5
        return {"unit_amount": spent / 60 / 60}

    @mapping
    def author(self, record):
        jira_author = record["author"]
        jira_author_key = jira_author["accountId"]
        binder = self.binder_for("jira.res.users")
        user = binder.to_internal(jira_author_key, unwrap=True)
        if not user:
            email = jira_author.get("emailAddress", "<unknown>")
            raise MappingError(
                _(
                    "No user found with login '%(key)s' or email '%(mail)s'."
                    " You must create a user or link it manually if the"
                    " login/email differs.",
                    key=jira_author_key,
                    mail=email,
                )
            )
        employee = (
            self.env["hr.employee"]
            .with_context(
                active_test=False,
            )
            .search([("user_id", "=", user.id)], limit=1)
        )
        return {"user_id": user.id, "employee_id": employee.id}

    @mapping
    def project_and_task(self, record):
        assert (
            self.options.task_binding
            or self.options.project_binding
            or self.options.fallback_project
        )
        task_binding = self.options.task_binding
        if not task_binding:
            if self.options.fallback_project:
                return {"project_id": self.options.fallback_project.id}
            project = self.options.project_binding.odoo_id
            if project:
                return {
                    "project_id": project.id,
                    "jira_project_bind_id": self.options.project_binding.id,
                }

        project = task_binding.project_id
        return {
            "task_id": task_binding.odoo_id.id,
            "project_id": project.id,
            "jira_project_bind_id": task_binding.jira_project_bind_id.id,
        }

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}
