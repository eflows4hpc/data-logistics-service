from airflow.plugins_manager import AirflowPlugin

appbuilder_eFlows = {
    "name": "About eFlows4HPC",
    "href": "https://eflows4hpc.eu/",
}

class AirflowEFlowsPlugin(AirflowPlugin):
    name = "eFlowsLink"
    operators = []
    flask_blueprints = []
    hooks = []
    admin_views = []
    appbuilder_menu_items = [appbuilder_eFlows]

class AirflowDataCatPlugin(AirflowPlugin):
    name = "Data Catalog"
    operators = []
    flask_blueprints = []
    hooks = []
    admin_views = []
    appbuilder_menu_items = [{"name": "Data Catalog", "href": "https://datacatalog.fz-juelich.de/index.html"}]
