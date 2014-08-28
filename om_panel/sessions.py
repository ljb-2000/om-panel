# -*- coding: utf-8 -*-

from flask import request, session, url_for, redirect, \
     render_template, g, flash

def sessions(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if not hasattr(g, 'user'): g.user = None

        """Logs the user in."""
        if g.user:
            return redirect(url_for('home'))
        error = None
        if request.method == 'POST':
            if request.form['username'] == app.config['USERNAME'] and request.form['password'] == app.config['PASSWORD']:
                flash('You were logged in')
                session['user_id'] = 1
                g.user = 1
                return redirect(url_for('home'))
            else:
                error = 'Wrong credentials'
        return render_template('login.html', error=error)
