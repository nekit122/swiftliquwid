import os
import json
import uuid
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from io import BytesIO

from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary, JSON as SAJSON
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
import bcrypt

# ============ НАСТРОЙКИ БД ============
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nvtulka.db")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="NVTULKA 💠", version="3.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============ МОДЕЛИ БД ============
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_password = Column(String(255), nullable=False)
    avatar_data = Column(LargeBinary, nullable=True)
    avatar_mime = Column(String(50), default="image/jpeg")
    bio = Column(Text, default="")
    theme = Column(String(20), default="dark")
    bg_data = Column(LargeBinary, nullable=True)
    bg_mime = Column(String(50), default="image/jpeg")
    is_blocked = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user", cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="Follow.following_id", back_populates="following_user", cascade="all, delete-orphan")
    following = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower_user", cascade="all, delete-orphan")

class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, autoincrement=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    follower_user = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following_user = relationship("User", foreign_keys=[following_id], back_populates="followers")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, default="")
    is_story = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="posts")
    files = relationship("PostFile", back_populates="post", cascade="all, delete-orphan")
    reactions = relationship("PostReaction", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    poll = relationship("PostPoll", back_populates="post", uselist=False, cascade="all, delete-orphan")
    views = relationship("PostView", back_populates="post", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="post", cascade="all, delete-orphan")

class PostFile(Base):
    __tablename__ = "post_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    filename = Column(String(500), default="file")
    file_type = Column(String(20), nullable=False)
    mime_type = Column(String(100), default="application/octet-stream")
    post = relationship("Post", back_populates="files")

class PostReaction(Base):
    __tablename__ = "post_reactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    emoji = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    post = relationship("Post", back_populates="reactions")

class PostPoll(Base):
    __tablename__ = "post_polls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    question = Column(String(500), nullable=False)
    options = Column(SAJSON, nullable=False)
    votes = Column(SAJSON, default=lambda: {})
    post = relationship("Post", back_populates="poll")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, default="")
    is_voice = Column(Boolean, default=False)
    voice_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    post = relationship("Post", back_populates="comments")
    comment_user = relationship("User", foreign_keys=[user_id])

class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    post = relationship("Post", back_populates="bookmarks")

class PostView(Base):
    __tablename__ = "post_views"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)
    post = relationship("Post", back_populates="views")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_group = Column(Boolean, default=False)
    name = Column(String(100), default="")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")

class ChatMember(Base):
    __tablename__ = "chat_members"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="members")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, default="")
    is_voice = Column(Boolean, default=False)
    voice_data = Column(LargeBinary, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    file_name = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User", foreign_keys=[user_id])

class ChatTyping(Base):
    __tablename__ = "chat_typing"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_typing = Column(DateTime, default=datetime.utcnow)

class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    file_mime = Column(String(50), default="image/jpeg")
    text_overlay = Column(Text, default="")
    text_position = Column(SAJSON, default=lambda: {"x": 50, "y": 50, "scale": 1})
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="stories")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    type = Column(String(30), nullable=False)
    post_id = Column(Integer, nullable=True)
    comment_id = Column(Integer, nullable=True)
    message = Column(Text, default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")

class AdminLog(Base):
    __tablename__ = "admin_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(100), nullable=False)
    target_user_id = Column(Integer, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ============ ЗАВИСИМОСТИ ============
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if user_id and user_id.isdigit():
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user and not user.is_blocked:
            return user
    return None

# ============ ХЕЛПЕРЫ ============
def is_new_year_period():
    now = datetime.utcnow()
    return (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 15)

def get_unread_notifications_count(user_id: int, db: Session):
    return db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).count()

def create_notification(db, user_id, from_user_id, n_type, post_id=None, comment_id=None, message=""):
    if user_id == from_user_id:
        return
    notif = Notification(user_id=user_id, from_user_id=from_user_id, type=n_type, post_id=post_id, comment_id=comment_id, message=message)
    db.add(notif)
    db.commit()

def format_post_json(post, user, viewed_ids=None):
    files_data = []
    for f in post.files:
        ext = f.filename.split('.')[-1] if '.' in f.filename else ''
        files_data.append({
            "path": f"/file/post/{f.id}",
            "type": f.file_type,
            "filename": f.filename
        })
    reactions = {}
    for r in post.reactions:
        reactions[r.emoji] = reactions.get(r.emoji, 0) + 1
    user_reaction = None
    for r in post.reactions:
        if r.user_id == user.id:
            user_reaction = r.emoji
            break
    result = {
        "id": post.id, "content": post.content, "created_at": post.created_at.isoformat(),
        "edited": post.edited_at is not None,
        "author": {
            "username": post.user.username,
            "avatar": f"/file/avatar/{post.user.id}" if post.user.avatar_data else ""
        },
        "files": files_data, "reactions": reactions, "user_reaction": user_reaction,
        "comments_count": len(post.comments),
    }
    if viewed_ids is not None:
        result["viewed"] = post.id in viewed_ids
    return result

# ============ ФАЙЛОВЫЙ СЕРВЕР ============
@app.get("/file/avatar/{user_id}")
async def get_avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.avatar_data:
        return StreamingResponse(BytesIO(user.avatar_data), media_type=user.avatar_mime or "image/jpeg")
    return RedirectResponse(url="/static/default_avatar.svg", status_code=302)

@app.get("/file/background/{user_id}")
async def get_bg(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.bg_data:
        return StreamingResponse(BytesIO(user.bg_data), media_type=user.bg_mime or "image/jpeg")
    raise HTTPException(status_code=404)

@app.get("/file/post/{file_id}")
async def get_post_file(file_id: int, db: Session = Depends(get_db)):
    pf = db.query(PostFile).filter(PostFile.id == file_id).first()
    if pf and pf.file_data:
        return StreamingResponse(BytesIO(pf.file_data), media_type=pf.mime_type)
    raise HTTPException(status_code=404)

@app.get("/file/story/{story_id}")
async def get_story_file(story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if story and story.file_data:
        return StreamingResponse(BytesIO(story.file_data), media_type=story.file_mime or "image/jpeg")
    raise HTTPException(status_code=404)

@app.get("/file/voice_comment/{comment_id}")
async def get_voice_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment and comment.voice_data:
        return StreamingResponse(BytesIO(comment.voice_data), media_type="audio/webm")
    raise HTTPException(status_code=404)

@app.get("/file/chat_voice/{msg_id}")
async def get_chat_voice(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()
    if msg and msg.voice_data:
        return StreamingResponse(BytesIO(msg.voice_data), media_type="audio/webm")
    raise HTTPException(status_code=404)

@app.get("/file/chat_file/{msg_id}")
async def get_chat_file(msg_id: int, db: Session = Depends(get_db)):
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()
    if msg and msg.file_data:
        return StreamingResponse(BytesIO(msg.file_data), media_type="application/octet-stream")
    raise HTTPException(status_code=404)

# ============ ГЛАВНАЯ ============
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, filter: str = Query("all"), db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    following_ids = [f.following_id for f in user.following]
    following_ids.append(user.id)
    query = db.query(Post).filter(Post.user_id.in_(following_ids), Post.is_story == False)
    if filter == "photo":
        pids = [p[0] for p in db.query(PostFile.post_id).filter(PostFile.file_type == "image").distinct().all()]
        query = query.filter(Post.id.in_(pids)) if pids else query.filter(Post.id == -1)
    elif filter == "video":
        vids = [p[0] for p in db.query(PostFile.post_id).filter(PostFile.file_type == "video").distinct().all()]
        query = query.filter(Post.id.in_(vids)) if vids else query.filter(Post.id == -1)
    posts = query.order_by(Post.created_at.desc()).limit(20).all()
    user_reactions = {}
    if posts:
        reactions = db.query(PostReaction).filter(PostReaction.post_id.in_([p.id for p in posts]), PostReaction.user_id == user.id).all()
        for r in reactions:
            user_reactions[r.post_id] = r.emoji
    unread = get_unread_notifications_count(user.id, db)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "posts": posts, "user_reactions": user_reactions, "unread_notifs": unread, "is_new_year": is_new_year_period(), "filter_type": filter})

# ============ АВТОРИЗАЦИЯ ============
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, response: Response, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return HTMLResponse("<script>alert('Неверный логин или пароль'); window.location.href='/login';</script>")
    if user.is_blocked:
        return HTMLResponse("<script>alert('Аккаунт заблокирован'); window.location.href='/login';</script>")
    user.is_online = True
    user.last_seen = datetime.utcnow()
    db.commit()
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie(key="user_id", value=str(user.id), max_age=30*24*3600, httponly=True)
    return resp

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db), username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        return HTMLResponse("<script>alert('Уже существует'); window.location.href='/register';</script>")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.add(User(username=username, email=email, password_hash=hashed, real_password=password, created_at=datetime.utcnow(), last_seen=datetime.utcnow()))
    db.commit()
    return HTMLResponse("<script>alert('Успешно!'); window.location.href='/login';</script>")

@app.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        user.is_online = False
        user.last_seen = datetime.utcnow()
        db.commit()
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("user_id")
    return resp

# ============ ПРОФИЛЬ ============
@app.get("/profile/{username}", response_class=HTMLResponse)
async def profile(request: Request, username: str, db: Session = Depends(get_db)):
    current_user = get_current_user_optional(request, db)
    profile_user = db.query(User).filter(User.username == username).first()
    if not profile_user:
        raise HTTPException(status_code=404)
    posts = db.query(Post).filter(Post.user_id == profile_user.id, Post.is_story == False).order_by(Post.created_at.desc()).all()
    stories = db.query(Story).filter(Story.user_id == profile_user.id, Story.expires_at > datetime.utcnow()).all()
    is_following = False
    if current_user:
        is_following = db.query(Follow).filter(Follow.follower_id == current_user.id, Follow.following_id == profile_user.id).first() is not None
    followers_count = db.query(Follow).filter(Follow.following_id == profile_user.id).count()
    following_count = db.query(Follow).filter(Follow.follower_id == profile_user.id).count()
    activity_dates, activity_counts = [], []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        count = db.query(Post).filter(Post.user_id == profile_user.id, Post.is_story == False, Post.created_at >= day.replace(hour=0, minute=0, second=0), Post.created_at < (day + timedelta(days=1)).replace(hour=0, minute=0, second=0)).count()
        activity_dates.append(day.strftime("%d.%m"))
        activity_counts.append(count)
    unread = get_unread_notifications_count(current_user.id, db) if current_user else 0
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user, "profile_user": profile_user, "posts": posts, "stories": stories, "is_following": is_following, "followers_count": followers_count, "following_count": following_count, "activity_dates": activity_dates, "activity_counts": activity_counts, "unread_notifs": unread, "is_new_year": is_new_year_period()})

@app.post("/profile/edit")
async def edit_profile(request: Request, db: Session = Depends(get_db), bio: str = Form(""), theme: str = Form("dark"), avatar: UploadFile = File(None), bg_image: UploadFile = File(None)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    if bio: user.bio = bio
    if theme: user.theme = theme
    if avatar and avatar.filename:
        user.avatar_data = await avatar.read()
        user.avatar_mime = avatar.content_type or "image/jpeg"
    if bg_image and bg_image.filename:
        user.bg_data = await bg_image.read()
        user.bg_mime = bg_image.content_type or "image/jpeg"
    db.commit()
    return RedirectResponse(url=f"/profile/{user.username}", status_code=302)

# ============ ПОСТЫ ============
@app.post("/post/create")
async def create_post(request: Request, db: Session = Depends(get_db), content: str = Form(""), files: List[UploadFile] = File([])):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    post = Post(user_id=user.id, content=content)
    db.add(post)
    db.flush()
    for file in files:
        if file.filename:
            ext = Path(file.filename).suffix.lower()
            ft = "image" if ext in [".jpg",".jpeg",".png",".gif",".webp",".svg"] else "video" if ext in [".mp4",".webm",".mov",".avi"] else "document"
            data = await file.read()
            db.add(PostFile(post_id=post.id, file_data=data, filename=file.filename, file_type=ft, mime_type=file.content_type or "application/octet-stream"))
    db.commit()
    return RedirectResponse(url="/", status_code=302)

@app.post("/post/{post_id}/edit")
async def edit_post(request: Request, post_id: int, db: Session = Depends(get_db), content: str = Form("")):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if post:
        post.content = content
        post.edited_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/", status_code=302)

@app.post("/post/{post_id}/delete")
async def delete_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse(url="/", status_code=302)

@app.get("/post/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404)
    if user:
        if not db.query(PostView).filter(PostView.post_id == post_id, PostView.user_id == user.id).first():
            db.add(PostView(post_id=post_id, user_id=user.id))
            db.commit()
    user_reaction = None
    if user:
        r = db.query(PostReaction).filter(PostReaction.post_id == post_id, PostReaction.user_id == user.id).first()
        if r: user_reaction = r.emoji
    views_data = []
    for v in post.views:
        vu = db.query(User).filter(User.id == v.user_id).first()
        if vu: views_data.append({"username": vu.username, "avatar": f"/file/avatar/{vu.id}" if vu.avatar_data else "", "viewed_at": v.viewed_at.strftime('%d.%m.%Y %H:%M')})
    unread = get_unread_notifications_count(user.id, db) if user else 0
    return templates.TemplateResponse("post_detail.html", {"request": request, "user": user, "post": post, "user_reaction": user_reaction, "unread_notifs": unread, "is_new_year": is_new_year_period(), "views_data": views_data})

# ============ РЕАКЦИИ ============
@app.post("/post/{post_id}/react")
async def react_post(request: Request, post_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    emoji = data.get("emoji", "")
    existing = db.query(PostReaction).filter(PostReaction.post_id == post_id, PostReaction.user_id == user.id).first()
    if existing:
        if existing.emoji == emoji:
            db.delete(existing)
        else:
            existing.emoji = emoji
    else:
        db.add(PostReaction(post_id=post_id, user_id=user.id, emoji=emoji))
        post = db.query(Post).filter(Post.id == post_id).first()
        if post: create_notification(db, post.user_id, user.id, "like", post_id=post_id)
    db.commit()
    reactions = db.query(PostReaction).filter(PostReaction.post_id == post_id).all()
    rc, ur = {}, None
    for r in reactions:
        rc[r.emoji] = rc.get(r.emoji, 0) + 1
        if r.user_id == user.id: ur = r.emoji
    return JSONResponse({"reactions": rc, "user_reaction": ur})

# ============ КОММЕНТАРИИ ============
@app.post("/post/{post_id}/comment")
async def add_comment(request: Request, post_id: int, db: Session = Depends(get_db), content: str = Form(""), voice: UploadFile = File(None)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    voice_data = None
    if voice and voice.filename:
        voice_data = await voice.read()
    comment = Comment(post_id=post_id, user_id=user.id, content=content, is_voice=voice_data is not None, voice_data=voice_data)
    db.add(comment)
    db.commit()
    post = db.query(Post).filter(Post.id == post_id).first()
    if post: create_notification(db, post.user_id, user.id, "comment", post_id=post_id, comment_id=comment.id)
    return RedirectResponse(url=f"/post/{post_id}", status_code=302)

@app.post("/post/{post_id}/comment/{comment_id}/delete")
async def delete_comment(request: Request, post_id: int, comment_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user.id).first()
    if not post: return JSONResponse({"error": "Forbidden"}, status_code=403)
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment:
        db.delete(comment)
        db.commit()
    return RedirectResponse(url=f"/post/{post_id}", status_code=302)

# ============ ЗАКЛАДКИ ============
@app.post("/bookmark/{post_id}")
async def toggle_bookmark(request: Request, post_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    existing = db.query(Bookmark).filter(Bookmark.user_id == user.id, Bookmark.post_id == post_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return JSONResponse({"status": "removed"})
    else:
        db.add(Bookmark(user_id=user.id, post_id=post_id))
        db.commit()
        return JSONResponse({"status": "added"})

@app.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    bms = db.query(Bookmark).filter(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc()).all()
    posts = [db.query(Post).filter(Post.id == b.post_id).first() for b in bms if db.query(Post).filter(Post.id == b.post_id).first()]
    return templates.TemplateResponse("bookmarks.html", {"request": request, "user": user, "posts": posts, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

# ============ ПОДПИСКИ ============
@app.post("/follow/{username}")
async def follow_user(request: Request, username: str, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    target = db.query(User).filter(User.username == username).first()
    if not target or target.id == user.id: return JSONResponse({"error": "Invalid"}, status_code=400)
    existing = db.query(Follow).filter(Follow.follower_id == user.id, Follow.following_id == target.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return JSONResponse({"status": "unfollowed"})
    else:
        db.add(Follow(follower_id=user.id, following_id=target.id))
        db.commit()
        create_notification(db, target.id, user.id, "follow")
        return JSONResponse({"status": "followed"})

@app.get("/followers/{username}", response_class=HTMLResponse)
async def followers_page(request: Request, username: str, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    profile_user = db.query(User).filter(User.username == username).first()
    if not profile_user: raise HTTPException(status_code=404)
    followers = db.query(Follow).filter(Follow.following_id == profile_user.id).all()
    fusers = []
    for f in followers:
        u = db.query(User).filter(User.id == f.follower_id).first()
        if u:
            mutual = db.query(Follow).filter(Follow.follower_id == profile_user.id, Follow.following_id == u.id).first() is not None
            fusers.append({"user": u, "mutual": mutual})
    unread = get_unread_notifications_count(user.id, db) if user else 0
    return templates.TemplateResponse("followers.html", {"request": request, "user": user, "profile_user": profile_user, "followers": fusers, "unread_notifs": unread, "is_new_year": is_new_year_period()})

# ============ ЧАТЫ ============
@app.get("/chats", response_class=HTMLResponse)
async def chats_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    member_chats = db.query(ChatMember).filter(ChatMember.user_id == user.id).all()
    chat_list = []
    for m in member_chats:
        chat = db.query(Chat).filter(Chat.id == m.chat_id).first()
        if chat:
            last_msg = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).order_by(ChatMessage.id.desc()).first()
            other_user = None
            if not chat.is_group:
                om = db.query(ChatMember).filter(ChatMember.chat_id == chat.id, ChatMember.user_id != user.id).first()
                if om: other_user = db.query(User).filter(User.id == om.user_id).first()
            chat_list.append({"chat": chat, "last_message": last_msg, "member": m, "other_user": other_user})
    chat_list.sort(key=lambda x: x["last_message"].created_at if x["last_message"] else x["chat"].created_at, reverse=True)
    return templates.TemplateResponse("chats.html", {"request": request, "user": user, "chats": chat_list, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.get("/chat/{chat_id}", response_class=HTMLResponse)
async def chat_detail(request: Request, chat_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat: raise HTTPException(status_code=404)
    member = db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == user.id).first()
    if not member: raise HTTPException(status_code=403)
    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.id.asc()).limit(50).all()
    members_data = []
    for cm in db.query(ChatMember).filter(ChatMember.chat_id == chat_id).all():
        u = db.query(User).filter(User.id == cm.user_id).first()
        if u: members_data.append({"user": u, "role": cm.role})
    typing_users = []
    for t in db.query(ChatTyping).filter(ChatTyping.chat_id == chat_id, ChatTyping.user_id != user.id, ChatTyping.last_typing > datetime.utcnow() - timedelta(seconds=5)).all():
        u = db.query(User).filter(User.id == t.user_id).first()
        if u: typing_users.append(u.username)
    return templates.TemplateResponse("chat.html", {"request": request, "user": user, "chat": chat, "messages": messages, "members": members_data, "current_member": member, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period(), "typing_users": typing_users})

@app.post("/chat/{chat_id}/message")
async def send_message(request: Request, chat_id: int, db: Session = Depends(get_db), content: str = Form(""), voice: UploadFile = File(None), file: UploadFile = File(None)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    voice_data = None
    file_data = None
    file_name = ""
    if voice and voice.filename:
        voice_data = await voice.read()
    if file and file.filename:
        file_data = await file.read()
        file_name = file.filename
    db.add(ChatMessage(chat_id=chat_id, user_id=user.id, content=content if not voice_data else "🎤 Голосовое", is_voice=voice_data is not None, voice_data=voice_data, file_data=file_data, file_name=file_name))
    db.commit()
    return RedirectResponse(url=f"/chat/{chat_id}", status_code=302)

@app.get("/chat/{chat_id}/messages")
async def chat_messages_since(request: Request, chat_id: int, since_id: int = 0, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"messages": []})
    msgs = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id, ChatMessage.id > since_id).order_by(ChatMessage.id.asc()).all()
    return JSONResponse({"messages": [{"id": m.id, "content": m.content, "is_voice": m.is_voice, "voice_path": f"/file/chat_voice/{m.id}" if m.is_voice else "", "file_path": f"/file/chat_file/{m.id}" if m.file_data else "", "created_at": m.created_at.isoformat(), "mine": m.user_id == user.id, "sender_name": m.user.username if m.user_id != user.id else None} for m in msgs]})

@app.post("/chat/{chat_id}/typing")
async def typing_chat(request: Request, chat_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    existing = db.query(ChatTyping).filter(ChatTyping.chat_id == chat_id, ChatTyping.user_id == user.id).first()
    if existing: existing.last_typing = datetime.utcnow()
    else: db.add(ChatTyping(chat_id=chat_id, user_id=user.id, last_typing=datetime.utcnow()))
    db.commit()
    return JSONResponse({"status": "ok"})

@app.get("/chat/{chat_id}/typing_users")
async def get_typing_users(request: Request, chat_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse([])
    records = db.query(ChatTyping).filter(ChatTyping.chat_id == chat_id, ChatTyping.user_id != user.id, ChatTyping.last_typing > datetime.utcnow() - timedelta(seconds=5)).all()
    return JSONResponse([db.query(User).filter(User.id == t.user_id).first().username for t in records if db.query(User).filter(User.id == t.user_id).first()])

@app.post("/chat/start/{username}")
async def start_chat(request: Request, username: str, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    target = db.query(User).filter(User.username == username).first()
    if not target or target.id == user.id: raise HTTPException(status_code=400)
    mutual = db.query(Follow).filter(Follow.follower_id == user.id, Follow.following_id == target.id).first() and db.query(Follow).filter(Follow.follower_id == target.id, Follow.following_id == user.id).first()
    if not mutual: return HTMLResponse("<script>alert('Нужна взаимная подписка'); window.history.back();</script>")
    existing = None
    for m in db.query(ChatMember).filter(ChatMember.user_id == user.id).all():
        chat = db.query(Chat).filter(Chat.id == m.chat_id, Chat.is_group == False).first()
        if chat and db.query(ChatMember).filter(ChatMember.chat_id == chat.id, ChatMember.user_id == target.id).first():
            existing = chat; break
    if existing: return RedirectResponse(url=f"/chat/{existing.id}", status_code=302)
    chat = Chat(is_group=False, created_by=user.id)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=user.id, role="member"))
    db.add(ChatMember(chat_id=chat.id, user_id=target.id, role="member"))
    db.commit()
    return RedirectResponse(url=f"/chat/{chat.id}", status_code=302)

# ============ ГРУППЫ ============
@app.get("/create_group", response_class=HTMLResponse)
async def create_group_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    mutuals = db.query(Follow).filter(Follow.follower_id == user.id).all()
    mutual_users = []
    for f in mutuals:
        if db.query(Follow).filter(Follow.follower_id == f.following_id, Follow.following_id == user.id).first():
            u = db.query(User).filter(User.id == f.following_id).first()
            if u: mutual_users.append(u)
    return templates.TemplateResponse("create_group.html", {"request": request, "user": user, "mutual_users": mutual_users, "unread_notifs": get_unread_notifications_count(user.id, db)})

@app.post("/group/create")
async def create_group(request: Request, db: Session = Depends(get_db), name: str = Form(...), members: str = Form("")):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    chat = Chat(is_group=True, name=name, created_by=user.id)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=user.id, role="creator"))
    for uid in members.split(","):
        if uid.strip().isdigit(): db.add(ChatMember(chat_id=chat.id, user_id=int(uid.strip()), role="member"))
    db.commit()
    return RedirectResponse(url=f"/chat/{chat.id}", status_code=302)

@app.post("/group/{chat_id}/manage")
async def manage_group(request: Request, chat_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    cm = db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == user.id).first()
    if not cm or cm.role not in ["creator", "admin"]: return JSONResponse({"error": "Forbidden"}, status_code=403)
    data = await request.form()
    target = db.query(ChatMember).filter(ChatMember.chat_id == chat_id, ChatMember.user_id == int(data.get("user_id", 0))).first()
    if data.get("action") == "kick" and target and target.role != "creator": db.delete(target)
    elif data.get("action") == "promote" and target: target.role = "admin"
    elif data.get("action") == "demote" and target and target.role != "creator": target.role = "member"
    db.commit()
    return RedirectResponse(url=f"/chat/{chat_id}", status_code=302)

# ============ СТОРИС ============
@app.get("/stories", response_class=HTMLResponse)
async def stories_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    active = db.query(Story).filter(Story.expires_at > datetime.utcnow()).order_by(Story.created_at.desc()).all()
    su = {}
    for s in active:
        su.setdefault(s.user_id, []).append(s)
    users_with = []
    for uid, sts in su.items():
        u = db.query(User).filter(User.id == uid).first()
        if u: users_with.append({"user": u, "stories": sts})
    return templates.TemplateResponse("stories.html", {"request": request, "user": user, "users_with_stories": users_with, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.post("/story/create")
async def create_story(request: Request, db: Session = Depends(get_db), file: UploadFile = File(...), text_overlay: str = Form(""), text_x: float = Form(50), text_y: float = Form(50), text_scale: float = Form(1)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    data = await file.read()
    db.add(Story(user_id=user.id, file_data=data, file_mime=file.content_type or "image/jpeg", text_overlay=text_overlay, text_position={"x": text_x, "y": text_y, "scale": text_scale}, created_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    return RedirectResponse(url="/stories", status_code=302)

@app.get("/story/{story_id}/view", response_class=HTMLResponse)
async def view_story(request: Request, story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id, Story.expires_at > datetime.utcnow()).first()
    if not story: raise HTTPException(status_code=404)
    all_stories = db.query(Story).filter(Story.user_id == story.user_id, Story.expires_at > datetime.utcnow()).order_by(Story.created_at.asc()).all()
    return templates.TemplateResponse("view_story.html", {"request": request, "user": get_current_user_optional(request, db), "story": story, "all_stories": all_stories, "story_user": db.query(User).filter(User.id == story.user_id).first()})

# ============ SWIFT ============
@app.get("/swift", response_class=HTMLResponse)
async def swift_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    video_posts = db.query(Post).join(PostFile).filter(PostFile.file_type == "video", Post.is_story == False).order_by(Post.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("swift.html", {"request": request, "user": user, "posts": video_posts, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.get("/api/swift")
async def api_swift(request: Request, offset: int = 0, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"posts": []})
    video_posts = db.query(Post).join(PostFile).filter(PostFile.file_type == "video", Post.is_story == False).order_by(Post.created_at.desc()).offset(offset).limit(10).all()
    return JSONResponse({"posts": [format_post_json(p, user) for p in video_posts]})

# ============ УВЕДОМЛЕНИЯ / ПОИСК / API ============
@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    notifs = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("notifications.html", {"request": request, "user": user, "notifications": notifs, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.post("/notifications/read")
async def mark_read(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return JSONResponse({"status": "ok"})

@app.get("/api/unread_notifications")
async def api_unread(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    return JSONResponse({"count": get_unread_notifications_count(user.id, db) if user else 0})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = Query(None), db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    results = []
    if q:
        for u in db.query(User).filter(User.username.ilike(f"%{q}%")).limit(20).all():
            results.append({"type": "user", "user": u, "is_following": db.query(Follow).filter(Follow.follower_id == user.id, Follow.following_id == u.id).first() is not None})
        for p in db.query(Post).filter((Post.content.ilike(f"%{q}%")) | (Post.content.ilike(f"%#{q}%")), Post.is_story == False).order_by(Post.created_at.desc()).limit(20).all():
            results.append({"type": "post", "post": p})
    return templates.TemplateResponse("search.html", {"request": request, "user": user, "results": results, "query": q or "", "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.get("/search/mention")
async def search_mention(request: Request, q: str = Query(""), db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse([])
    results = []
    for f in db.query(Follow).filter(Follow.follower_id == user.id).all():
        u = db.query(User).filter(User.id == f.following_id).first()
        if u and u.is_online and q.lower() in u.username.lower():
            results.append({"username": u.username, "avatar": f"/file/avatar/{u.id}" if u.avatar_data else ""})
    return JSONResponse(results)

@app.get("/api/feed")
async def api_feed(request: Request, offset: int = 0, filter_type: str = "all", db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"posts": []})
    fids = [f.following_id for f in user.following] + [user.id]
    query = db.query(Post).filter(Post.user_id.in_(fids), Post.is_story == False)
    if filter_type == "photo":
        pids = [p[0] for p in db.query(PostFile.post_id).filter(PostFile.file_type == "image").distinct().all()]
        query = query.filter(Post.id.in_(pids)) if pids else query.filter(Post.id == -1)
    elif filter_type == "video":
        vids = [p[0] for p in db.query(PostFile.post_id).filter(PostFile.file_type == "video").distinct().all()]
        query = query.filter(Post.id.in_(vids)) if vids else query.filter(Post.id == -1)
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(10).all()
    return JSONResponse({"posts": [format_post_json(p, user) for p in posts]})

@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    posts = db.query(Post).filter(Post.is_story == False).order_by(Post.created_at.desc()).limit(30).all()
    viewed = [v.post_id for v in db.query(PostView).filter(PostView.user_id == user.id).all()]
    return templates.TemplateResponse("recommendations.html", {"request": request, "user": user, "posts": posts, "viewed_post_ids": viewed, "unread_notifs": get_unread_notifications_count(user.id, db), "is_new_year": is_new_year_period()})

@app.get("/api/recommendations")
async def api_recommendations(request: Request, offset: int = 0, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"posts": []})
    posts = db.query(Post).filter(Post.is_story == False).order_by(Post.created_at.desc()).offset(offset).limit(10).all()
    viewed = [v.post_id for v in db.query(PostView).filter(PostView.user_id == user.id).all()]
    return JSONResponse({"posts": [format_post_json(p, user, viewed) for p in posts]})

# ============ ОПРОСЫ ============
@app.post("/poll/{poll_id}/vote")
async def vote_poll(request: Request, poll_id: int, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user: return JSONResponse({"error": "Unauthorized"}, status_code=401)
    poll = db.query(PostPoll).filter(PostPoll.id == poll_id).first()
    if not poll: return JSONResponse({"error": "Not found"}, status_code=404)
    data = await request.json()
    opt = str(data.get("option", 0))
    votes = poll.votes or {}
    for k, v in list(votes.items()):
        if str(user.id) in [str(x) for x in v]:
            votes[k] = [x for x in v if str(x) != str(user.id)]
    votes.setdefault(opt, [])
    if str(user.id) not in [str(x) for x in votes[opt]]:
        votes[opt].append(user.id)
    poll.votes = votes
    db.commit()
    uv = None
    for k, v in votes.items():
        if str(user.id) in [str(x) for x in v]:
            uv = int(k); break
    return JSONResponse({"votes": votes, "user_vote": uv})

# ============ АДМИН-ПАНЕЛЬ ============
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse("admin_login.html", {"request": request, "user": user})

@app.post("/admin/login")
async def admin_login(request: Request, db: Session = Depends(get_db), password: str = Form(...)):
    user = get_current_user_optional(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    if password != "adminpanel1":
        return HTMLResponse("<script>alert('Неверный пароль'); window.location.href='/';</script>")
    db.add(AdminLog(admin_user_id=user.id, action="login", details="Вход в админку"))
    db.commit()
    resp = RedirectResponse(url="/admin/dashboard", status_code=302)
    resp.set_cookie(key="admin_user_id", value=str(user.id), max_age=3600, httponly=True)
    return resp

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, sort: str = Query("date"), search: str = Query(""), db: Session = Depends(get_db)):
    aid = request.cookies.get("admin_user_id")
    if not aid: return RedirectResponse(url="/admin", status_code=302)
    admin_user = db.query(User).filter(User.id == int(aid)).first()
    if not admin_user: return RedirectResponse(url="/admin", status_code=302)
    q = db.query(User)
    if search: q = q.filter(User.username.ilike(f"%{search}%"))
    if sort == "date": q = q.order_by(User.created_at.desc())
    elif sort == "alphabet": q = q.order_by(User.username.asc())
    elif sort == "activity": q = q.order_by(User.last_seen.desc())
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "admin_user": admin_user, "users": q.all(), "logs": db.query(AdminLog).order_by(AdminLog.created_at.desc()).limit(50).all(), "sort": sort, "search": search})

@app.post("/admin/user/{user_id}/reset_password")
async def admin_reset(request: Request, user_id: int, db: Session = Depends(get_db), new_password: str = Form(...)):
    aid = request.cookies.get("admin_user_id")
    if not aid: return RedirectResponse(url="/admin")
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        u.real_password = new_password
        db.add(AdminLog(admin_user_id=int(aid), action="reset_password", target_user_id=user_id))
        db.commit()
    return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/user/{user_id}/delete")
async def admin_delete(request: Request, user_id: int, db: Session = Depends(get_db)):
    aid = request.cookies.get("admin_user_id")
    if not aid: return RedirectResponse(url="/admin")
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        db.add(AdminLog(admin_user_id=int(aid), action="delete_user", target_user_id=user_id))
        db.delete(u)
        db.commit()
    return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/user/{user_id}/toggle_block")
async def admin_block(request: Request, user_id: int, db: Session = Depends(get_db)):
    aid = request.cookies.get("admin_user_id")
    if not aid: return RedirectResponse(url="/admin")
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        u.is_blocked = not u.is_blocked
        db.add(AdminLog(admin_user_id=int(aid), action="block" if u.is_blocked else "unblock", target_user_id=user_id))
        db.commit()
    return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/mass_notification")
async def admin_mass(request: Request, db: Session = Depends(get_db), message: str = Form(...)):
    aid = request.cookies.get("admin_user_id")
    if not aid: return RedirectResponse(url="/admin")
    for u in db.query(User).all():
        db.add(Notification(user_id=u.id, from_user_id=int(aid), type="admin_mass", message=message))
    db.add(AdminLog(admin_user_id=int(aid), action="mass_notification", details=message))
    db.commit()
    return RedirectResponse(url="/admin/dashboard")

# ============ ЗАПУСК ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
