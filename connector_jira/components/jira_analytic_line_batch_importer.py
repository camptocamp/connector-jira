# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo.addons.component.core import Component

from ..fields import MilliDatetime

_logger = logging.getLogger(__name__)


class JiraAnalyticLineBatchImporter(Component):
    """Import the Jira worklogs

    For every id in in the list, a delayed job is created.
    Import from a date
    """

    _name = "jira.analytic.line.batch.importer"
    _inherit = "jira.timestamp.batch.importer"
    _apply_on = ["jira.account.analytic.line"]

    def _search(self, timestamp):
        unix_timestamp = MilliDatetime.to_timestamp(timestamp.last_timestamp)
        result = self.backend_adapter.updated_since(since=unix_timestamp)
        worklog_ids = self._filter_update(result.updated_worklogs)
        # We need issue_id + worklog_id for the worklog importer (the jira
        # "read" method for worklogs asks both), get it from yield_read.
        # TODO we might consider to optimize the import process here:
        # yield_read reads worklogs data, then the individual
        # import will do a request again (and 2 with the tempo module)
        next_timestamp = MilliDatetime.from_timestamp(result.until)
        return (next_timestamp, self.backend_adapter.yield_read(worklog_ids))

    def _handle_records(self, records, force=False):
        count = 0
        for worklog in records:
            count += 1
            worklog_id = worklog["id"]
            issue_id = worklog["issueId"]
            self._import_record(issue_id, worklog_id, force=force)
        return count

    def _filter_update(self, updated_worklogs):
        """Filter only the worklogs needing an update

        The result from Jira contains the worklog id and
        the last update on Jira. So we keep only the worklog
        ids with an sync_date before the Jira last update.
        """
        if not updated_worklogs:
            return []
        self.env.cr.execute(
            "SELECT external_id, jira_updated_at "
            "FROM jira_account_analytic_line "
            "WHERE external_id IN %s ",
            (tuple(str(r.worklog_id) for r in updated_worklogs),),
        )
        bindings = {int(row[0]): row[1] for row in self.env.cr.fetchall()}
        worklog_ids = []
        for worklog in updated_worklogs:
            worklog_id = worklog.worklog_id
            # we store the latest "updated_at" value on the binding
            # so we can check if we already know the latest value,
            # for instance because we imported the record from a
            # webhook before, we can skip the import
            binding_updated_at = bindings.get(worklog_id)
            if not binding_updated_at:
                worklog_ids.append(worklog_id)
                continue
            binding_updated_at = MilliDatetime.from_string(binding_updated_at)
            jira_updated_at = MilliDatetime.from_timestamp(worklog.updated)
            if binding_updated_at < jira_updated_at:
                worklog_ids.append(worklog_id)
        return worklog_ids

    def _import_record(self, issue_id, worklog_id, force=False, **kwargs):
        """Delay the import of the records"""
        self.model.with_delay(**kwargs).import_record(
            self.backend_record,
            issue_id,
            worklog_id,
            force=force,
        )
