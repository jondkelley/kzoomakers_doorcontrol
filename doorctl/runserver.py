# Filename    : runserver.py
# Author      : Jon Kelley <jon.kelley@kzoomakers.org>
# Description : Kzoomakers Door Controller

from flask import Blueprint, Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, json, make_response, send_file
from doorctl.blueprints.doorctl import doorctl
import base64
import os
from datetime import datetime
import time
from dateutil import tz

os.environ['TZ'] = os.environ.get('TIMEZONE')
time.tzset()


app = Flask(__name__)#,  template_folder='templates')

# Define a custom Jinja2 filter for strftime
def format_datetime(value, format='%B %d'):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime(format)

# Add the custom filter to the Jinja2 environment
app.jinja_env.filters['strftime'] = format_datetime

print('startup')
app.secret_key = os.getenv(
    "SECRET_KEY", "kalamazoo03h0f03h0f3h03hf830dboqboqow2")

ENV_REST_ENDPOINT = os.environ.get('REST_ENDPOINT', 'http://127.0.0.1:8080')
app.config['REST_ENDPOINT'] = f"{ENV_REST_ENDPOINT}/uhppote"
app.config['ENABLE_PROXY_DETECTION'] = os.environ.get('ENABLE_PROXY_DETECTION', False)
app.config['ENABLE_PROXIED_SECURIY_KEY'] = os.environ.get('ENABLE_PROXIED_SECURIY_KEY', False)


app.register_blueprint(doorctl)

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return render_template('500.html'), 500


def main():
    app.run(host='0.0.0.0', debug=True, port=5001, threaded=True)


if __name__ == '__main__':
    main()
