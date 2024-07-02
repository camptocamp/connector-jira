# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class JiraProjectTaskMapper(Component):
    _name = "jira.project.task.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.project.task"]

    direct = [("key", "jira_key")]

    from_fields = [("duedate", "date_deadline")]

    @mapping
    def from_attributes(self, record):
        return self.component(usage="map.from.attrs").values(record, self)

    @mapping
    def name(self, record):
        # On an Epic, you have 2 fields:

        #     a field like 'customfield_10003' labelled "Epic Name"
        #     a field 'summary' labelled "Sumarry"

        # The other types of tasks have only the 'summary' field, the other is
        # empty. To simplify, we always try to read the Epic Name, which
        # will always be empty for other types.
        epic_name_field = self.backend_record.epic_name_field_name
        name = False
        if epic_name_field:
            name = record["fields"].get(epic_name_field)
        if not name:
            name = record["fields"]["summary"]
        return {"name": name}

    @mapping
    def issue_type(self, record):
        binder = self.binder_for("jira.issue.type")
        jira_type_id = record["fields"]["issuetype"]["id"]
        binding = binder.to_internal(jira_type_id)
        return {"jira_issue_type_id": binding.id}

    @mapping
    def assignee(self, record):
        assignee = record["fields"].get("assignee")
        if not assignee:
            return {"user_ids": False}
        jira_key = assignee["accountId"]
        binder = self.binder_for("jira.res.users")
        user = binder.to_internal(jira_key, unwrap=True)
        if not user:
            email = assignee.get("emailAddress")
            raise MappingError(
                _(
                    'No user found with accountId "%(jira_key)s" or email "%(email)s".'
                    "You must create a user or link it manually if the "
                    "login/email differs.",
                    jira_key=jira_key,
                    email=email,
                )
            )
        return {"user_id": user.id}

    @mapping
    def description(self, record):
        return {"description": record["renderedFields"]["description"]}

    @mapping
    def project(self, record):
        binder = self.binder_for("jira.project.project")
        project = binder.unwrap_binding(self.options.project_binding)
        values = {
            "project_id": project.id,
            "company_id": project.company_id.id,
            "jira_project_bind_id": self.options.project_binding.id,
        }
        if not project.active:
            values["active"] = False
        return values

    @mapping
    def epic(self, record):
        if not self.options.jira_epic:
            return {}
        jira_epic_id = self.options.jira_epic["id"]
        binder = self.binder_for("jira.project.task")
        binding = binder.to_internal(jira_epic_id)
        return {"jira_epic_link_id": binding.id}

    @mapping
    def parent(self, record):
        jira_parent = record["fields"].get("parent")
        if not jira_parent:
            return {}
        jira_parent_id = jira_parent["id"]
        binder = self.binder_for("jira.project.task")
        binding = binder.to_internal(jira_parent_id)
        return {"jira_parent_id": binding.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def status(self, record):
        status = record["fields"].get("status", {})
        status_name = status.get("name")
        if not status_name:
            return {"stage_id": False}
        project_binder = self.binder_for("jira.project.project")
        project_id = project_binder.unwrap_binding(self.options.project_binding)
        stage = self.env["project.task.type"].search(
            [("name", "=", status_name), ("project_ids", "=", project_id.id)],
            limit=1,
        )
        return {"stage_id": stage.id}

    @mapping
    def time_estimate(self, record):
        original_estimate = record["fields"].get("timeoriginalestimate")
        if not original_estimate:
            return {"planned_hours": False}
        return {"planned_hours": float(original_estimate) / 3600.0}

    def finalize(self, map_record, values):
        values = values.copy()
        if values.get("odoo_id"):
            # If a mapping binds the issue to an existing odoo
            # task, we should not change the project.
            # It's not only unexpected, but would fail as soon
            # as we have invoiced timesheet lines on the task.
            values.pop("project_id")
        return values
