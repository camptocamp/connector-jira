# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
from collections import namedtuple

from odoo.addons.component.core import Component

UpdatedWorklog = namedtuple(
    "UpdatedWorklog",
    "worklog_id updated",
    # id as integer, timestamp
)

UpdatedWorklogSince = namedtuple(
    "UpdatedWorklogSince",
    "since until updated_worklogs",
    # timestamp, timestamp, [UpdatedWorklog]
)


DeletedWorklogSince = namedtuple(
    "DeletedWorklogSince",
    "since until deleted_worklog_ids",
    # timestamp, timestamp, [ids as integer]
)


class WorklogAdapter(Component):
    _name = "jira.worklog.adapter"
    _inherit = "jira.webservice.adapter"
    _apply_on = ["jira.account.analytic.line"]

    def read(self, issue_id, worklog_id):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """Search worklogs of an issue"""
        worklogs = self.client.worklogs(issue_id)
        return [worklog.id for worklog in worklogs]

    @staticmethod
    def _chunks(whole, size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(whole), size):
            yield whole[i : i + size]

    def yield_read(self, worklog_ids):
        """Generator returning worklog ids data"""
        path = "worklog/list"

        # the method returns max 1000 results
        for chunk in self._chunks(worklog_ids, 1000):
            payload = json.dumps({"ids": chunk})
            result = self._post_get_json(path, data=payload)
            yield from result

    def updated_since(self, since=None):
        path = "worklog/updated"

        start_since = since
        updated_worklogs = []

        while True:
            result = self.client._get_json(path, params={"since": since})
            updated_worklogs += [
                UpdatedWorklog(worklog_id=row["worklogId"], updated=row["updatedTime"])
                for row in result["values"]
            ]
            until = since = result["until"]
            if result["lastPage"]:
                break
        return UpdatedWorklogSince(
            since=start_since, until=until, updated_worklogs=updated_worklogs
        )

    def deleted_since(self, since=None):
        path = "worklog/deleted"

        start_since = since
        deleted_worklog_ids = []

        while True:
            result = self.client._get_json(path, params={"since": since})
            deleted_worklog_ids += [row["worklogId"] for row in result["values"]]
            until = since = result["until"]
            if result["lastPage"]:
                break
        return DeletedWorklogSince(
            since=start_since, until=until, deleted_worklog_ids=deleted_worklog_ids
        )
