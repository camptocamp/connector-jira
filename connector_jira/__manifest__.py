# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "JIRA Connector",
    "version": "17.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Connector",
    "depends": [
        # Odoo community
        "project",
        "hr_timesheet",
        "web",
        # OCA/connector
        "connector",
        # OCA/queue
        "queue_job",
        # OCA/server-ux
        "multi_step_wizard",
        # OCA/web
        "web_widget_url_advanced",
    ],
    "external_dependencies": {
        "python": [
            "requests>=2.21.0",
            "jira>=2.0.0",
            "oauthlib>=2.1.0",
            "requests-oauthlib>=1.1.0",
            "requests-toolbelt>=0.9.1",
            "requests-jwt>=0.6.0",
            "PyJWT>=1.7.1,<2.9.0",
            "cryptography>=38,<39",  # Compatibility w/ Odoo 17.0 requirements
            "atlassian_jwt>=3.0.0",
        ],
    },
    "website": "https://github.com/OCA/connector-jira",
    "data": [
        "views/jira_menus.xml",
        "views/project_link_jira_views.xml",
        "views/task_link_jira_views.xml",
        "views/jira_backend_views.xml",
        "views/jira_backend_report_templates.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/res_users_views.xml",
        "views/jira_issue_type_views.xml",
        "views/timesheet_account_analytic_line.xml",
        "wizards/jira_account_analytic_line_import_views.xml",
        "security/ir.model.access.csv",
        "data/cron.xml",
        "data/queue_job_data.xml",
    ],
    "demo": ["demo/jira_backend_demo.xml"],
    "installable": True,
}
