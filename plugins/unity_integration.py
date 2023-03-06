import os, random, string
from authlib.integrations.flask_client import OAuth
from flask import url_for, redirect, current_app as app
from flask_login import login_user
from flask_appbuilder import expose, BaseView as AppBuilderBaseView
from airflow.plugins_manager import AirflowPlugin
import logging
import os

log = logging.getLogger(__name__)
log.setLevel(os.getenv("AIRFLOW__LOGGING__FAB_LOGGING_LEVEL", "INFO"))

FAB_ADMIN_ROLE = "Admin"
FAB_VIEWER_ROLE = "Viewer"
FAB_PUBLIC_ROLE = "Public"  # The "Public" role is given no permissions

oauth = OAuth(app)
oauth.register(
    name='unity',
    client_id=os.getenv("OAUTH_CLIENT_ID"),
    server_metadata_url=os.getenv("OAUTH_METADATA_URL"),
    client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
    client_kwargs={
        'scope' : 'openid email profile eflows'
    }

)

class UnityIntegrationLoginView(AppBuilderBaseView):
    @expose("/unity_login")
    #@app.route('/unity_login')
    def unity_login():
        redirect_uri = url_for('unity_authorize', _external=True)
        return oauth.unity.authorize_redirect(redirect_uri)
class UnityIntegrationAuthView(AppBuilderBaseView):
    @expose("/unity_authorize")
    #@app.route('/unity_authorize')
    async def authorize():
        token = await oauth.unity.authorize_access_token()
        user = await oauth.unity.userinfo(token=token)
        # get relevant data from token
        email = user['email']
        persistent_identifier = user["sub"]
        first_name = user["given_name"]
        last_name = user["family_name"]
        admin_access = user.get('eflows:dlsAccess', False)
        role = FAB_VIEWER_ROLE
        if admin_access:
            role = FAB_ADMIN_ROLE

        # check airflow user backend
        # check if user already exists, if not create it (with long random password)
        sec_manager = app.appbuilder.sm
        fab_user = sec_manager.find_user(username=persistent_identifier)
        if fab_user is None: # TODO check if None is the rioght thing to compare to
            characters = string.ascii_letters + string.digits + string.punctuation
            fab_user = sec_manager.add_user(
                username=persistent_identifier,
                first_name=first_name,
                last_name=last_name,
                email=email,
                role=role,
                password=''.join(random.choice(characters) for i in range(20))
            )
        # login as that user
        login_user(fab_user, remember=False)
        return redirect('/')

v_unity_login_view = UnityIntegrationLoginView()
v_unity_login_package = {
    "name": "Unity Login View",
    "category": "Unity Integration",
    "view": v_unity_login_view,
}

v_unity_auth_view = UnityIntegrationAuthView()
v_unity_auth_package = {
    "name": "Unity Auth View",
    "category": "Unity Integration",
    "view": v_unity_auth_view,
}

class UnityIntegrationPlugin(AirflowPlugin):
    name = "unity_integration"
    appbuilder_views = [v_unity_auth_package, v_unity_login_package]