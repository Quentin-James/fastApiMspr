from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    author_id: str
    author_name: str
    content: str = Field(min_length=1, max_length=1000)


class Comment(BaseModel):
    id: str
    author_id: str
    author_name: str
    content: str
    created_at: datetime


class PostCreate(BaseModel):
    author_id: str
    author_name: str
    content: str = Field(min_length=1, max_length=2000)
    category: str = Field(default="general")  # "success" | "difficulty" | "general"


class Post(BaseModel):
    id: str
    author_id: str
    author_name: str
    content: str
    category: str
    likes: List[str] = []       # liste des author_id qui ont liké
    likes_count: int = 0
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime


class PostFeedResponse(BaseModel):
    posts: List[Post]
    total: int
    page: int
    page_size: int
