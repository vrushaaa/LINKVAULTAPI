from flask import Blueprint, request, jsonify, url_for, redirect
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from urllib.parse import urljoin
#import re
import pytz
from datetime import datetime

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

# display all bookmarks
@bp.route('/bookmarks', methods=['GET'])
def list_bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    tag = request.args.get('tag')
    keyword = request.args.get('q')
    archived = request.args.get('archived', type=lambda x: x.lower() == 'true')

    query = Bookmark.query

    if tag:
        query = query.join(Bookmark.tags).filter(Tag.name == tag.lower())
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Bookmark.url.ilike(pattern),
                Bookmark.title.ilike(pattern),
                Bookmark.notes.ilike(pattern)
            )
        )
    if archived is not None:
        query = query.filter(Bookmark.archived == archived)

    pagination = query.order_by(Bookmark.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    base_url = url_for('bookmarks_api.list_bookmarks', _external=True)
    def abs_url(page_num):
        return f"{base_url.split('?')[0]}?page={page_num}&per_page={per_page}" + \
               (f"&tag={tag}" if tag else "") + \
               (f"&q={keyword}" if keyword else "") + \
               (f"&archived={archived}" if archived is not None else "")

    results = []
    for b in pagination.items:
        created_ist = b.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))
        results.append({
            'id': b.id,
            'url': b.url,
            'short_url': b.short_url,
            'full_short_url': url_for('short.redirect_short', short_code=b.short_url, _external=True),
            'title': b.title,
            'notes': b.notes,
            'archived': b.archived,
            'created_at': created_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
            'tags': [t.name for t in b.tags]
        })

    return jsonify({
        'bookmarks': results,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'next_url': abs_url(page + 1) if pagination.has_next else None,
            'prev_url': abs_url(page - 1) if pagination.has_prev else None
        }
    }),200

# display bookmark by id


# update bookmark


# delete Bookmark using id


# toggle archive status


# # url-shortner
@short_bp.route('/<short_code>')
def redirect_short(short_code):
    bookmark = Bookmark.query.filter_by(short_url=short_code).first_or_404()
    bookmark.updated_at = db.func.now()
    db.session.commit()
    return redirect(bookmark.url)