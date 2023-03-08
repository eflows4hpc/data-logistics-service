import os, random, string, logging
from authlib.integrations.flask_client import OAuth
from flask import url_for, redirect, current_app as app, Blueprint, abort
from flask_login import login_user
from flask_appbuilder import BaseView as AppBuilderBaseView
from airflow.plugins_manager import AirflowPlugin

log = logging.getLogger(__name__)
log.setLevel("DEBUG")

FAB_ADMIN_ROLE = "Admin"
FAB_VIEWER_ROLE = "Viewer"
FAB_PUBLIC_ROLE = "Public"  # The "Public" role is given no permissions

oauth = OAuth(app)
oauth.register(
    name='unity',
    client_id=os.getenv("OAUTH_CLIENT_ID"),
    server_metadata_url=os.getenv("OAUTH_METADATA_URL"),
    client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
    client_kwargs={'scope' : 'openid profile email eflows'}

)

unity = Blueprint('unity', __name__, url_prefix="/unity")

class UnityIntegrationView(AppBuilderBaseView):

    @unity.route('/')
    @unity.route('/login')
    def login():
        redirect_uri = url_for('.authorize', _external=True)
        log.debug("Redirect uri is '" + str(redirect_uri) + "'")
        log.debug("Metadata uri is '" + str(os.getenv("OAUTH_METADATA_URL")) + "'")
        return oauth.unity.authorize_redirect(redirect_uri)
    
    @unity.route('/authorize')
    def authorize():
        try:
            token = oauth.unity.authorize_access_token()
        except:
            abort(403)
        user = oauth.unity.userinfo(token=token)
        # get relevant data from token
        log.debug(str(user))
        email = user['email']
        persistent_identifier = user["sub"]
        first_name = user["firstname"]
        last_name = user["surname"]
        admin_access = user.get('eflows:dlsAccess', False)

        log.debug("SSO user logging in...")
        log.debug("sub : " + persistent_identifier)
        log.debug("first name : " + first_name)
        log.debug("last name : " + last_name)
        log.debug("email : " + email)
        log.debug("admin : " + admin_access)
        log.debug("......................")

        role = FAB_VIEWER_ROLE
        if admin_access:
            role = FAB_ADMIN_ROLE

        # check airflow user backend
        # check if user already exists, if not create it (with long random password)
        sec_manager = app.appbuilder.sm
        fab_user = sec_manager.find_user(username=persistent_identifier)
        log.debug("Searching for user by name gave '" + (str(fab_user)) + "'")

        if fab_user is None: # TODO check if None is the rioght thing to compare to
            log.debug("Trying to create non-existing user")
            characters = string.ascii_letters + string.digits + string.punctuation
            fab_user = sec_manager.add_user(
                username=persistent_identifier,
                first_name=first_name,
                last_name=last_name,
                email=email,
                role=sec_manager.find_role(role),
                password=''.join(random.choice(characters) for i in range(20))
            )
        # login as that user
        login_user(fab_user, remember=False)
        return redirect(url_for('home'))
    
    @unity.route('/logout')
    def logout():
        pass

class UnityIntegrationPlugin(AirflowPlugin):
    name = "Unity Integration"
    flask_blueprints = [unity]