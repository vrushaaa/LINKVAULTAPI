import os
import tempfile
from flask import Blueprint, current_app, render_template, request, jsonify, url_for, redirect, Response
from flask_login import login_required
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from app.models.user import User
from app.models.user_bookmark import UserBookmark
from app.models.tag_user_bookmark import tag_user_bookmarks
from urllib.parse import urljoin
import pytz
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# blueprints
bp = Blueprint('bookmarks_api', __name__, url_prefix='/api')
short_bp = Blueprint('short', __name__, url_prefix='/') 

# home page
@short_bp.route('/')
def home():
    return render_template('landing.html'), 200

# short url redirect
@short_bp.route('/<short_code>')
def redirect_short(short_code):   
    bookmark = Bookmark.query.filter_by(short_url=short_code).first_or_404()
    bookmark.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(bookmark.url)

# title extraction using web scrapping
def extract_title(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else None
    except Exception:
        return None

@bp.route('/', methods=['GET'])
def dashboard():
    return render_template('landing.html'), 200

#bookmark creation route
@bp.route('/bookmarks', methods=['POST'])
@login_required
def create_bookmark():
    data = request.get_json()
    url = data.get('url')
    user_id = data.get('user_id')
    notes = data.get('notes', '')
    tags = data.get('tags', [])
    archived = data.get('archived', False)
    title = data.get('title')

    if not url or not user_id:
        return jsonify({'error': 'url and user_id required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    norm_url = normalize_url(url)
    url_hash = generate_url_hash(norm_url)
    existing = Bookmark.query.filter_by(hash_url=url_hash).first()

    if existing:
        stmt = db.select(UserBookmark).where(
            UserBookmark.c.user_id == user_id,
            UserBookmark.c.bookmark_id == existing.id
        )
        if db.session.execute(stmt).scalar():
            return jsonify({'error': 'You already saved this link'}), 409
        bookmark = existing
    else:
        bookmark = Bookmark(url=norm_url)
        bookmark.set_hash()
        bookmark.set_short_url()
        db.session.add(bookmark)
        db.session.flush()

        if not title:
            title = extract_title(norm_url) or "Untitled Link"

    # Create or update UserBookmark
    ub = UserBookmark.query.filter_by(user_id=user_id, bookmark_id=bookmark.id).first()
    if not ub:
        ub = UserBookmark(
            user_id=user_id,
            bookmark_id=bookmark.id,
            title=title,
            notes=notes,
            archived=archived
        )
        db.session.add(ub)
    else:
        ub.title = title
        ub.notes = notes
        ub.archived = archived

    # Handle tags via tag_user_bookmarks (count auto-updated by event)
    if tags:
        db.session.execute(
            tag_user_bookmarks.delete().where(
                tag_user_bookmarks.c.bookmark_id == bookmark.id,
                tag_user_bookmarks.c.user_id == user_id
            )
        )
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                db.session.execute(
                    tag_user_bookmarks.insert().values(
                        tag_id=tag.id,
                        user_id=user_id,
                        bookmark_id=bookmark.id
                        # ← NO bookmark_count=1
                    )
                )

    db.session.commit()

    return jsonify({
        'message': 'Bookmark saved successfully',
        'bookmark': bookmark.to_dict(user_id=user_id)
    }), 201

# get single bookmark
@bp.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
@login_required
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({'error': 'Bookmark not found'}), 404
    user_id = request.args.get('user_id', type=int)
    return jsonify(bookmark.to_dict(user_id=user_id)), 200

# update bookmark
@bp.route('/bookmarks/<int:bookmark_id>', methods=['PUT'])
def update_bookmark(bookmark_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    ub = UserBookmark.query.filter_by(user_id=user_id, bookmark_id=bookmark_id).first()
    if not ub:
        return jsonify({'error': 'Access denied or not found'}), 404

    bookmark = Bookmark.query.get(bookmark_id)
    updated = False

    if 'title' in data:
        ub.title = data['title']
        updated = True

    if 'notes' in data:
        ub.notes = data['notes']
        updated = True

    if 'archived' in data:
        ub.archived = data['archived']
        updated = True

    if 'tags' in data:
        db.session.execute(
            tag_user_bookmarks.delete().where(
                tag_user_bookmarks.c.bookmark_id == bookmark_id,
                tag_user_bookmarks.c.user_id == user_id
            )
        )
        for tag_name in data.get('tags', []):
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                db.session.execute(
                    tag_user_bookmarks.insert().values(
                        tag_id=tag.id,
                        user_id=user_id,
                        bookmark_id=bookmark_id
                    )
                )
        updated = True

    if updated:
        ub.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({
        'message': 'Updated',
        'bookmark': bookmark.to_dict(user_id=user_id)
    }), 200

# archive toggle
@bp.route('/bookmarks/<int:bookmark_id>/archive', methods=['PATCH'])
@login_required
def toggle_archive(bookmark_id):
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    ub = UserBookmark.query.filter_by(user_id=user_id, bookmark_id=bookmark_id).first()
    if not ub:
        return jsonify({'error': 'Not found or access denied'}), 404

    ub.archived = not ub.archived
    ub.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Archive toggled',
        'archived': ub.archived
    }), 200

# delete bookmark
@bp.route('/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def delete_bookmark(bookmark_id):
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    ub = UserBookmark.query.filter_by(user_id=user_id, bookmark_id=bookmark_id).first()
    if not ub:
        return jsonify({'error': 'Not found or access denied'}), 404

    db.session.delete(ub)
    db.session.commit()

    return jsonify({'message': 'Bookmark removed'}), 200

# export bookmark
@bp.route('/export', methods=['GET'])
@login_required
def export_bookmarks():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    bookmarks = db.session.query(Bookmark).join(UserBookmark).filter(UserBookmark.user_id == user_id).all()
    if not bookmarks:
        return jsonify({'error': 'No bookmarks found'}), 404

    ist = pytz.timezone('Asia/Kolkata')
    html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>LinkVault Export</TITLE>
<H1>LinkVault Bookmarks</H1>
<DL><p>\n"""

    for b in bookmarks:
        ub = UserBookmark.query.filter_by(bookmark_id=b.id, user_id=user_id).first()
        notes = ub.notes if ub else ""
        tags = ",".join(t.name for t in b.tags)
        title = (ub.title if ub else b.url).replace('&', '&amp;').replace('<', '&lt;')
        created_ist = (ub.created_at if ub else b.created_at).replace(tzinfo=pytz.UTC).astimezone(ist)
        add_date = int(created_ist.timestamp())
        html += f'    <DT><A HREF="{b.url}" ADD_DATE="{add_date}" TAGS="{tags}">{title}</A>\n'
        if notes:
            html += f'    <DD>{notes.replace("&", "&amp;")}</DD>\n'

    html += "</DL><p>"

    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f"attachment;filename=linkvault_user{user_id}_{datetime.now().strftime('%Y%m%d')}.html"}
    )

# list tags with count
@bp.route('/tags', methods=['GET'])
def list_tags():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # Subquery: max bookmark_count per tag for this user
    subq = db.select(
        tag_user_bookmarks.c.tag_id,
        db.func.max(tag_user_bookmarks.c.bookmark_count).label('cnt')
    ).where(
        tag_user_bookmarks.c.user_id == user_id
    ).group_by(tag_user_bookmarks.c.tag_id).subquery()

    # Join with Tag, filter count > 0
    tags = db.session.query(
        Tag.name,
        subq.c.cnt.label('count')
    ).join(
        subq, Tag.id == subq.c.tag_id
    ).filter(
        subq.c.cnt > 0
    ).order_by(
        db.desc('count'), Tag.name
    ).all()

    return jsonify([{'name': n, 'count': c} for n, c in tags])

# list bookmark with filtering
@bp.route('/bookmarks', methods=['GET'])
@login_required
def list_bookmarks():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    tag = request.args.get('tag')
    q = request.args.get('q')
    archived = request.args.get('archived')

    query = db.session.query(Bookmark).join(UserBookmark).filter(UserBookmark.user_id == user_id)

    if tag:
        query = query.join(tag_user_bookmarks).join(Tag).filter(Tag.name == tag.lower())
    if q:
        query = query.join(UserBookmark).filter(
            db.or_(UserBookmark.title.ilike(f'%{q}%'), Bookmark.url.ilike(f'%{q}%'))
        )
    if archived is not None:
        archived_bool = archived.lower() == 'true'
        query = query.filter(UserBookmark.archived == archived_bool)

    total = query.count()
    bookmarks = query.order_by(UserBookmark.created_at.desc()) \
                     .offset((page-1)*per_page).limit(per_page).all()

    return jsonify({
        'bookmarks': [b.to_dict(user_id=user_id) for b in bookmarks],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

# error handling
@bp.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad Request', 'message': str(e)}), 400

@bp.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not Found'}), 404

@bp.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({'error': 'Server Error'}), 500