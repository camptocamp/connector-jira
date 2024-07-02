# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Receive webhooks from Jira


(Outdated) JIRA could well send all the data in the webhook request's body,
which would avoid Odoo to make another GET to get this data, but
JIRA webhooks are potentially insecure as we don't know if it really
comes from JIRA. So we don't use the data sent by the webhook and the job
gets the data by itself (with the nice side-effect that the job is retryable).

TODO: we now have authenticated calls from Jira through the JWT tokens, so we
 could move back to a setup where we avoid querying the data back to Jira.
 Changing this is on the roadmap.

"""

import logging

import odoo
from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):
    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/issue",
        type="json",
        auth="none",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def webhook_issue(self, backend_id, issue_id=None, **kw):
        ensure_db()
        import pprint

        pprint.pprint(request.get_json_data())
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        backend = env["jira.backend"].search(
            [("id", "=", backend_id), ("state", "=", "running")]
        )
        if not backend:
            _logger.warning(
                "Received an Issue webhook from Jira for backend %d but cannot find a "
                "matching running backend",
                backend_id,
            )
            return
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        action = request.get_json_data()["webhookEvent"]

        payload = request.get_json_data()["issue"]
        issue_id = payload["id"]

        delayable_model = env["jira.project.task"].with_delay()
        if action == "jira:issue_deleted":
            delayable_model.delete_record(backend, issue_id)
        else:
            delayable_model.import_record(backend, issue_id)

    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/worklog",
        type="json",
        auth="none",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def webhook_worklog(self, backend_id, **kw):
        ensure_db()
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        backend = env["jira.backend"].search(
            [("id", "=", backend_id), ("state", "=", "running")]
        )
        if not backend:
            _logger.warning(
                "Received a Worklog webhook from Jira for backend %d but cannot find a "
                "matching runnign backend",
                backend_id,
            )
            return
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        action = request.get_json_data()["webhookEvent"]

        payload = request.get_json_data()["worklog"]

        issue_id = payload["issueId"]
        worklog_id = payload["id"]

        if action == "worklog_deleted":
            env["jira.account.analytic.line"].with_delay(
                description=_("Delete a local worklog which has been deleted on JIRA")
            ).delete_record(backend, worklog_id)
        else:
            env["jira.account.analytic.line"].with_delay(
                description=_("Import a worklog from JIRA")
            ).import_record(backend, issue_id, worklog_id)
