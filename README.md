# Blog Management API

A full-featured blogging system API built with **FastAPI**, **SQLite**, **SQLAlchemy ORM**, **JWT authentication**, and **Auth0 social login (Google & Facebook)**.

## Features

### 1. Core Blog Management (Task 1)
- **Authentication**: JWT-based user registration and login (/auth/register, /auth/login)
- **Social Login**: Auth0-powered Google & Facebook login (/auth/login/google, /auth/login/facebook)
- **Signup & Login UI**: Beautiful dark-themed login page at /login with social buttons
- **Posts CRUD**: Create, read, update, and delete blog posts with ownership checks
- **Comments**: Add, view, and delete comments on posts
- **Likes**: Like and unlike posts (toggle)
- **/posts/mine**: View only your own posts
- **Swagger UI**: Interactive API documentation at /docs

### 2. Image Uploads, Pagination & Search (Task 2)
- **Image Uploads**: Upload cover images when creating or editing posts (UploadFile)
- **Pagination**: GET /posts/?page=1&limit=10 with total count and total pages
- **Search**: Filter posts by title or content using ?search=keyword
- Images saved under /media/posts/ and served via static file mount

### 3. Subscription & Billing (Task 3)
- **Three Subscription Plans**: Basic, Premium, Pro with different feature limits
- **Access Control**: Limits on posts, likes, comments, and images per plan
- **Friendly Validation**: "You've reached your plan limit. Kindly upgrade your plan to continue."
- **PDF Invoices**: Generated via ReportLab, saved under /media/invoices/
- **Billing History**: Full transaction history with invoice download

### 4. Email Notifications (Task 4)
- **Async Email on Comment**: Notifies post author when someone comments
- **Async Email on Like**: Notifies post author when someone likes their post
- **Email Content**: Includes post title, user name, activity type, and timestamp
- **Implementation**: Uses BackgroundTasks for non-blocking email delivery
- **Modular Architecture**: services/email_service.py + services/notification_service.py

### 5. User Dashboard (Task 5)
- **Dashboard API**: GET /user/dashboard/ returns personalised analytics
- **Metrics Returned**:
  - Total posts created
  - Total comments made
  - Total likes received on all posts
  - Total post views (view_count tracking)
  - Per-post likes/comments distribution (for bar/pie charts)
  - Post activity over time (for line charts)
- **JWT Protected**: Each user can only view their own data
- **Chart-Ready**: JSON structure designed for Chart.js / Plotly integration

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Authentication | JWT (python-jose) |
| Password Hashing | bcrypt (passlib) |
| PDF Generation | ReportLab |
| Email | smtplib (async via BackgroundTasks) |
| Image Handling | FastAPI UploadFile |

## Project Structure

`
Task Blog Management/
+-- main.py                         # Entry point
+-- requirements.txt                # Python dependencies
+-- .env                            # Environment variables (not committed)
+-- .gitignore
+-- .pre-commit-config.yaml         # Pre-commit hooks (detect-secrets)
+-- .secrets.baseline               # Secrets baseline file
+-- blog.db                         # SQLite database
+-- media/                          # Uploaded images & invoices
    +-- posts/
    +-- invoices/
+-- fastapi_app/
    +-- main.py                     # FastAPI app factory & router registration
    +-- core/
        +-- config.py               # App settings / env config
        +-- database.py             # SQLAlchemy engine & session
        +-- security.py             # JWT creation, password hashing, auth deps
        +-- storage.py              # Image upload/delete helpers
        +-- subscription_service.py # Plan limit checks & subscription logic
        +-- invoices.py             # ReportLab PDF invoice generation
        +-- notifications.py        # Notification helpers
    +-- models/
        +-- user.py                 # User model
        +-- post.py                 # Post model (with view_count)
        +-- comment.py              # Comment model
        +-- like.py                 # Like model
        +-- subscription.py         # SubscriptionPlan & BillingHistory models
    +-- schemas/
        +-- user.py                 # User Pydantic schemas
        +-- post.py                 # Post schemas (incl. pagination)
        +-- comment.py              # Comment schemas
        +-- like.py                 # Like schemas
        +-- subscription.py         # Subscription & billing schemas
        +-- dashboard.py            # Dashboard response schemas
    +-- routes/
        +-- auth.py                 # /auth/register, /auth/login, /auth/me
        +-- posts.py                # /posts CRUD with image upload, pagination, search
        +-- comments.py             # /posts/{id}/comments
        +-- likes.py                # /posts/{id}/like
        +-- subscriptions.py        # /subscriptions/*, /billing/*
        +-- admin.py                # Admin panel routes
        +-- dashboard.py            # /user/dashboard/ endpoint
    +-- services/
        +-- email_service.py        # SMTP email sender
        +-- notification_service.py # Comment/like notification logic
        +-- dashboard_service.py    # Dashboard data aggregation
`

## Quick Start

`ash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload

# Open Swagger UI
# http://127.0.0.1:8000/docs
`

## API Endpoints Summary

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /auth/register | Register new user | No |
| POST | /auth/signup | Alias for register | No |
| POST | /auth/login | Login & get JWT | No |
| GET | /auth/login/google | Redirect to Google Login (Auth0) | No |
| GET | /auth/login/facebook | Redirect to Facebook Login (Auth0) | No |
| GET | /auth/callback | Auth0 callback handler | No |
| GET | /auth/logout | Auth0 logout | No |
| GET | /auth/me | Get current user profile | Yes |
| GET | /login | Login / Signup UI page | No |
| GET | /posts | List posts (paginated, searchable) | No |
| GET | /posts/mine | List my posts | Yes |
| GET | /posts/{id} | Get single post | No |
| POST | /posts/create | Create post (with image) | Yes |
| PUT | /posts/{id}/update | Update post | Yes (owner) |
| DELETE | /posts/{id} | Delete post | Yes (owner) |
| GET | /posts/{id}/comments | List comments | No |
| POST | /posts/{id}/comments | Add comment | Yes |
| DELETE | /posts/{id}/comments/{cid} | Delete comment | Yes |
| POST | /posts/{id}/like | Toggle like | Yes |
| DELETE | /posts/{id}/like | Unlike | Yes |
| GET | /subscriptions/plans | List plans | No |
| GET | /subscriptions/my-plan | Current plan & usage | Yes |
| POST | /subscriptions/subscribe | Subscribe/upgrade | Yes |
| GET | /billing/history | Billing history | Yes |
| GET | /billing/invoices/{id}/download | Download PDF invoice | Yes |
| GET | /user/dashboard/ | User dashboard analytics | Yes |


