import flask
import requests
from datetime import datetime

from settings import SERVICES_URI, SESSION_EXPIRES_AFTER
from tools import parse_datetime, render_datetime


class Session(dict, flask.sessions.SessionMixin):
    def __init__(self, json, **kwargs):
        super().__init__(**kwargs)
        self.id = json['id']
        self.user_id = json['user_id']
        self.data = {item['key']: item['value'] for item in json['data_items']}

    @property
    def data(self):
        return self

    @data.setter
    def data(self, data):
        self.clear()
        self.update(data)

    def to_json(self):
        return {
            'user_id': self.user_id,
            'last_used_at': render_datetime(datetime.now()),
            'data_items': [{'key': key, 'value': value} for key, value in self.data.items()]
        }


class SessionInterface(flask.sessions.SessionInterface):
    def open_session(self, app, request):
        try:
            if 'session_id' in request.cookies:
                session_response = requests.get(SERVICES_URI['sessions'] + '/' + request.cookies['session_id'])
                if session_response.status_code == 200:
                    session = session_response.json()
                    if parse_datetime(session['last_used_at']) + SESSION_EXPIRES_AFTER > datetime.now():
                        return Session(session)

            session_response = requests.post(SERVICES_URI['sessions'], json={
                'last_used_at': render_datetime(datetime.now()),
            })
            if session_response.status_code == 201:
                session = session_response.json()
                return Session(session)
        except requests.exceptions.RequestException:
            return Session({
                'id': None,
                'user_id': None,
                'data_items': [],
            })

    def save_session(self, app, session, response):
        if session.id is None:
            response.set_cookie('session_id', '', expires=0)
            return

        try:
            session_response = requests.patch(SERVICES_URI['sessions'] + '/' + str(session.id), json=session.to_json())
            if session_response.status_code == 200:
                response.set_cookie('session_id', str(session.id))
        except requests.exceptions.RequestException:
            pass
