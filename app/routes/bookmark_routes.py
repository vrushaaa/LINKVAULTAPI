import os
import tempfile
from flask import Blueprint, current_app, flash, render_template, request, jsonify, url_for, redirect
from flask_login import login_required, current_user  # ← ADD THIS
from app import db
from app.models.bookmark import Bookmark, generate_url_hash, normalize_url
from app.models.tag import Tag
from app.models.user import User
from app.models.user_bookmark import UserBookmark
from app.models.tag_user_bookmark import tag_user_bookmarks
from urllib.parse import urljoin
import pytz
from datetime import datetime

bp = Blueprint('bookmarks_api', __name__)
short_bp = Blueprint('short', __name__)

# Title extraction
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

# Home page
@short_bp.route('/')
def home():
    return render_template('home.html')

# CREATE BOOKMARK — SECURE
# @bp.route('/bookmarks', methods=['POST'])
# @login_required
# def create_bookmark():
#     data = request.get_json() or {}
#     url = data.get('url')
#     title = data.get('title')
#     notes = data.get('notes')
#     tags = data.get('tags', [])
#     archived = data.get('archived', False)

#     if not url:
#         return jsonify({'error': 'URL is required'}), 400

#     norm_url = normalize_url(url)
#     url_hash = generate_url_hash(url)

#     # ← CHECK DUPLICATE FOR THIS USER ONLY
#     existing = Bookmark.query.filter_by(hash_url=url_hash, user_id=current_user.id).first()
#     if existing :
#         short_url = url_for('short.redirect_short', short_code=existing.short_url, _external=True)
#         return jsonify({
#             'message': 'You already saved this URL',
#             'bookmark': {
#                 'id': existing.id,
#                 'url': existing.url,
#                 'short_url': existing.short_url,
#                 'full_short_url': short_url
#             }
#         }), 409

#     # ← ADD USER_ID
#     bookmark = Bookmark(
#         url=norm_url,
#         user_id=current_user.id,
#         notes=notes,
#         archived=archived
#     )
#     bookmark.set_hash()
#     bookmark.set_short_url()

#     if not title:
#         title = extract_title(norm_url)
#     bookmark.title = title

#     for tag_name in tags:
#         tag_name = tag_name.strip().lower()
#         if tag_name:
#             tag = Tag.query.filter_by(name=tag_name).first()
#             if not tag:
#                 tag = Tag(name=tag_name)
#                 db.session.add(tag)
#             bookmark.tags.append(tag)

#     db.session.add(bookmark)
#     db.session.commit()

#     short_url = url_for('short.redirect_short', short_code=bookmark.short_url, _external=True)
#     ist_time = bookmark.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))

#     return jsonify({
#         'message': 'Bookmark created',
#         'bookmark': {
#             'id': bookmark.id,
#             'url': bookmark.url,
#             'short_url': bookmark.short_url,
#             'full_short_url': short_url,
#             'title': bookmark.title,
#             'created_at': ist_time.strftime('%Y-%m-%d %H:%M:%S IST'),
#             'tags': [t.name for t in bookmark.tags]
#         }
#     }), 201



# In bookmark_routes.py
@bp.route('/')
@login_required
def dashboard():
    total = Bookmark.query.filter_by(user_id=current_user.id).count()
    archived = Bookmark.query.filter_by(user_id=current_user.id, archived=True).count()

    top_tags = db.session.query(
        Tag.name,
        db.func.count(Tag.name).label('count')
    ).join(
        Tag.bookmarks
    ).filter(
        Bookmark.user_id == current_user.id
    ).group_by(
        Tag.name
    ).order_by(
        db.func.count(Tag.name).desc()
    ).limit(5).all()

    # return render_template('dashboard.html', total=total, archived=archived, top_tags=top_tags)
    return render_template('dashboard.html')

@bp.route('/add')
@login_required
def create_bookmark_get():
    return render_template('add_bookmark.html')


# In bookmark_routes.py
@bp.route('/bookmarks', methods=['POST'])
@login_required
def create_bookmark():
    # === WEB FORM SUBMISSION ===
    if request.form:
        url = request.form.get('url')
        title = request.form.get('title')
        notes = request.form.get('notes')
        tags_input = request.form.get('tags', '')
        archived = bool(request.form.get('archived'))

    # === API JSON SUBMISSION (Postman, Mobile, etc.) ===
    elif request.is_json:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title')
        notes = data.get('notes')
        tags_input = ','.join(data.get('tags', [])) if data.get('tags') else ''
        archived = data.get('archived', False)

    else:
        if request.is_json:
            return jsonify({'error': 'Invalid content type'}), 400
        flash('Invalid request', 'error')
        return redirect(url_for('bookmarks_api.create_bookmark_get'))

    # === VALIDATE URL ===
    if not url:
        if request.is_json:
            return jsonify({'error': 'URL is required'}), 400
        flash('URL is required', 'error')
        return redirect(url_for('bookmarks_api.create_bookmark_get'))

    # === NORMALIZE & HASH URL ===
    norm_url = normalize_url(url)
    url_hash = generate_url_hash(norm_url)

    # === CHECK DUPLICATE ===
    existing = Bookmark.query.filter_by(hash_url=url_hash, user_id=current_user.id).first()
    if existing:
        if request.is_json:
            return jsonify({
                'message': 'You already saved this URL',
                'bookmark_id': existing.id,
                'short_url': url_for('short.redirect_short', short_code=existing.short_url, _external=True)
            }), 409
        flash('You already saved this URL!', 'error')
        return redirect(url_for('bookmarks_api.list_bookmarks'))

    # === CREATE BOOKMARK ===
    bookmark = Bookmark(
        url=norm_url,
        user_id=current_user.id,
        notes=notes,
        archived=archived
    )
    bookmark.set_hash()
    bookmark.set_short_url()
    print("Generated short_url:", bookmark.short_url)
    # # === GENERATE UNIQUE SHORT URL ===
    # for _ in range(100):
    #     bookmark.set_short_url()
    #     if not Bookmark.query.filter_by(short_url=bookmark.short_url).first():
    #         break
    # else:
    #     if request.is_json:
    #         return jsonify({'error': 'Failed to generate unique short URL'}), 500
    #     flash('Failed to generate short URL', 'error')
    #     return redirect(url_for('bookmarks_api.create_bookmark_get'))

    # === SET TITLE (Auto-fetch if empty) ===
    if not title:
        title = extract_title(norm_url)
    bookmark.title = title or "Untitled"

    # === ADD TAGS ===
    if tags_input:
        tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            bookmark.tags.append(tag)

    # === SAVE TO DATABASE ===
    db.session.add(bookmark)
    db.session.commit()

    # === GENERATE FULL SHORT URL ===
    full_short_url = url_for('short.redirect_short', short_code=bookmark.short_url, _external=True)

    # === API RESPONSE (Postman) ===
    if request.is_json:
        return jsonify({
            'message': 'Bookmark created successfully!',
            'bookmark': {
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'short_url': bookmark.short_url,
                'full_short_url': full_short_url,
                'notes': bookmark.notes,
                'tags': [t.name for t in bookmark.tags],
                'archived': bookmark.archived,
                'created_at': bookmark.created_at.strftime('%Y-%m-%d %H:%M:%S IST')
            }
        }), 201

    # === WEB RESPONSE (Browser) ===
    flash(f'Bookmark saved! Short URL: {full_short_url}', 'success')
    return redirect(url_for('bookmarks_api.list_bookmarks'))



# GET SINGLE — SECURE
@bp.route('/bookmarks/<int:bookmark_id>', methods=['GET'])
@login_required
def get_bookmark(bookmark_id):
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first_or_404()
    # ← ONLY USER'S BOOKMARK

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


# UPDATE — SECURE
@bp.route('/bookmarks/<int:bookmark_id>', methods=['PUT'])
@login_required
def update_bookmark(bookmark_id):
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first_or_404()
    # ← OWNERSHIP CHECK

    data = request.get_json() or {}
    if 'title' in data: bookmark.title = data['title']
    if 'notes' in data: bookmark.notes = data['notes']
    if 'archived' in data: bookmark.archived = data['archived']
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
    return jsonify({'message': 'Bookmark updated'}), 200


# DELETE — SECURE
@bp.route('/bookmarks/<int:bookmark_id>', methods=['DELETE'])
@login_required
def delete_bookmark(bookmark_id):
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first()
    
    if not bookmark:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Bookmark not found'}), 404
        flash('Bookmark not found', 'error')
        return redirect(url_for('bookmarks_api.list_bookmarks'))

    # === DELETE FROM DB ===
    db.session.delete(bookmark)
    db.session.commit()

    # === API RESPONSE ===
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': 'Bookmark deleted successfully'}), 200

    # === WEB RESPONSE ===
    flash('Bookmark deleted!', 'success')
    return redirect(url_for('bookmarks_api.list_bookmarks'))

# TOGGLE ARCHIVE — SECURE
@bp.route('/bookmarks/<int:bookmark_id>/archive', methods=['PATCH'])
@login_required
def toggle_archive(bookmark_id):
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user.id).first_or_404()
    bookmark.archived = not bookmark.archived
    db.session.commit()
    return jsonify({'archived': bookmark.archived}), 200


# SHORT URL — KEEP PUBLIC (RECOMMENDED)
@short_bp.route('/<short_code>')
def redirect_short(short_code):
    bookmark = Bookmark.query.filter_by(short_url=short_code).first_or_404()
    bookmark.updated_at = db.func.now()
    db.session.commit()

    return jsonify({'message': 'Bookmark removed'}), 200


# LIST BOOKMARKS — SECURE + FILTERS
# @bp.route('/bookmarks/', methods=['GET'])
# @login_required
# def list_bookmarks():
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('per_page', 5, type=int)
#     tag = request.args.get('tag')
#     q = request.args.get('q')
#     archived_param = request.args.get('archived')
#     bookmark_id = request.args.get('id', type=int)

#     # ← ONLY USER'S BOOKMARKS
#     query = Bookmark.query.filter_by(user_id=current_user.id)

#     if archived_param is not None:
#         archived = archived_param.lower() == 'true'
#         query = query.filter_by(archived=archived)

#     if tag:
#         tags_list = [t.strip().lower() for t in tag.split(",") if t.strip()]
#         for t in tags_list:
#             query = query.filter(Bookmark.tags.any(Tag.name == t))

#     if q:
#         search = f"%{q}%"
#         query = query.filter(
#             db.or_(
#                 Bookmark.title.ilike(search),
#                 Bookmark.url.ilike(search),
#                 Bookmark.notes.ilike(search)
#             )
#         )

#     if bookmark_id:
#         query = query.filter_by(id=bookmark_id)

#     pagination = query.order_by(Bookmark.created_at.desc()).paginate(
#         page=page, per_page=per_page, error_out=False
#     )

#     return jsonify({
#         'bookmarks': [b.to_dict() for b in pagination.items],
#         'pagination': {
#             'page': page,
#             'pages': pagination.pages,
#             'per_page': per_page,
#             'total': pagination.total,
#             'has_next': pagination.has_next,
#             'has_prev': pagination.has_prev,
#             'next_url': url_for('bookmarks_api.list_bookmarks', page=page+1, per_page=per_page, _external=True) if pagination.has_next else None,
#             'prev_url': url_for('bookmarks_api.list_bookmarks', page=page-1, per_page=per_page, _external=True) if pagination.has_prev else None,
#         }
#     })

@bp.route('/bookmarks', methods=['GET'])
@login_required
def list_bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)  # 12 for web grid
    tag = request.args.get('tag')
    q = request.args.get('q')
    archived_param = request.args.get('archived')
    bookmark_id = request.args.get('id', type=int)

    # Base query — only current user's bookmarks
    query = Bookmark.query.filter_by(user_id=current_user.id)

    # Filter by archived
    if archived_param is not None:
        archived = archived_param.lower() in ('true', '1', 'yes')
        query = query.filter_by(archived=archived)

    # Filter by tag(s)
    if tag:
        tags_list = [t.strip().lower() for t in tag.split(",") if t.strip()]
        for t in tags_list:
            query = query.filter(Bookmark.tags.any(Tag.name.ilike(t)))

    # Search in title, url, notes
    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Bookmark.title.ilike(search),
                Bookmark.url.ilike(search),
                Bookmark.notes.ilike(search)
            )
        )

    # Filter by ID
    if bookmark_id:
        query = query.filter_by(id=bookmark_id)

    # Pagination
    pagination = query.order_by(Bookmark.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    bookmarks = pagination.items

    # === API MODE: Return JSON (Postman, mobile, etc.) ===
    if request.is_json or 'application/json' in request.headers.get('Accept', ''):
        data = []
        for b in bookmarks:
            short_full = url_for('short.redirect_short', short_code=b.short_url, _external=True)
            ist_time = b.created_at.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Asia/Kolkata'))
            data.append({
                'id': b.id,
                'title': b.title or "Untitled",
                'url': b.url,
                'short_url': b.short_url,
                'full_short_url': short_full,
                'notes': b.notes or "",
                'tags': [t.name for t in b.tags],
                'archived': b.archived,
                'created_at': ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
            })

        return jsonify({
            'bookmarks': data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'total': pagination.total,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'next_url': url_for('bookmark_routes.list_bookmarks', page=page+1, per_page=per_page, **request.args.to_dict(), _external=True) if pagination.has_next else None,
                'prev_url': url_for('bookmark_routes.list_bookmarks', page=page-1, per_page=per_page, **request.args.to_dict(), _external=True) if pagination.has_prev else None,
            },
            'filters': {
                'tag': tag,
                'q': q,
                'archived': archived_param,
                'id': bookmark_id
            }
        })

    # === WEB MODE: Return HTML template ===
    return render_template(
        'bookmarks.html',
        bookmarks=bookmarks,
        pagination=pagination,
        current_filters=request.args  # For search bar persistence
    )


# EXPORT — ONLY USER'S BOOKMARKS
@bp.route('/export', methods=['GET'])
@login_required
def export_bookmarks():
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()  # ← SECURE
    if not bookmarks:
        return jsonify({'error': 'No bookmarks found'}), 404

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


