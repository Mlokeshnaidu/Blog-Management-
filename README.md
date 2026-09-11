# Blog Management API

A mini blogging system backend API built using **FastAPI**, **SQLite** with **SQLAlchemy ORM**, and **JWT Authentication**.

---

## 🎯 Features

- **User Authentication**: Register & Login with JWT bearer tokens (`/auth/register`, `/auth/login`, `/auth/me`).
- **Post Management (CRUD)**:
  - Create posts (`POST /posts`)
  - List all posts (`GET /posts`) with optional search query (`?q=...`)
  - View single post (`GET /posts/{id}`)
  - View personal posts (`GET /posts/mine`)
  - Update post (`PUT /posts/{id}`) — *Only post author*
  - Delete post (`DELETE /posts/{id}`) — *Only post author*
- **Comments**:
  - Add comments to any post (`POST /posts/{id}/comments`)
  - View comments on a post (`GET /posts/{id}/comments`)
  - Delete comment (`DELETE /posts/{id}/comments/{comment_id}`) — *Comment author or Post author*
- **Likes**:
  - Like/Unlike post toggle (`POST /posts/{id}/like`)
  - Delete like (`DELETE /posts/{id}/like`)
- **Background Email Notifications**:
  - Automatically triggers email notifications to post authors on new comments and likes.
- **Interactive Documentation**: Interactive Swagger UI at `http://127.0.0.1:8000/docs` and ReDoc at `http://127.0.0.1:8000/redoc`.

---

## 🗄️ Database Models (SQLite & SQLAlchemy ORM)

| Model | Fields |
|---|---|
| **User** | `id`, `username`, `email`, `password` (hashed with bcrypt) |
| **Post** | `id`, `title`, `content`, `author_id`, `created_at` |
| **Comment** | `id`, `post_id`, `user_id`, `text`, `created_at` |
| **Like** | `id`, `post_id`, `user_id` |

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the API Server
```bash
uvicorn main:app --reload
```
or
```bash
python main.py
```

The API will start at: `http://127.0.0.1:8000`

### 3. Open Swagger UI
Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to explore and test all endpoints.

---

## 🧪 Running Tests
To run the automated unit tests:
```bash
python test_api.py
```
