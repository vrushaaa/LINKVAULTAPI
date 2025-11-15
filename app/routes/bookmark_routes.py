import os
import tempfile
from flask import Blueprint, current_app, render_template, request, jsonify, url_for, redirect, Response
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from app.models.user import User
from app.models.user_bookmark import user_bookmarks
from urllib.parse import urljoin
import pytz
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Blueprints
bp = Blueprint('bookmarks_api', __name__, url_prefix='/api')
short_bp = Blueprint('short', __name__)

# ===================== TITLE EXTRACTION (SAFE & ISOLATED) =====================
def extract_title(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=8, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else None
    except Exception:
        return None

# ===================== HOME PAGE =====================
@short_bp.route('/')
def home():
    return render_template('welcome.html'), 200

# ===================== CREATE BOOKMARK (FIXED & FINAL) =====================
@bp.route('/bookmarks', methods=['POST'])
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
        # Check if user already has it
        stmt = user_bookmarks.select().where(
            user_bookmarks.c.user_id == user_id,
            user_bookmarks.c.bookmark_id == existing.id
        )
        if db.session.execute(stmt).scalar():
            return jsonify({'error': 'You already saved this link'}), 409
        bookmark = existing
    else:
        bookmark = Bookmark(url=norm_url, notes='', archived=False)
        bookmark.set_hash()
        bookmark.set_short_url()
        db.session.add(bookmark)
        db.session.flush()

        # Auto extract title if not provided and new bookmark
        if not title:
            title = extract_title(norm_url) or "Untitled Link"
        bookmark.title = title

    # Link user via junction
    db.session.execute(
        user_bookmarks.insert().values(
            user_id=user_id,
            bookmark_id=bookmark.id,
            notes=notes,
            archived=archived
        )
    )

    # Handle tags
    if tags:
        bookmark.tags.clear()
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                bookmark.tags.append(tag)

    db.session.commit()

    return jsonify({
        'message': 'Bookmark saved successfully',
        'bookmark': bookmark.to_dict(user_id=user_id)
    }), 201

# ===================== GET SINGLE BOOKMARK =====================
@bp.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    if not bookmark:
        return jsonify({'error': 'Bookmark not found'}), 404
    return jsonify(bookmark.to_dict()), 200

# ===================== UPDATE BOOKMARK =====================
@bp.route('/bookmarks/<int:bookmark_id>', methods=['PUT'])
def update_bookmark(bookmark_id):
    # NEVER use or {} — it hides 400 errors
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # Check ownership
    link = db.session.execute(
        user_bookmarks.select().where(
            user_bookmarks.c.bookmark_id == bookmark_id,
            user_bookmarks.c.user_id == user_id
        )
    ).first()

    if not link:
        return jsonify({'error': 'Access denied or not found'}), 404

    bookmark = Bookmark.query.get(bookmark_id)
    updated = False

    # Update title
    if 'title' in data:
        bookmark.title = data['title']
        updated = True

    # Update notes in junction table
    if 'notes' in data:
        db.session.execute(
            user_bookmarks.update()
            .where(
                user_bookmarks.c.bookmark_id == bookmark_id,
                user_bookmarks.c.user_id == user_id
            )
            .values(notes=data['notes'])
        )
        updated = True

    # Update archived in junction table
    if 'archived' in data:
        db.session.execute(
            user_bookmarks.update()
            .where(
                user_bookmarks.c.bookmark_id == bookmark_id,
                user_bookmarks.c.user_id == user_id
            )
            .values(archived=data['archived'])
        )
        updated = True

    # Update tags
    if 'tags' in data:
        bookmark.tags.clear()
        for tag_name in data.get('tags', []):
            tag_name = tag_name.strip().lower()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                bookmark.tags.append(tag)
        updated = True

    # ONLY update timestamp if something changed
    if updated:
        bookmark.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({
        'message': 'Updated',
        'bookmark': bookmark.to_dict(user_id=user_id)
    }), 200

# ===================== DELETE BOOKMARK =====================
@bp.route('/bookmarks/<int:bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    result = db.session.execute(
        user_bookmarks.delete().where(
            user_bookmarks.c.bookmark_id == bookmark_id,
            user_bookmarks.c.user_id == user_id
        )
    )
    db.session.commit()

    if result.rowcount == 0:
        return jsonify({'error': 'Not found or access denied'}), 404

    return jsonify({'message': 'Bookmark removed'})

# ===================== TOGGLE ARCHIVE =====================
from sqlalchemy import update, not_, func
from datetime import datetime
from app.models.bookmark import Bookmark

@bp.route('/bookmarks/<int:bookmark_id>/archive', methods=['PATCH'])
def toggle_archive(bookmark_id):
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # 1. Toggle archived in user_bookmarks
    result = db.session.execute(
        update(user_bookmarks)
        .where(
            user_bookmarks.c.bookmark_id == bookmark_id,
            user_bookmarks.c.user_id == user_id
        )
        .values(archived=not_(user_bookmarks.c.archived))
        .returning(user_bookmarks.c.archived)
    )

    row = result.fetchone()
    if not row:
        return jsonify({'error': 'Not found or access denied'}), 404

    # 2. Update Bookmark.updated_at
    db.session.execute(
        update(Bookmark)
        .where(Bookmark.id == bookmark_id)
        .values(updated_at=datetime.utcnow())
    )

    db.session.commit()

    return jsonify({
        'message': 'Archive toggled',
        'archived': row[0]
    })

# ===================== SHORT URL REDIRECT =====================
@short_bp.route('/<short_code>')
def redirect_short(short_code):
    bookmark = Bookmark.query.filter_by(short_url=short_code).first_or_404()
    bookmark.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(bookmark.url)

# ===================== EXPORT BOOKMARKS =====================
@bp.route('/export', methods=['GET'])
def export_bookmarks():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    bookmarks = db.session.query(Bookmark).join(user_bookmarks).filter(user_bookmarks.c.user_id == user_id).all()
    if not bookmarks:
        return jsonify({'error': 'No bookmarks found'}), 404

    ist = pytz.timezone('Asia/Kolkata')
    html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>LinkVault Export</TITLE>
<H1>LinkVault Bookmarks</H1>
<DL><p>\n"""

    for b in bookmarks:
        link = db.session.execute(
            user_bookmarks.select().where(
                user_bookmarks.c.bookmark_id == b.id,
                user_bookmarks.c.user_id == user_id
            )
        ).first()
        notes = link.notes if link else ""
        tags = ",".join(t.name for t in b.tags)
        title = (b.title or b.url).replace('&', '&amp;').replace('<', '&lt;')
        created_ist = b.created_at.replace(tzinfo=pytz.UTC).astimezone(ist)
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

# ===================== LIST TAGS =====================
@bp.route('/tags', methods=['GET'])
def list_tags():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    tags = db.session.query(Tag.name, db.func.count(user_bookmarks.c.bookmark_id).label('count')) \
        .join(Tag.bookmarks).join(user_bookmarks) \
        .filter(user_bookmarks.c.user_id == user_id) \
        .group_by(Tag.name) \
        .order_by(db.desc('count')).all()

    return jsonify([{'name': n, 'count': c} for n, c in tags])

# ===================== LIST BOOKMARKS WITH FILTERING =====================
@bp.route('/bookmarks', methods=['GET'])
def list_bookmarks():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    tag = request.args.get('tag')
    q = request.args.get('q')
    archived = request.args.get('archived')

    query = db.session.query(Bookmark).join(user_bookmarks).filter(user_bookmarks.c.user_id == user_id)

    if tag:
        query = query.join(Bookmark.tags).filter(Tag.name == tag.lower())
    if q:
        query = query.filter(
            db.or_(Bookmark.title.ilike(f'%{q}%'), Bookmark.url.ilike(f'%{q}%'))
        )
    if archived is not None:
        archived_bool = archived.lower() == 'true'
        query = query.filter(user_bookmarks.c.archived == archived_bool)

    total = query.count()
    bookmarks = query.order_by(Bookmark.created_at.desc()) \
                     .offset((page-1)*per_page).limit(per_page).all()

    return jsonify({
        'bookmarks': [b.to_dict(user_id=user_id) for b in bookmarks],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

# ===================== ERROR HANDLERS =====================
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