# -*- coding: utf-8 -*-

import json
import redis

from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash


app = Flask(__name__)
app.config.update(dict(
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='admin'
))

redis = redis.StrictRedis(host='localhost', port='6379', db=0)


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('hosts'))
    else:
        return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(e=None):
    return render_template('errors/404.html'), 404


def sessions(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if session.get('logged_in'):
            return redirect(url_for('hosts'))
        if request.method == 'POST':
            if request.form['username'] == app.config['USERNAME'] \
                and request.form['password'] == app.config['PASSWORD']:
                flash('You were logged in')
                session['logged_in'] = True
                return redirect(url_for('hosts'))
            else:
                error = 'wrong credentials'
        return render_template('login.html', error=error)

    @app.route('/logout')
    def logout():
        session['logged_in'] = False
        return redirect(url_for('login'))


class Host(object):

    def __init__(self, name, host, ssh='{}'):
        assert len(name) > 0, 'Name must not be blank'
        assert len(host) > 0, 'Host must not be blank'
        self.name = name
        self.host = host

    def save(self):
        with redis.pipeline() as pipeline:
            pipeline.hmset('host:' + self.name, {
                'host': self.host,
            })
            pipeline.sadd('hosts', self.name)
            pipeline.execute()

    @staticmethod
    def destroy(host_id):
        with redis.pipeline() as pipeline:
            name = 'host:' + host_id
            pipeline.delete(name)
            pipeline.srem('hosts', host_id)
            print pipeline.execute()

    @staticmethod
    def find(host_id):
        name = 'host:' + host_id
        host = redis.hgetall(name)
        if not host: return
        host.update(name=host_id)
        return Host(**host)

    @staticmethod
    def all():
        return redis.smembers('hosts')


def hosts(app):
    @app.route('/hosts/new', methods=['GET', 'POST'])
    def host_new():
        host = {}
        error = None

        if request.method == 'POST':
            try:
                host['name'], host['host'] = request.form['name'], request.form['host']
                host_object = Host(**host)
                host_object.save()
                return redirect(url_for('host', host_id=host_object.name))
            except Exception as e:
                error = e

        return render_template('hosts/new.html', host=host, error=error)

    @app.route('/hosts')
    def hosts():
        return render_template('hosts/list.html', hosts=Host.all())

    @app.route('/hosts/<host_id>')
    def host(host_id):
        host = Host.find(host_id)
        return render_template('hosts/host.html', host=host) if host else not_found()

    @app.route('/hosts/<host_id>/destroy')
    def destroy_host(host_id):
        if host_id in Host.all():
            Host.destroy(host_id)
            return redirect(url_for('hosts'))
        return not_found()


for subapp in [sessions, hosts]:
    subapp(app)

