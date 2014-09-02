# -*- coding: utf-8 -*-

import json
import redis
import os

from flask import Flask, Blueprint, request, session, url_for, redirect, \
     render_template, abort, g, flash

import chartkick

app = Flask(__name__)
app.config.update(dict(
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='admin'
))
redis = redis.StrictRedis(host='localhost', port='6379', db=0)

# Charts

ck = Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")


# Config

BASE_CONFIG = {'hosts': {}}


def write_config(path, config=BASE_CONFIG):
    with open(path, 'w') as f: json.dump(config, f)
    return config

def load_config(path, refresh_redis=True):
    config = json.load(open(path)) if os.path.exists(path) else write_config(path)
    for name, host_config in config.get('hosts', {}).iteritems():
        host = Host.from_config(name, host_config)
        if refresh_redis:
            host.save() # FIXME this could have side effects..
    return config

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


def clean_timeseries_array(ar):
    a, b = ar[1:-1].split(',')
    return [int(a), float(b)]


class Host(object):

    def __init__(self, name, host):
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
        self._update_ext_config()

    def disks_usage(self):
        disks = {}
        disks_for_host = redis.keys('%s:disk_usage:*' % self.host)
        for disk in disks_for_host:
            disk_name = disk.split(':')[-2]
            usage = map(clean_timeseries_array, redis.lrange(disk, -200, -1))
            disks[disk_name] = usage
        return disks

    @property
    def memory_usage(self):
        base_key = '%s:memory_usage:system:' % self.host
        free = redis.lrange(base_key + 'free', -200, -1)
        used = redis.lrange(base_key + 'free', -200, -1)
        usage = redis.lrange(base_key + 'usage', -200, -1)
        return map(clean_timeseries_array, usage)

    @staticmethod
    def destroy(host_id):
        with redis.pipeline() as pipeline:
            name = 'host:' + host_id
            pipeline.delete(name)
            pipeline.srem('hosts', host_id)
            pipeline.execute()

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

    @staticmethod
    def from_config(name, config):
        # TODO ssh
        return Host(name, config['host'])

    def _update_ext_config(self):
        with app.app_context():
            if not hasattr(app, 'config_file'): return
            config = load_config(app.config_file, refresh_redis=False)

            if self.name not in config['hosts']:
                config['hosts'][self.name] = {'host': self.host}

            write_config(app.config_file, config)


def hosts(app):
    @app.route('/hosts/new', methods=['GET', 'POST'])
    def host_new():
        host = {}
        error = None

        if request.method == 'POST':
            try:
                host['name'], host['host'] = request.form['name'], request.form['host']
                assert host['name'] not in Host.all(), 'Name already in use'
                host_object = Host(**host)
                host_object.save()
                return redirect(url_for('host', host_id=host_object.name))
            except Exception as e:
                print e
                import traceback
                traceback.print_exc()
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

