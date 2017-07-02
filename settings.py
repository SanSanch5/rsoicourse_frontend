from datetime import timedelta
import os

DEBUG_MODE = False
PORT = 5000
SESSION_EXPIRES_AFTER = timedelta(hours=1)

FRONTEND_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(FRONTEND_PATH, 'static')
UPLOAD_FOLDER = os.path.join(STATIC_PATH, 'img')

SERVICES_URI = {service: 'http://{}.herokuapp.com/api/{}'.format(domen, service) for domen, service in [
    ('rsoicourse-sessions', 'sessions'),
    ('rsoicourse-profiles', 'profiles'),
    ('rsoicourse-tasks', 'tasks'),
    ('rsoicourse-tasks', 'lessons'),
]}

