"""
LinkVault Dummy Data Initializer with Multiple Users & Shared Bookmarks
Run: python init_db.py
"""

from app import create_app, db
from app.models.bookmark import Bookmark, normalize_url, generate_url_hash, bookmark_tags
from app.models.tag import Tag
from app.models.user import User
from app.models.user_bookmark import user_bookmarks
from datetime import datetime
import random

# users
DUMMY_USERS = [
    {"username": "alice", "email": "alice@example.com"},
    {"username": "bob", "email": "bob@example.com"},
    {"username": "carol", "email": "carol@example.com"},
    {"username": "dave", "email": "dave@example.com"}
]

# bookmarks, some shared among users
DUMMY_BOOKMARKS = [
    {"url": "https://github.com", "title": "GitHub", "notes": "Code hosting", "tags": ["code", "git"], "archived": False},
    {"url": "https://python.org", "title": "Python Official", "notes": "Python site", "tags": ["python", "dev"], "archived": False},
    {"url": "https://flask.palletsprojects.com", "title": "Flask Docs", "notes": "Flask framework", "tags": ["flask", "web"], "archived": False},
    {"url": "https://getbootstrap.com", "title": "Bootstrap", "notes": "CSS framework", "tags": ["css", "web"], "archived": True},
    {"url": "https://stackoverflow.com", "title": "Stack Overflow", "notes": "Q&A site", "tags": ["help", "coding"], "archived": False},
    {"url": "https://reactjs.org", "title": "React", "notes": "JS frontend", "tags": ["react", "javascript"], "archived": False},
    {"url": "https://nodejs.org", "title": "Node.js", "notes": "JS backend", "tags": ["nodejs", "javascript"], "archived": False},
    {"url": "https://vuejs.org", "title": "Vue.js", "notes": "Frontend framework", "tags": ["vue", "javascript"], "archived": False},
    {"url": "https://angular.io", "title": "Angular", "notes": "Frontend framework", "tags": ["angular", "typescript"], "archived": False},
    {"url": "https://linux.org", "title": "Linux Info", "notes": "OS info", "tags": ["linux", "oss"], "archived": True},
    {"url": "https://docker.com", "title": "Docker", "notes": "Container platform", "tags": ["docker", "devops"], "archived": False},
    {"url": "https://kubernetes.io", "title": "Kubernetes", "notes": "Orchestration", "tags": ["k8s", "devops"], "archived": False},
    {"url": "https://aws.amazon.com", "title": "AWS Cloud", "notes": "Cloud provider", "tags": ["cloud", "aws"], "archived": False},
    {"url": "https://azure.microsoft.com", "title": "Azure Cloud", "notes": "Microsoft cloud", "tags": ["cloud", "azure"], "archived": False},
    {"url": "https://gcp.google.com", "title": "Google Cloud", "notes": "GCP", "tags": ["cloud", "gcp"], "archived": False},
    {"url": "https://mongodb.com", "title": "MongoDB", "notes": "NoSQL DB", "tags": ["database", "nosql"], "archived": False},
    {"url": "https://postgresql.org", "title": "PostgreSQL", "notes": "Relational DB", "tags": ["database", "sql"], "archived": False},
    {"url": "https://redis.io", "title": "Redis", "notes": "In-memory DB", "tags": ["database", "cache"], "archived": False},
    {"url": "https://rabbitmq.com", "title": "RabbitMQ", "notes": "Message broker", "tags": ["mq", "devops"], "archived": False},
    {"url": "https://jenkins.io", "title": "Jenkins", "notes": "CI/CD tool", "tags": ["ci", "cd"], "archived": False},
] + [
    {"url": f"https://example.com/tutorial{i}", "title": f"Tutorial {i}", "notes": f"Learning {i}", "tags": ["tutorial", "learning"], "archived": False}
    for i in range(1, 21)
]

def init_db_with_data():
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating tables...")
        db.create_all()

        # creates user here
        users = []
        print(f"Creating {len(DUMMY_USERS)} users...")
        for udata in DUMMY_USERS:
            user = User(username=udata["username"], email=udata["email"])
            db.session.add(user)
            db.session.flush()
            users.append(user)
            print(f"Created user {user.username} (ID: {user.id})")

        # creates bookmarks
        bookmarks = []
        print(f"Adding {len(DUMMY_BOOKMARKS)} bookmarks...")
        for idx, item in enumerate(DUMMY_BOOKMARKS):
            norm_url = normalize_url(item["url"])
            url_hash = generate_url_hash(norm_url)
            
            bookmark = Bookmark.query.filter_by(hash_url=url_hash).first()
            if not bookmark:
                bookmark = Bookmark(
                    url=norm_url,
                    title=item["title"],
                    notes=item["notes"],
                    archived=item["archived"]
                )
                bookmark.set_hash()
                bookmark.set_short_url()
                db.session.add(bookmark)
                db.session.flush()
            bookmarks.append(bookmark)

            # add tags
            for tag_name in item["tags"]:
                tag_name = tag_name.lower()
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                if tag not in bookmark.tags:
                    bookmark.tags.append(tag)

        db.session.commit()
        print("Bookmarks and tags added!")

        # assign bookmark to users (some shared, some unique)
        print("Assigning bookmarks to users...")
        for bookmark in bookmarks:
            # Randomly assign to 1–3 users
            assigned_users = random.sample(users, random.randint(1, 3))
            for user in assigned_users:
                stmt = user_bookmarks.insert().values(
                    user_id=user.id,
                    bookmark_id=bookmark.id,
                    notes=bookmark.notes + f" (saved by {user.username})",
                    archived=bookmark.archived,
                    saved_at=datetime.utcnow()
                )
                db.session.execute(stmt)
        db.session.commit()

        # update tag counts
        print("Updating Tag.bookmark_count...")
        for tag in Tag.query.all():
            count = db.session.scalar(
                db.select(db.func.count()).select_from(bookmark_tags).where(bookmark_tags.c.tag_id == tag.id)
            )
            tag.bookmark_count = count
        db.session.commit()
        print("Tag counts updated!")

        print("DB initialization complete!")
        print("Sample curl commands:")
        for user in users:
            print(f"curl http://127.0.0.1:5000/api/bookmarks?user_id={user.id}")

if __name__ == "__main__":
    init_db_with_data()
