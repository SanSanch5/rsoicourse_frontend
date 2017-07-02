import requests
import simplejson
from urllib.parse import unquote as urldecode
from werkzeug.utils import secure_filename
from datetime import datetime

import os
import flask

from session_interface import SessionInterface
from settings import DEBUG_MODE, PORT, SERVICES_URI, UPLOAD_FOLDER
from tools import hash_password, render_datetime


app = flask.Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.session_interface = SessionInterface()


@app.route('/', methods=['GET'])
def index():
    return flask.redirect('/lessons')


@app.route('/register', methods=['GET'])
def register():
    if 'redirect_to' in flask.request.args:
        flask.session['redirect_to'] = urldecode(flask.request.args['redirect_to'])

    if flask.session.user_id is not None:
        return flask.redirect('/me')

    # get all tutors
    try:
        tutors = get_tutors()
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 503

    return flask.render_template('profile/register_form.html', tutors=tutors)


@app.route('/register', methods=['POST'])
def post_to_register():
    password_hash = hash_password(flask.request.form['password'])
    name = flask.request.form['name']
    middle_name = flask.request.form['midname']
    surname = flask.request.form['surname']
    phone = flask.request.form['phone']

    role = flask.request.form['role']
    group = None if role == 'tutor' else flask.request.form['group']
    tutor_id = None if role == 'tutor' else flask.request.form.get('tutor', None)

    about = flask.request.form.get('brief', None)
    photo_file = flask.request.files['avatar']
    photo_filename = secure_filename(photo_file.filename)

    # дополнительная необязательная информация
    email = flask.request.form.get('email', None)

    try:
        user_response = requests.post(SERVICES_URI['profiles'], json={
            'name': name,
            'surname': surname,
            'middle_name': middle_name,
            'phone': phone,
            'password_hash': password_hash,
            'email': email,
            'role': role,
            'group': group,
            'tutor_id': tutor_id,
            'about': about,
            'photo': photo_filename,
        })
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 503

    if user_response.status_code == 201:
        user_upload_path = os.path.join(app.config['UPLOAD_FOLDER'], phone)
        if not os.path.exists(user_upload_path):
            os.makedirs(user_upload_path)
        photo_path = os.path.join(user_upload_path, photo_filename)
        photo_file.save(photo_path)

        user = user_response.json()
        flask.session.user_id = user['id']

        return flask.redirect(flask.session.pop('redirect_to', '/me'), code=303)

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/sign_in', methods=['GET'])
def sign_in():
    if 'redirect_to' in flask.request.args:
        flask.session['redirect_to'] = urldecode(flask.request.args['redirect_to'])

    if flask.session.user_id is not None:
        return flask.redirect('/me')

    return flask.render_template('profile/authorize_form.html')


@app.route('/sign_in', methods=['POST'])
def post_to_sign_in():
    try:
        user_response = requests.get(SERVICES_URI['profiles'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'phone', 'op': '==', 'val': flask.request.form['phone']},
                    {'name': 'password_hash', 'op': '==', 'val': hash_password(flask.request.form['password'])},
                ],
                'single': True,
            }),
        })
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 503

    if user_response.status_code == 200:
        user = user_response.json()
        flask.session.user_id = user['id']
        return flask.redirect(flask.session.pop('redirect_to', '/me'), code=303)

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/me', methods=['GET'])
def me():
    if flask.session.user_id is None:
        flask.session['redirect_to'] = '/me'
        return flask.redirect('/sign_in')

    try:
        user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
        tutors = get_tutors()
        assert user_response.status_code == 200
        user = user_response.json()
    except requests.exceptions.RequestException:
        user = None

    profile_photo_name = os.path.join(user['phone'], user['photo'])
    return flask.render_template('profile/me.html',
                                 user=user, tutors=tutors,
                                 user_photo_path=flask.url_for(
                                     'static',
                                     filename=os.path.join("img", profile_photo_name)
                                 ))


@app.route('/me', methods=['POST'])
def patch_me():
    user = dict()
    user['password_hash'] = hash_password(flask.request.form['password'])
    user['name'] = flask.request.form['name']
    user['middle_name'] = flask.request.form['midname']
    user['surname'] = flask.request.form['surname']
    user['phone'] = flask.request.form['phone']

    user['group'] = flask.request.form.get('group', None)
    user['tutor_id'] = flask.request.form.get('tutor', None)
    user['about'] = flask.request.form.get('brief', None)

    # дополнительная необязательная информация
    user['email'] = flask.request.form.get('email', None)

    try:
        user_response = requests.patch(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id), json=user)
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис пользователей недоступен'), 503

    if user_response.status_code == 200:
        user = user_response.json()
        profile_photo_name = os.path.join(user['phone'], user['photo'])
        return flask.render_template('profile/me.html',
                                     user=user, tutors=get_tutors(),
                                     user_photo_path=flask.url_for(
                                         'static',
                                         filename=os.path.join("img", profile_photo_name)
                                     ))

    return flask.render_template('error.html', reason=user_response.json()), 500


@app.route('/lessons', methods=['GET'])
def get_lessons():
    if flask.session.user_id is None:
        flask.session['redirect_to'] = '/lessons'
        return flask.redirect('/sign_in')

    user_role = None
    tutor_id = None
    if flask.session.user_id is not None:
        try:
            user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
            if user_response.status_code != 200:
                return flask.render_template('error.html', reason=user_response.json()), 500

            user = user_response.json()
            user_role = user['role']
            tutor_id = user['tutor_id'] if user_role == 'student' else user['id']
        except requests.exceptions.RequestException:
            pass

    try:
        lessons_response = requests.get(SERVICES_URI['lessons'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'tutor_id', 'op': '==', 'val': tutor_id},
                ],
            }),
        })
        assert lessons_response.status_code == 200
        lessons = lessons_response.json()
        lessons = lessons['objects']
        if user_role == 'tutor':
            # для преподавателя это будут все уроки, где есть непроверенные ответы
            selected_lessons = [l for l in lessons if None in [ans['mark'] for ans in l['answers']]]
        else:
            # для студента - все недорешенные уроки
            selected_lessons = [l for l in lessons if l['task_id'] is not None and flask.session.user_id not in
                                [ans['student_id'] for ans in l['answers']]]

    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис заданий недоступен'), 503

    return flask.render_template('tasks/lessons.html',
                                 user_role=user_role,
                                 selected_lessons=selected_lessons,
                                 lessons=lessons)


@app.route('/lessons', methods=['POST'])
def create_lesson():
    lesson = dict()
    lesson['number'] = flask.request.form['new_lesson']
    lesson['tutor_id'] = flask.session.user_id
    lesson['created_at'] = render_datetime(datetime.now())

    try:
        lesson_response = requests.post(SERVICES_URI['lessons'], json=lesson)
    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис заданий недоступен'), 503

    if lesson_response.status_code == 201:
        return flask.redirect("/lessons/%s" % lesson['number'], code=303)

    return flask.render_template('error.html', reason=lesson_response.json()), 500


@app.route('/lessons/<number>', methods=['GET'])
def get_lesson(number):
    if flask.session.user_id is None:
        flask.session['redirect_to'] = "/lessons/%s" % number
        return flask.redirect('/sign_in')

    user_role = None
    tutor_id = None
    task = None
    answer = None
    if flask.session.user_id is not None:
        try:
            user_response = requests.get(SERVICES_URI['profiles'] + '/' + str(flask.session.user_id))
            if user_response.status_code != 200:
                return flask.render_template('error.html', reason=user_response.json()), 500

            user = user_response.json()
            user_role = user['role']
            tutor_id = user['tutor_id'] if user_role == 'student' else user['id']
        except requests.exceptions.RequestException:
            pass

    try:
        lesson_response = requests.get(SERVICES_URI['lessons'], params={
            'q': simplejson.dumps({
                'filters': [
                    {'name': 'tutor_id', 'op': '==', 'val': tutor_id},
                    {'name': 'number', 'op': '==', 'val': number},
                ],
            }),
        })
        assert lesson_response.status_code == 200
        lesson = lesson_response.json()['objects']
        lesson = None if len(lesson) == 0 else lesson[0]

        if lesson:
            if lesson['task_id'] is not None:
                task_response = requests.get(SERVICES_URI['tasks'] + "/%d" % lesson['task_id'])
                assert task_response.status_code == 200
                task = task_response.json()
            if user_role == 'student':
                student_answers = [ans for ans in lesson['answers'] if ans['student_id'] == user['id']]
                if len(student_answers) > 0:
                    assert len(student_answers) == 1
                    answer = student_answers[0]
            else:
                for ans in lesson['answers']:
                    student = requests.get(SERVICES_URI['profiles'] + "/%s" % ans['student_id']).json()
                    ans['student_name'] = student['name']
                    ans['student_surname'] = student['surname']
                    ans['student_midname'] = student['middle_name']
    except requests.exceptions.RequestException:
        lesson = None

    return flask.render_template('tasks/lesson.html',
                                 user_role=user_role,
                                 lesson=lesson,
                                 task=task,
                                 answer=answer)


@app.route('/lessons/<number>', methods=['POST'])
def update_lesson(number):
    try:
        print(flask.request.form)
        if 'create_task' in flask.request.form:
            task = dict()
            task['task'] = flask.request.form['task']
            task['created_at'] = render_datetime(datetime.now())
            task['last_updated_at'] = render_datetime(datetime.now())

            task_response = requests.post(SERVICES_URI['tasks'], json=task)
            if task_response.status_code == 201:
                created_task = task_response.json()
                requests.patch(SERVICES_URI['lessons'] + '/' + str(flask.request.form['lesson_id']),
                               json={'task_id': created_task['id']})
                return flask.redirect("/lessons/%s" % number)

            return flask.render_template('error.html', reason=task_response.json()), 500

        elif 'update_task' in flask.request.form:
            task = dict()
            task['task'] = flask.request.form['task']
            task['last_updated_at'] = render_datetime(datetime.now())

            task_response = requests.patch("%s/%s" % (SERVICES_URI['tasks'], flask.request.form['task_id']),
                                           json=task)
            if task_response.status_code == 200:
                return flask.redirect("/lessons/%s" % number)

            return flask.render_template('error.html', reason=task_response.json()), 500

        elif 'update_answer' in flask.request.form:
            lesson_response = requests.get("%s/%s" % (SERVICES_URI['lessons'], flask.request.form['lesson_id']))
            answers = lesson_response.json()['answers']
            student_answers_indexes = [ind for ind, ans in enumerate(answers)
                                       if ans['student_id'] == flask.session.user_id]
            if len(student_answers_indexes) > 0:
                assert len(student_answers_indexes) == 1
                answer = answers[student_answers_indexes[0]]
                answer['mark'] = None
            else:
                answer = dict()
                answer['student_id'] = flask.session.user_id
                answer['created_at'] = render_datetime(datetime.now())
                answers.append(answer)

            answer['answer'] = flask.request.form['answer']
            answer['last_updated_at'] = render_datetime(datetime.now())
            lesson_response = requests.patch("%s/%s" % (SERVICES_URI['lessons'], flask.request.form['lesson_id']),
                                             json={'answers': answers})
            if lesson_response.status_code == 200:
                return flask.redirect("/lessons/%s" % number)

            return flask.render_template('error.html', reason=lesson_response.json()), 500

        elif 'mark_answer' in flask.request.form:
            lesson_response = requests.get("%s/%s" % (SERVICES_URI['lessons'], flask.request.form['lesson_id']))
            answers = lesson_response.json()['answers']
            student_id = int(flask.request.form['student_id'])
            student_answers_indexes = [ind for ind, ans in enumerate(answers)
                                       if ans['student_id'] == student_id]
            assert len(student_answers_indexes) == 1
            answer = answers[student_answers_indexes[0]]
            answer['mark'] = flask.request.form['mark']
            answer['last_updated_at'] = render_datetime(datetime.now())
            lesson_response = requests.patch("%s/%s" % (SERVICES_URI['lessons'], flask.request.form['lesson_id']),
                                             json={'answers': answers})
            if lesson_response.status_code == 200:
                return flask.redirect("/lessons/%s" % number)

            return flask.render_template('error.html', reason=lesson_response.json()), 500

    except requests.exceptions.RequestException:
        return flask.render_template('error.html', reason='Сервис заданий недоступен'), 503

    return flask.render_template('error.html', reason='Внутренняя ошибка. Что-то пошло не так.'), 500


def get_tutors():
    tutors_response = requests.get(SERVICES_URI['profiles'], params={
        'q': simplejson.dumps({
            'filters': [
                {'name': 'role', 'op': '==', 'val': 'tutor'},
            ],
        }),
    })
    assert tutors_response.status_code == 200
    tutors = tutors_response.json()

    return tutors['objects']

if __name__ == '__main__':
    app.run(port=PORT)

