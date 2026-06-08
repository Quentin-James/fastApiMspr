from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.database import get_db
from app.models.social import Comment, CommentCreate, Post, PostCreate, PostFeedResponse

router = APIRouter(prefix="/social", tags=["Social"])


def _serialize_post(doc: dict) -> Post:
    likes: List[str] = doc.get("likes", [])
    return Post(
        id=str(doc["_id"]),
        author_id=doc["author_id"],
        author_name=doc["author_name"],
        content=doc["content"],
        category=doc.get("category", "general"),
        likes=likes,
        likes_count=len(likes),
        comments_count=doc.get("comments_count", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _serialize_comment(doc: dict) -> Comment:
    return Comment(
        id=str(doc["_id"]),
        author_id=doc["author_id"],
        author_name=doc["author_name"],
        content=doc["content"],
        created_at=doc["created_at"],
    )


# ─── Posts ───────────────────────────────────────────────────────────────────

@router.post("/posts", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreate) -> Post:
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "author_id": payload.author_id,
        "author_name": payload.author_name,
        "content": payload.content,
        "category": payload.category,
        "likes": [],
        "comments_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["posts"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_post(doc)


@router.get("/posts", response_model=PostFeedResponse)
async def list_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
) -> PostFeedResponse:
    db = get_db()
    query: dict = {}
    if category:
        query["category"] = category

    total = await db["posts"].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db["posts"].find(query).sort("created_at", -1).skip(skip).limit(page_size)
    posts = [_serialize_post(doc) async for doc in cursor]

    return PostFeedResponse(posts=posts, total=total, page=page, page_size=page_size)


@router.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str) -> Post:
    db = get_db()
    doc = await db["posts"].find_one({"_id": ObjectId(post_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Post introuvable.")
    return _serialize_post(doc)


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, author_id: str = Query(...)) -> Response:
    db = get_db()
    doc = await db["posts"].find_one({"_id": ObjectId(post_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Post introuvable.")
    if doc["author_id"] != author_id:
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    await db["posts"].delete_one({"_id": ObjectId(post_id)})
    await db["comments"].delete_many({"post_id": post_id})
    return Response(status_code=204)


# ─── Likes ───────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/like", response_model=Post)
async def toggle_like(post_id: str, user_id: str = Query(...)) -> Post:
    db = get_db()
    doc = await db["posts"].find_one({"_id": ObjectId(post_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Post introuvable.")

    likes: list = doc.get("likes", [])
    if user_id in likes:
        likes.remove(user_id)
    else:
        likes.append(user_id)

    now = datetime.now(timezone.utc)
    await db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"likes": likes, "updated_at": now}},
    )
    doc["likes"] = likes
    doc["updated_at"] = now
    return _serialize_post(doc)


# ─── Comments ────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def add_comment(post_id: str, payload: CommentCreate) -> Comment:
    db = get_db()
    if not await db["posts"].find_one({"_id": ObjectId(post_id)}):
        raise HTTPException(status_code=404, detail="Post introuvable.")

    now = datetime.now(timezone.utc)
    doc = {
        "post_id": post_id,
        "author_id": payload.author_id,
        "author_name": payload.author_name,
        "content": payload.content,
        "created_at": now,
    }
    result = await db["comments"].insert_one(doc)
    doc["_id"] = result.inserted_id

    await db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"comments_count": 1}, "$set": {"updated_at": now}},
    )
    return _serialize_comment(doc)


@router.get("/posts/{post_id}/comments", response_model=List[Comment])
async def list_comments(
    post_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> List[Comment]:
    db = get_db()
    skip = (page - 1) * page_size
    cursor = db["comments"].find({"post_id": post_id}).sort("created_at", 1).skip(skip).limit(page_size)
    return [_serialize_comment(doc) async for doc in cursor]


@router.delete("/posts/{post_id}/comments/{comment_id}")
async def delete_comment(post_id: str, comment_id: str, author_id: str = Query(...)) -> Response:
    db = get_db()
    doc = await db["comments"].find_one({"_id": ObjectId(comment_id), "post_id": post_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Commentaire introuvable.")
    if doc["author_id"] != author_id:
        raise HTTPException(status_code=403, detail="Action non autorisée.")
    await db["comments"].delete_one({"_id": ObjectId(comment_id)})
    await db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"comments_count": -1}},
    )
    return Response(status_code=204)
