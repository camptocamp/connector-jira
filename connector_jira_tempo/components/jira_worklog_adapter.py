# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraWorklogAdapter(Component):
    _inherit = "jira.worklog.adapter"

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get("jira_worklog_no_tempo_timesheets_approval_data"):
            return worklog
        with self.handle_404():
            approval = self.tempo_timesheets_approval_read(worklog)
            worklog["_tempo_timesheets_approval"] = approval
        return worklog

    def tempo_timesheets_approval_read(self, worklog):
        url = self._tempo_timesheets_get_url("timesheet-approval/current")
        with self.handle_404():
            response = self.client._session.get(
                url,
                params={
                    "username": worklog["author"]["name"],
                },  # noqa
            )
        return response.json()

    def tempo_timesheets_approval_read_status_by_team(self, team_id, period_start):
        url = self._tempo_timesheets_get_url("timesheet-approval")
        params = {"teamId": team_id, "periodStartDate": period_start}
        with self.handle_404():
            response = self.client._session.get(url, params=params)
        return response.json()
