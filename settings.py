from datetime import timedelta
import os

DEBUG_MODE = True
PORT = 5000
SESSION_EXPIRES_AFTER = timedelta(hours=1)

FRONTEND_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(FRONTEND_PATH, 'static')
UPLOAD_FOLDER = os.path.join(STATIC_PATH, 'img')


#SERVICES_URI = {service: 'http://localhost:{}/api/{}'.format(port, service) for service, port in [
#    ('sessions', 5001),
#    ('profiles', 5002),
#    ('tasks', 5003),
#    ('lessons', 5003),
#]}

SERVICES_URI = {service: 'https://{}.herokuapp.com/api/{}'.format(domen, service) for domen, service in [
    ('rsoicourse-sessions', 'sessions'),
    ('rsoicourse-profiles', 'profiles'),
    ('rsoicourse-tasks', 'tasks'),
    ('rsoicourse-tasks', 'lessons'),
]}

