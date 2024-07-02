# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from itertools import groupby

from odoo.addons.component.core import Component


class JiraResUsersAdapter(Component):
    _name = "jira.res.users.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.res.users"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.user(id_).raw

    def search(self, fragment=None):
        """Search users

        :param fragment: a string to match usernames, name or email against.
        """
        users = self.client.search_users(
            query=fragment, maxResults=None, includeActive=True, includeInactive=True
        )

        # User 'accountId' is unique and if same key appears several times, it means
        # that same user is present in multiple User Directories
        users = list(
            map(
                lambda group: list(group[1])[0],
                groupby(users, key=lambda user: user.accountId),
            )
        )

        return users
