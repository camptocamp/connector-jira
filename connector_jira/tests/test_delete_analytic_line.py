# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from mock import patch

import odoo
from odoo.addons.connector.exception import IDMissingInBackend

from .common import JiraSavepointCase, recorder


class TestBatchTimestampDelete(JiraSavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_issue_type_bindings()
        cls.epic_issue_type = cls.env["jira.issue.type"].search([("name", "=", "Epic")])
        cls.project = cls.env["project.project"].create({"name": "Jira Project"})

    @recorder.use_cassette
    def test_delete_analytic_line(self):
        """Test deletion of a single worklogs"""

        # Simulate a worklogs we would already have imported and is
        # deleted in Jira. First create the binding as it would be
        # in Odoo.
        line = self.env["account.analytic.line"].create(
            {
                "project_id": self.project.id,
                "amount": 30.0,
                "date": "2019-04-08",
                "name": "A worklog that will be deleted",
                "user_id": self.env.user.id,
            }
        )
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        binding = self._create_analytic_line_binding(
            line, jira_issue_id="10101", external_id="10103",
        )
        # This is usually delayed as a job from either a controller,
        # either the component with usage "timestamp.batch.deleter"
        self.env["jira.account.analytic.line"].delete_record(
            self.backend_record, "10103", only_binding=False, set_inactive=False
        )

        self.assertFalse(binding.exists())
        self.assertFalse(line.exists())

    def test_delete_analytic_line_check_removed(self):
        """Test that with check we can delete a worklogs that was removed"""

        module = odoo.addons.connector_jira
        WorklogAdapter = module.models.account_analytic_line.common.WorklogAdapter

        # Simulate a worklogs we would already have imported and is
        # deleted in Jira. First create the binding as it would be
        # in Odoo.
        line = self.env["account.analytic.line"].create(
            {
                "project_id": self.project.id,
                "amount": 30.0,
                "date": "2019-04-08",
                "name": "A worklog that will be deleted",
                "user_id": self.env.user.id,
            }
        )
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        binding = self._create_analytic_line_binding(
            line, jira_issue_id="10101", external_id="10103",
        )

        def raiseIDMissing(*args, **kwargs):
            raise IDMissingInBackend

        with patch.object(WorklogAdapter, 'read', raiseIDMissing):
            # This is usually delayed as a job from either a controller,
            # either the component with usage "timestamp.batch.deleter"
            self.env["jira.account.analytic.line"].delete_record(
                self.backend_record, "10103", issue_id="10101", only_binding=False,
                set_inactive=False, check_ext=True
            )
        self.assertFalse(binding.exists())
        self.assertFalse(line.exists())

    def test_delete_analytic_line_check_exists(self):
        """Test that with check we can't delete of a worklogs that still exists"""

        module = odoo.addons.connector_jira
        WorklogAdapter = module.models.account_analytic_line.common.WorklogAdapter

        # Simulate a worklogs we would already have imported and is
        # deleted in Jira. First create the binding as it would be
        # in Odoo.
        line = self.env["account.analytic.line"].create(
            {
                "project_id": self.project.id,
                "amount": 30.0,
                "date": "2019-04-08",
                "name": "A worklog that will NOT be deleted",
                "user_id": self.env.user.id,
            }
        )
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        binding = self._create_analytic_line_binding(
            line, jira_issue_id="10101", external_id="10103",
        )

        with patch.object(WorklogAdapter, 'read', lambda *args, **kwargs: True):
            # This is usually delayed as a job from either a controller,
            # either the component with usage "timestamp.batch.deleter"
            res = self.env["jira.account.analytic.line"].delete_record(
                self.backend_record, "10103", issue_id="10101", only_binding=False,
                set_inactive=False, check_ext=True
            )
        expected_msg = (
            "Wrongfully trying to delete a resource that still exists in Jira"
        )
        self.assertEqual(res, expected_msg)
        self.assertTrue(binding.exists())
        self.assertTrue(line.exists())
