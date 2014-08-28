# -*- coding: utf-8 -*-

from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash

from om_panel.sessions import sessions

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    # DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='admin'
))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/')
def index():
    if not hasattr(g, 'user'):
        g.user = None

    if not g.user:
        return redirect(url_for('login'))

sessions(app)