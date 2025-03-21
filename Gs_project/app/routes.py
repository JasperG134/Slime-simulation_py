import os
import uuid
from flask import render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from app import app
from app.auth import authenticate, login_required, logout
from app.generator import generate_family_report, generate_family_tree_data

# Configuratie voor bestandsuploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')

        if authenticate(password):
            next_page = request.args.get('next')
            flash('U bent succesvol ingelogd!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Ongeldig wachtwoord. Probeer het opnieuw.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout_route():
    logout()
    flash('U bent uitgelogd.', 'info')
    return redirect(url_for('home'))


@app.route('/generate', methods=['POST'])
@login_required
def generate_report():
    data = {
        'onderzoeksvraag': request.form.get('onderzoeksvraag', ''),
        'deelvragen': request.form.get('deelvragen', ''),
        'interviews': request.form.get('interviews', ''),
        'bronnen': request.form.get('bronnen', ''),
        'documenten': request.form.get('documenten', ''),
        'notities': request.form.get('notities', '')
    }

    # Afbeelding uploads verwerken
    uploaded_images = []
    if 'images' in request.files:
        images = request.files.getlist('images')
        for image in images:
            if image and image.filename and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(file_path)
                uploaded_images.append(file_path)

    # There is no money on this account, only used for the free model. so no use in stealing it ;).
    # also this key will be removed from my account after 21/03/2025 european notation.
    api_key = "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"

    # Verslag genereren
    report_text, doc_file = generate_family_report(data, uploaded_images, api_key)

    # Familierelatie data voor de stamboom genereren
    family_tree_data = generate_family_tree_data(data)

    # Bewaar de resultaten in de sessie
    session['report_text'] = report_text
    session['doc_file'] = doc_file
    session['family_tree_data'] = family_tree_data

    return redirect(url_for('show_results'))


@app.route('/results')
@login_required
def show_results():
    report_text = session.get('report_text')
    doc_file = session.get('doc_file')
    family_tree_data = session.get('family_tree_data')

    if not report_text:
        flash('Geen verslag gevonden. Genereer eerst een verslag.', 'warning')
        return redirect(url_for('index'))

    return render_template(
        'success.html',
        report_text=report_text,
        doc_file=doc_file,
        family_tree_data=family_tree_data
    )


@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], path=filename)


@app.route('/family-tree-data')
@login_required
def get_family_tree_data():
    data = session.get('family_tree_data')
    return jsonify(data)


@app.route('/dashboard')
@login_required
def index():
    return render_template('index.html')