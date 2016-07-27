from flask import Flask, current_app, request
from flask.ext.mandrill import Mandrill

import senseapi
import random
import string
import json

app = Flask(__name__)
app.config.from_pyfile('config.py')

mandrill = Mandrill(app)


@app.route("/register", methods=['POST'])
def create_user():
    data = request.get_json()
    email = str(data['email'])

    if data is None:
        raise

    api = senseapi.SenseAPI()

    current_app.logger.debug("login as manager")
    api.Login(current_app.config['MANAGER_USER'], senseapi.MD5Hash(current_app.config['MANAGER_PASSWORD']))

    if not api.getResponseStatus() == 200:
        current_app.logger.error("Error login as manager")
        raise

    pwd = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    user = {"user": {"username": email, "email": email, "password": senseapi.MD5Hash(pwd)}}

    current_app.logger.debug("creating user {} with pwd {}".format(email, pwd))
    api.CreateUser(user)
    if not api.getResponseStatus() == 201:
        current_app.logger.error("Error creating user")
        raise

    user['user'].update(json.loads(api.getResponse())['user'])

    try:
        current_app.logger.debug("adding user to domain")
        param = api.DomainAddUserPost_Parameters()
        param['users'][0]['id'] = user['user']['id']
        if not api.DomainAddUserPost(param, current_app.config['DOMAIN_ID']):
            current_app.logger.error("Error adding user to domain")
            raise

        mandrill.send_email(
            template_name=current_app.config['TEMPLATE_NAME'],
            from_email=current_app.config['SENDER_EMAIL'],
            from_name=current_app.config['SENDER_NAME'],
            global_merge_vars=[{'content': email, 'name': 'USERNAME'},
                               {'content': pwd, 'name': 'PASSWORD'}],
            to=[{'email': email, 'type': 'to'}],
        )

    except:
        current_app.logger.info("Deleting user")
        api.Login(email, senseapi.MD5Hash(pwd))
        api.UsersDelete(user["user"]["id"])

    return "OK", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
