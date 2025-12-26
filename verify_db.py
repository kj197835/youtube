from database import get_session, Comment, Video
from sqlalchemy.orm import outerjoin

session = get_session()
comments = session.query(Comment).outerjoin(Video).all()
print(f"Total Comments: {len(comments)}")
for c in comments:
    print(f"ID: {c.id}, Text: {c.text}, Video: {c.video_id}")
    if c.video:
        print(f"  -> Video Title: {c.video.title}")
    else:
        print("  -> No Video Rel")
