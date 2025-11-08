import os
import tempfile
from flask import Blueprint, current_app, render_template, request, jsonify, url_for, redirect
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from urllib.parse import urljoin
#import re
import pytz
from datetime import datetime

# parameter checking for all routes

#blueprints
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
        return render_template('welcome.html'),200
    
#bookmark creation route
@bp.route('/bookmarks', methods=['POST'])
def create_bookmark():
    data = request.get_json() or {}
    url = data.get('url')
    title = data.get('title')
    notes = data.get('notes')
    tags = data.get('tags', [])
    archived = data.get('archived', False)

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    norm_url = normalize_url(url)
    url_hash = generate_url_hash(url)

    existing = Bookmark.query.filter_by(hash_url=url_hash).first()
    if existing:
        short_url = url_for('short.redirect_short', short_code=existing.short_url, _external=True)
        return jsonify({
            'message': 'URL already exists',
            'bookmark': {
                'id': existing.id,
                'url': existing.url,
                'short_url': existing.short_url,
                'full_short_url': short_url
            }
        }), 409

    bookmark = Bookmark(url=norm_url, notes=notes, archived=archived)
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
        'bookmark': {
            'id': bookmark.id,
            'url': bookmark.url,
            'short_url': bookmark.short_url,
            'full_short_url': short_url,
            'title': bookmark.title,
            'created_at': ist_time.strftime('%Y-%m-%d %H:%M:%S IST'),
            'tags': [t.name for t in bookmark.tags]
        }
    }), 201


#display bookmark by id if exists
@bp.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)

    if not bookmark:
        return jsonify({'error': 'Bookmark not found'}), 404

    created_ist = bookmark.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))

    return jsonify({
        'id': bookmark.id,
        'url': bookmark.url,
        'short_url': bookmark.short_url,
        'full_short_url': url_for('short.redirect_short', short_code=bookmark.short_url, _external=True),
        'title': bookmark.title,
        'notes': bookmark.notes,
        'archived': bookmark.archived,
        'created_at': created_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
        'tags': [t.name for t in bookmark.tags]
    }), 200


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
        'bookmark': {
            'id': bookmark.id,
            'url': bookmark.url,
            'short_url': bookmark.short_url,
            'full_short_url': url_for('short.redirect_short', short_code=bookmark.short_url, _external=True),
            'title': bookmark.title,
            'notes': bookmark.notes,
            'archived': bookmark.archived,
            'tags': [t.name for t in bookmark.tags]
        }
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
        'bookmark': {
            'id': bookmark.id,
            'url': bookmark.url,
            'short_url': bookmark.short_url,
            'full_short_url': url_for('short.redirect_short', short_code=bookmark.short_url, _external=True),
            'archived': bookmark.archived
        }
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
    bookmarks = Bookmark.query.all()
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

            title = (b.title or b.url)
            title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

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
    response.headers.set('Content-Disposition', 'attachment', filename='linkvault_bookmarks.html')
    return response

# filtering by tag if else logic to be applied
# updated filter by id route
@bp.route('/bookmarks/', methods=['GET'])
def list_bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    tag = request.args.get('tag')
    q = request.args.get('q')
    archived_param = request.args.get('archived')
    bookmark_id = request.args.get('id', type=int)

    # validate allowed query parameters
    allowed_params = {'page', 'per_page', 'tag', 'q', 'archived', 'id'}
    invalid_params = set(request.args.keys()) - allowed_params
    if invalid_params:
        return jsonify({
            'error': 'Invalid query parameter(s)',
            'invalid': list(invalid_params),
            'allowed': list(allowed_params),
            'correct_url_example': url_for('bookmarks_api.list_bookmarks', _external=True)
        }), 400

    query = Bookmark.query

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

    # if bookmark_id:
    #     query = query.filter(Bookmark.id == bookmark_id)

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
    })

#error handling for bp
@bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request data'
    }), 400

# @bp.errorhandler(404)
# def not_found(error):
#     return jsonify({
#         'error': 'Not Found',
#         'message': 'The requested resource does not exist'
#     }), 404

# @bp.errorhandler(405)
# def method_not_allowed(error):
#     return jsonify({
#         'error': 'Method Not Allowed',
#         'message': 'HTTP method not supported for this endpoint'
#     }), 405

# @bp.errorhandler(500)
# def internal_error(error):
#     db.session.rollback()
#     return jsonify({
#         'error': 'Internal Server Error',
#         'message': 'An unexpected error occurred'
#     }), 500

@bp.errorhandler(ValueError)
def validation_error(error):
    return jsonify({
        'error': 'Validation Error',
        'message': str(error)
    }), 400

@bp.errorhandler(db.exc.IntegrityError)
def integrity_error(error):
    db.session.rollback()
    return jsonify({
        'error': 'Database Error',
        'message': 'Data integrity violation (e.g. duplicate entry)'
    }), 400

# @bp.errorhandler(Exception)
# def unhandled_exception(error):
#     db.session.rollback()
#     current_app.logger.error(f'Unhandled Exception: {error}', exc_info=True)
#     return jsonify({
#         'error': 'Server Error',
#         'message': 'Something went wrong. Please try again later.'
#     }), 500   

#erroe handling for short_bp 
# @short_bp.errorhandler(404)
# def short_not_found(error):
#     # If someone visits /invalidcode
#     return jsonify({
#         'error': 'Not Found',
#         'message': 'Short URL does not exist'
#     }), 404

# @short_bp.errorhandler(Exception)
# def short_unhandled(error):
#     db.session.rollback()
#     current_app.logger.error(f'Short URL Error: {error}', exc_info=True)
#     return jsonify({
#         'error': 'Server Error',
#         'message': 'Failed to redirect. Please try again later.'
#     }), 500