# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import tempfile

from odoo import _, exceptions

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

try:
    from jira import JIRAError
    from jira.utils import json_loads
except ImportError as err:
    _logger.debug(err)


class JiraProjectAdapter(Component):
    _name = "jira.project.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.project.project"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.get(id_).raw

    def get(self, id_):
        with self.handle_404():
            return self.client.project(id_)

    def write(self, id_, values):
        super().write(id_, values)
        with self.handle_404():
            return self.get(id_).update(values)

    def create(self, key=None, name=None, template_name=None, values=None):
        super().create(key=key, name=name, template_name=template_name, values=values)
        project = self.client.create_project(
            key=key,
            name=name,
            template_name=template_name,
        )
        if values:
            project.update(values)
        return project

    def create_shared(self, key=None, name=None, shared_key=None, lead=None):
        assert key and name and shared_key
        # There is no public method for creating a shared project:
        # https://jira.atlassian.com/browse/JRA-45929
        # People found a private method for doing so, which is explained on:
        # https://jira.atlassian.com/browse/JRASERVER-27256

        try:
            project = self.read(shared_key)
            project_id = project["id"]
        except JIRAError as err:
            if err.status_code == 404:
                raise exceptions.UserError(
                    _('Project template with key "%s" not found.') % shared_key
                ) from err
            else:
                raise

        url = (
            self.client._options["server"]
            + "/rest/project-templates/1.0/createshared/%s" % project_id
        )
        payload = {
            "name": name,
            "key": key,
            "lead": lead,
        }

        r = self.client._session.post(url, data=json.dumps(payload))
        if r.status_code == 200:
            r_json = json_loads(r)
            return r_json

        f = tempfile.NamedTemporaryFile(
            suffix=".html",
            prefix="python-jira-error-create-shared-project-",
            delete=False,
        )
        f.write(r.text)

        if self.logging:
            _logger.error(
                "Unexpected result while running create shared project."
                f" Server response saved in {f.name} for further investigation"
                f" [HTTP response={r.status_code}]."
            )
        return False
