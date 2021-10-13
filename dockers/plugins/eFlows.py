from airflow.plugins_manager import AirflowPlugin
from flask_admin.base import MenuLink

appbuilder_eFlows = {
    "name": "More about eFlows4HPC",
    "href": "https://eflows4hpc.eu/",
}

class AirflowEFlowsPlugin(AirflowPlugin):
    name = "eFlowsLink"
    operators = []
    flask_blueprints = []
    hooks = []
    admin_views = []
    appbuilder_menu_items = [appbuilder_eFlows]