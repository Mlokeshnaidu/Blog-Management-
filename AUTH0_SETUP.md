# Auth0 Social Login Integration — Setup & Documentation

## Overview

This document covers the **Auth0 Signup & Authentication** integration added to the Blog Management Platform. Users can now:
- **Sign up / Login** with traditional email and password.
- **Continue with Google** — redirects to Auth0 → Google OAuth2.
- **Continue with Facebook** — redirects to Auth0 → Facebook Login.

---

## Architecture

```
┌───────────────┐       ┌────────────────┐       ┌──────────┐
│   Login UI    │──────►│  FastAPI Auth   │──────►│  Auth0   │
│  /login page  │◄──────│  /auth/* routes │◄──────│  Tenant  │
└───────────────┘       └────────────────┘       └──────────┘
                              │
                              ▼
                        ┌──────────┐
                        │  SQLite  │
                        │  blog.db │
                        └──────────┘
```

### Flow: Social Login
1. User clicks **"Continue with Google"** or **"Continue with Facebook"**.
2. Browser redirects to `/auth/login/google` (or `/auth/login/facebook`).
3. FastAPI builds the Auth0 `/authorize` URL and redirects the user to Auth0.
4. User authenticates with Google/Facebook on the Auth0 hosted login page.
5. Auth0 redirects back to `/auth/callback?code=...`.
6. FastAPI exchanges the `code` for tokens via Auth0's `/oauth/token` endpoint.
7. FastAPI fetches user info from Auth0's `/userinfo` endpoint.
8. If the user doesn't exist locally, a new `User` record is created (with `auth_provider` set to `google-oauth2` or `facebook`).
9. A local **JWT** is issued, and the user is redirected to `/login?token=...`.
10. The login page JavaScript picks up the token from the URL, stores it in `localStorage`, and redirects to the dashboard.

### Flow: Email/Password
1. User fills in the signup/login form on `/login`.
2. JavaScript sends a `POST` to `/auth/signup` or `/auth/login`.
3. FastAPI validates credentials, issues a JWT, and returns it in the response.
4. JavaScript stores the token and redirects.

---

## Auth0 Setup Instructions

### 1. Create an Auth0 Account
- Go to [https://auth0.com](https://auth0.com) and sign up.
- Create a new **tenant** (e.g., `my-blog-app`).

### 2. Create an Application
- In the Auth0 Dashboard, go to **Applications → Applications → Create Application**.
- Choose **Regular Web Application**.
- Note down the **Domain**, **Client ID**, and **Client Secret**.

### 3. Configure Callback URLs
In your Auth0 Application Settings:

| Setting | Value |
|---|---|
| **Allowed Callback URLs** | `http://localhost:8000/auth/callback` |
| **Allowed Logout URLs** | `http://localhost:8000/login` |
| **Allowed Web Origins** | `http://localhost:8000` |

> For production, replace `localhost:8000` with your actual domain.

### 4. Enable Social Connections
- Go to **Authentication → Social** in the Auth0 Dashboard.
- Enable **Google** and **Facebook** connections.
- For **Google**: You'll need to create OAuth2 credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and paste the Client ID and Secret into Auth0.
- For **Facebook**: You'll need to create an app in [Facebook Developers](https://developers.facebook.com/) and paste the App ID and Secret into Auth0.

### 5. Update Your `.env` File
```env
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_CALLBACK_URL=http://localhost:8000/auth/callback
AUTH0_AUDIENCE=
AUTH0_LOGOUT_REDIRECT=http://localhost:8000/login
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register with username, email, password |
| `POST` | `/auth/signup` | Alias for `/auth/register` |
| `POST` | `/auth/login` | Login with username/email + password |
| `GET`  | `/auth/login/google` | Redirect to Auth0 → Google Login |
| `GET`  | `/auth/login/facebook` | Redirect to Auth0 → Facebook Login |
| `GET`  | `/auth/callback` | Auth0 callback handler |
| `GET`  | `/auth/logout` | Logout (clears Auth0 session) |
| `GET`  | `/auth/me` | Get current user profile (requires JWT) |

---

## How to Run & Test Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy the Auth0 values into your `.env` file (see section above).

### 3. Start the Server
```bash
uvicorn main:app --reload
```

### 4. Open the Login Page
Navigate to: [http://localhost:8000/login](http://localhost:8000/login)

### 5. Test Email/Password
- Click **"Create Account"** tab.
- Fill in username, email, and password.
- Submit. You should get a JWT token and be redirected.

### 6. Test Social Login
- Click **"Continue with Google"** or **"Continue with Facebook"**.
- You'll be redirected to Auth0's hosted login page.
- After authenticating, you'll be redirected back with a JWT.

### 7. Verify via API
```bash
# Check your user profile
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/auth/me
```

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Username already exists | `400 — Username already registered` |
| Email already exists | `400 — Email already registered` |
| Invalid login credentials | `401 — Invalid credentials` |
| Missing Auth0 callback code | Redirect to `/login?error=Missing+authorization+code` |
| Auth0 token exchange failure | Redirect to `/login?error=Token+exchange+failed` |
| User info fetch failure | Redirect to `/login?error=Failed+to+fetch+user+info` |
| Email not provided by provider | Redirect to `/login?error=Email+not+provided+by+provider` |
| Invalid JWT token | `401 — Invalid token` |
| User not found | `401 — User not found` |

---

## Database Changes

The `users` table now includes:

| Column | Type | Description |
|--------|------|-------------|
| `auth_provider` | `String(50)` | Login provider: `local`, `google-oauth2`, `facebook` |
| `auth_provider_id` | `String(255)` | Unique ID from Auth0 (e.g., `google-oauth2\|123456`) |
| `password` | `String(255)` | Now **nullable** — social users don't have a password |

---

## Files Modified/Created

| File | Action |
|------|--------|
| `fastapi_app/models/user.py` | Modified — added `auth_provider`, `auth_provider_id`, made `password` nullable |
| `fastapi_app/schemas/user.py` | Modified — added `auth_provider` to `UserOut` |
| `fastapi_app/routes/auth.py` | Rewritten — added signup, social login, Auth0 callback, logout, `/me` |
| `fastapi_app/core/config.py` | Modified — added Auth0 settings |
| `fastapi_app/main.py` | Modified — serves `/login` page, bumped to v5.0.0 |
| `fastapi_app/templates/login.html` | **Created** — Login/Signup UI with social buttons |
| `.env` | Modified — added Auth0 placeholder variables |
| `requirements.txt` | Modified — added `authlib`, `itsdangerous`, `jinja2` |
| `AUTH0_SETUP.md` | **Created** — this documentation file |
