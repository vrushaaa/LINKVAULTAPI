"""
LinkVault Dummy Data Initializer
Run: python init_db.py
"""

from app import create_app, db
from app.models.bookmark import Bookmark, bookmark_tags, normalize_url, generate_url_hash
from app.models.tag import Tag

DUMMY_DATA = [
    {
        "url": "https://github.com",
        "title": "GitHub - Where the world builds software",
        "notes": "Code hosting platform with Git",
        "tags": ["code", "git", "oss", "programming"],
        "archived": False
    },
    {
        "url": "https://python.org",
        "title": "Python Official Site",
        "notes": "Main site for Python language",
        "tags": ["python", "programming", "dev"],
        "archived": False
    },
    {
        "url": "https://flask.palletsprojects.com",
        "title": "Flask Web Framework",
        "notes": "Micro web framework for Python",
        "tags": ["flask", "web", "python"],
        "archived": False
    },
    {
        "url": "https://getbootstrap.com",
        "title": "Bootstrap CSS Framework",
        "notes": "Frontend toolkit for responsive design",
        "tags": ["css", "web", "design"],
        "archived": True
    },
    {
        "url": "https://stackoverflow.com",
        "title": "Stack Overflow - Q&A for Developers",
        "notes": "Ask programming questions",
        "tags": ["help", "coding", "stackoverflow"],
        "archived": False
    },
    {
        "url": "https://old-site.example.com",
        "title": "Legacy Project Archive",
        "notes": "Deprecated internal tool",
        "tags": ["archive", "legacy", "internal"],
        "archived": True
    },
    {
        "url": "https://docs.python.org/3/tutorial/",
        "title": "Python Tutorial",
        "notes": "Official Python beginner guide",
        "tags": ["python", "tutorial", "learning"],
        "archived": False
    },
    {
        "url": "https://reactjs.org",
        "title": "React – A JavaScript library",
        "notes": "Frontend UI library",
        "tags": ["react", "javascript", "frontend"],
        "archived": False
    },
    {
        "url": "https://example.com/search?q=test",
        "title": "Example Search Page",
        "notes": "Demo with query params",
        "tags": ["demo", "test"],
        "archived": False
    },
    {
        "url": "https://github.com/torvalds/linux",
        "title": "Linux Kernel",
        "notes": "Source code for Linux OS",
        "tags": ["linux", "kernel", "oss"],
        "archived": True
    }
]

def init_db_with_data():
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating tables...")
        db.create_all()

        print(f"Adding {len(DUMMY_DATA)} bookmarks...")

        for item in DUMMY_DATA:
            url = item["url"]
            norm_url = normalize_url(url)
            url_hash = generate_url_hash(url)

            if Bookmark.query.filter_by(hash_url=url_hash).first():
                print(f"Skipping duplicate: {url}")
                continue

            bookmark = Bookmark(
                url=norm_url,
                title=item["title"],
                notes=item["notes"],
                archived=item["archived"]
            )
            bookmark.set_hash()
            bookmark.set_short_url()
            db.session.add(bookmark)
            db.session.flush()  # ← Give bookmark an ID

            for tag_name in item["tags"]:
                tag_name = tag_name.lower()
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()  # ← Give tag an ID
                bookmark.tags.append(tag)

            db.session.add(bookmark)

        db.session.commit()
        print("Dummy data loaded successfully!")

        # FIX TAG COUNTS
        print("Updating Tag.bookmark_count...")
        for tag in Tag.query.all():
            count = db.session.scalar(
                db.select(db.func.count())
                .select_from(bookmark_tags)
                .where(bookmark_tags.c.tag_id == tag.id)
            )
            tag.bookmark_count = count
        db.session.commit()
        print("Tag counts updated!")

        print("Try: curl http://127.0.0.1:5000/api/bookmarks?tag=python")

if __name__ == "__main__":
    init_db_with_data()