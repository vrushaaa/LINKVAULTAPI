import os
import tempfile
from flask import Blueprint, current_app, render_template, request, jsonify, url_for, redirect
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from app.models.user import User 
from urllib.parse import urljoin
import pytz
from datetime import datetime

# parameter checking for all routes

#bluprints
bp = Blueprint('bookmarks_api', __name__)
short_bp = Blueprint('short', __name__)

# title extraction
def extract_title(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.title.string.strip() if soup.title else None
    except:
        return None

# home page route
@short_bp.route('/')
def home():
    return render_template('welcome.html'), 200

#bookmark creation route
@bp.route('/bookmarks', methods=['POST'])
def create_bookmark():
    data = request.get_json() or {}
    url = data.get('url')
    title = data.get('title')
    notes = data.get('notes')
    tags = data.get('tags', [])
    archived = data.get('archived', False)
    user_id = data.get('user_id') 

    if not url:
        return jsonify({'error': 'URL is required'}), 400
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    norm_url = normalize_url(url)
    url_hash = generate_url_hash(norm_url)

    existing = Bookmark.query.filter_by(hash_url=url_hash).first()
    if existing:
        short_url = url_for('short.redirect_short', short_code=existing.short_url, _external=True)
        return jsonify({
            'message': 'URL already exists',
            'bookmark': {
                'id': existing.id,
                'url': existing.url,
                'short_url': existing.short_url,
                'full_short_url': short_url,
                'user_id': existing.user_id
            }
        }), 409

    bookmark = Bookmark(
        url=norm_url,
        notes=notes,
        archived=archived,
        user_id=user_id  
    )
    bookmark.set_hash()
    bookmark.set_short_url()

    if not title:
        title = extract_title(norm_url)
    bookmark.title = title

    for tag_name in tags:
        tag_name = tag_name.strip().lower()
        if tag_name:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            bookmark.tags.append(tag)

    db.session.add(bookmark)
    db.session.commit()

    short_url = url_for('short.redirect_short', short_code=bookmark.short_url, _external=True)
    ist_time = bookmark.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))

    return jsonify({
        'message': 'Bookmark created',
        'bookmark': bookmark.to_dict() 
    }), 201

#display bookmark by id if exists
@bp.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({'error': 'Bookmark not found'}), 404

    return jsonify(bookmark.to_dict()), 200

# update bookmark
@bp.route('/bookmarks/<int:bookmark_id>', methods=['PUT'])
def update_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    data = request.get_json() or {}

    if 'title' in data:
        bookmark.title = data['title']
    if 'notes' in data:
        bookmark.notes = data['notes']
    if 'archived' in data:
        bookmark.archived = data['archived']
    if 'user_id' in data:
        new_user = User.query.get(data['user_id'])
        if not new_user:
            return jsonify({'error': 'User not found'}), 404
        bookmark.user_id = new_user.id

    if 'tags' in data:
        bookmark.tags = []
        for tag_name in data['tags']:
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                bookmark.tags.append(tag)

    db.session.commit()

    return jsonify({
        'message': 'Bookmark updated',
        'bookmark': bookmark.to_dict()
    }), 200

# delete Bookmark using id
@bp.route('/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    db.session.delete(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmark deleted'}), 200

# toggle archive status
@bp.route('/bookmarks/<int:bookmark_id>/archive', methods=['PATCH'])
def toggle_archive(bookmark_id):
    bookmark = Bookmark.query.get_or_404(bookmark_id)
    bookmark.archived = not bookmark.archived
    db.session.commit()

    return jsonify({
        'message': 'Archive status toggled',
        'bookmark': bookmark.to_dict()
    }), 200

#  url-shortner
@short_bp.route('/<short_code>')
def redirect_short(short_code):
    bookmark = Bookmark.query.filter_by(short_url=short_code).first_or_404()
    bookmark.updated_at = db.func.now()
    db.session.commit()
    return redirect(bookmark.url)


# export bookmarks as HTML
@bp.route('/export', methods=['GET'])
def export_bookmarks():
    user_id = request.args.get('user_id')
    query = Bookmark.query
    if user_id:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        query = query.filter_by(user_id=user_id)
    else:
        query = query.all()

    bookmarks = query.all()
    if not bookmarks:
        return jsonify({'error': 'No bookmarks to export'}), 404

    ist = pytz.timezone('Asia/Kolkata')

    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as tmpfile:
        tmpfile.write('<!DOCTYPE NETSCAPE-Bookmark-file-1>\n')
        tmpfile.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
        tmpfile.write('<TITLE>LinkVault Bookmarks</TITLE>\n')
        tmpfile.write('<H1>LinkVault Bookmarks</H1>\n')
        tmpfile.write('<DL><p>\n')

        for b in bookmarks:
            created_ist = b.created_at.replace(tzinfo=pytz.UTC).astimezone(ist)
            add_date = int(created_ist.timestamp())
            title = (b.title or b.url).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            tmpfile.write(f'    <DT><A HREF="{b.url}" ADD_DATE="{add_date}">{title}</A>\n')
            if b.notes:
                notes = b.notes.replace('&', '&amp;').replace('<', '&lt;')
                tmpfile.write(f'    <DD>{notes}\n')

        tmpfile.write('</DL><p>\n')

    return_data = None
    with open(tmpfile.name, 'rb') as f:
        return_data = f.read()
    os.unlink(tmpfile.name)

    response = current_app.response_class(
        response=return_data,
        status=200,
        mimetype='text/html'
    )
    filename = f'linkvault_bookmarks_user{user_id}.html' if user_id else 'linkvault_bookmarks.html'
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response

# list all tags
@bp.route('/tags', methods=['GET'])
def list_tags():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1: page = 1
    if per_page < 1: per_page = 20
    if per_page > 100: per_page = 100

    pagination = Tag.query.order_by(Tag.name).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'tags': [tag.name for tag in pagination.items],
        'pagination': {
            'page': page,
            'pages': pagination.pages,
            'per_page': per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_url': url_for('bookmarks_api.list_tags', page=page+1, per_page=per_page, _external=True) if pagination.has_next else None,
            'prev_url': url_for('bookmarks_api.list_tags', page=page-1, per_page=per_page, _external=True) if pagination.has_prev else None,
        }
    }), 200

# filtering by tag if else logic to be applied
# updated filter by id route
@bp.route('/bookmarks', methods=['GET'])
def list_bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    tag = request.args.get('tag')
    q = request.args.get('q')
    archived_param = request.args.get('archived')
    user_id = request.args.get('user_id', type=int)

    allowed_params = {'page', 'per_page', 'tag', 'q', 'archived', 'user_id'}
    invalid_params = set(request.args.keys()) - allowed_params
    if invalid_params:
        return jsonify({
            'error': 'Invalid query parameter(s)',
            'invalid': list(invalid_params),
            'allowed': list(allowed_params)
        }), 400

    query = Bookmark.query

    if user_id:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        query = query.filter_by(user_id=user_id)

    if archived_param is not None:
        archived = archived_param.lower() == 'true'
        query = query.filter_by(archived=archived)

    if tag:
        tags_list = [t.strip() for t in tag.split(",") if t.strip()]
        for t in tags_list:
            query = query.filter(Bookmark.tags.any(Tag.name == t))

    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Bookmark.title.ilike(search),
                Bookmark.url.ilike(search)
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'bookmarks': [b.to_dict() for b in pagination.items],
        'pagination': {
            'page': page,
            'pages': pagination.pages,
            'per_page': per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_url': url_for('bookmarks_api.list_bookmarks', page=page+1, per_page=per_page, _external=True) if pagination.has_next else None,
            'prev_url': url_for('bookmarks_api.list_bookmarks', page=page-1, per_page=per_page, _external=True) if pagination.has_prev else None,
        }
    }), 200

# error handling for bp
@bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad Request', 'message': str(error.description)}), 400

@bp.errorhandler(ValueError)
def validation_error(error):
    return jsonify({'error': 'Validation Error', 'message': str(error)}), 400

@bp.errorhandler(db.exc.IntegrityError)
def integrity_error(error):
    db.session.rollback()
    return jsonify({'error': 'Database Error', 'message': 'Data integrity violation'}), 400