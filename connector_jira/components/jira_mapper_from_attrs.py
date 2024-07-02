# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraMapperFromAttrs(Component):
    _name = "jira.mapper.from.attrs"
    _inherit = ["jira.base"]
    _usage = "map.from.attrs"

    def values(self, record, mapper_):
        values = {}
        from_fields_mappings = getattr(mapper_, "from_fields", [])
        fields_values = record.get("fields", {})
        for source, target in from_fields_mappings:
            values[target] = mapper_._map_direct(fields_values, source, target)
        return values
