#!/usr/bin/env python3
"""
Flask сервер для локальной разработки и управления галереей
"""
from flask import Flask, send_from_directory, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import io
import os
import json
import subprocess
from functools import wraps

from update_gallery_assets import update_gallery, DEFAULT_OUTPUT_DIR, DEFAULT_SIZES

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = 'w'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in (ALLOWED_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS)

def is_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def load_gallery():
    try:
        with open('gallery.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_gallery(gallery):
    with open('gallery.json', 'w', encoding='utf-8') as f:
        json.dump(gallery, f, ensure_ascii=False, indent=2)


def sync_gallery_assets():
    try:
        update_gallery('gallery.json', DEFAULT_SIZES, DEFAULT_OUTPUT_DIR)
    except Exception as e:
        print(f"Failed to update gallery assets: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    # Простая проверка пароля (в продакшене используйте хеширование)
    if password == 'admin':  # Измените пароль!
        session['logged_in'] = True
        return redirect(url_for('admin'))
    return redirect('/admin?error=1')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/admin')

@login_required
@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('file')
    captions = request.form.getlist('caption')
    if not files:
        return jsonify({'error': 'No file'}), 400
    gallery = load_gallery()
    responses = []
    for idx, file in enumerate(files):
        if file and allowed_file(file.filename):
            try:
                if is_video_file(file.filename):
                    # Для видео файлов сохраняем как есть, без конвертации
                    base = secure_filename(file.filename.rsplit('.', 1)[0])
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{base}.{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    caption = captions[idx] if idx < len(captions) else ''
                    gallery.append({'src': f'w/{filename}', 'caption': caption, 'type': 'video'})
                    responses.append({'file': filename, 'success': True})
                else:
                    # Для изображений конвертируем в WebP
                    img = Image.open(file.stream)
                    webp_io = io.BytesIO()
                    if getattr(img, "is_animated", False):
                        img.save(webp_io, format='WEBP', save_all=True)
                    else:
                        img.save(webp_io, format='WEBP')
                    webp_io.seek(0)
                    base = secure_filename(file.filename.rsplit('.', 1)[0])
                    filename = f"{base}.webp"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    with open(filepath, 'wb') as f_out:
                        f_out.write(webp_io.read())
                    caption = captions[idx] if idx < len(captions) else ''
                    gallery.append({'src': f'w/{filename}', 'caption': caption})
                    responses.append({'file': filename, 'success': True})
            except Exception as e:
                responses.append({'file': file.filename, 'success': False, 'error': str(e)})
        else:
            responses.append({'file': file.filename, 'success': False, 'error': 'Invalid file'})
    save_gallery(gallery)
    sync_gallery_assets()
    return jsonify({'results': responses})

@login_required
@app.route('/gallery-list', methods=['GET'])
def gallery_list():
    return jsonify({'gallery': load_gallery()})

@login_required
@app.route('/delete-item', methods=['POST'])
def delete_item():
    data = request.json
    src = data.get('src')
    if not src:
        return jsonify({'error': 'No src provided'}), 400
    gallery = load_gallery()
    gallery = [item for item in gallery if item.get('src') != src]
    save_gallery(gallery)
    sync_gallery_assets()
    return jsonify({'success': True})

@login_required
@app.route('/update-caption', methods=['POST'])
def update_caption():
    data = request.json
    src = data.get('src')
    caption = data.get('caption', '')
    if not src:
        return jsonify({'error': 'No src provided'}), 400
    gallery = load_gallery()
    for item in gallery:
        if item.get('src') == src:
            item['caption'] = caption
            break
    save_gallery(gallery)
    return jsonify({'success': True})

@login_required
@app.route('/reorder-gallery', methods=['POST'])
def reorder_gallery():
    data = request.json
    order = data.get('order', [])
    if not order:
        return jsonify({'error': 'No order provided'}), 400
    gallery = load_gallery()
    # Создаем словарь для быстрого поиска
    gallery_dict = {item['src']: item for item in gallery}
    # Переупорядочиваем согласно order
    reordered = [gallery_dict[src] for src in order if src in gallery_dict]
    # Добавляем элементы, которых нет в order (на случай, если что-то пропущено)
    existing_srcs = set(order)
    for item in gallery:
        if item['src'] not in existing_srcs:
            reordered.append(item)
    save_gallery(reordered)
    return jsonify({'success': True})

@login_required
@app.route('/shuffle-gallery', methods=['POST'])
def shuffle_gallery():
    import random
    gallery = load_gallery()
    random.shuffle(gallery)
    save_gallery(gallery)
    return jsonify({'success': True})

@login_required
@app.route('/generate-static', methods=['POST'])
def generate_static():
    try:
        result = subprocess.run(['python3', 'generate_static.py'], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        if result.returncode == 0:
            return jsonify({'success': True, 'message': result.stdout.strip()})
        else:
            return jsonify({'success': False, 'error': result.stderr.strip() or 'Ошибка генерации'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/gallery.json')
def gallery_json():
    return send_from_directory('.', 'gallery.json')

@app.route('/<path:filename>')
def serve_static(filename):
    # Исключаем файлы, которые обрабатываются другими маршрутами
    if filename in ['index.html', 'admin.html']:
        return send_from_directory('.', filename)
    # Разрешаем доступ только к статическим файлам
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.pdf', '.ttf', '.mp4', '.webm', '.json', '.xml', '.css', '.js'}
    if any(filename.lower().endswith(ext) for ext in allowed_extensions):
        return send_from_directory('.', filename)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)

