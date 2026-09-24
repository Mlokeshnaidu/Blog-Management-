"""
AI Support Service — Mocked FAQ-based assistant.

Matches user messages against predefined FAQ entries using keyword scoring.
Replace the `get_ai_response` function body with a real AI API call
(OpenAI / HuggingFace / local LLM) when ready.
"""

from typing import List, Tuple

# ── Predefined FAQ knowledge base ─────────────────────────────────────────────
# Each entry: (keywords list, answer)
FAQ_ENTRIES: List[Tuple[List[str], str]] = [
    # ── Creating Posts ───────────────────────────────────────────────
    (
        ["create", "post", "new", "write", "add", "blog", "publish"],
        "To create a new blog post:\n"
        "1. Make sure you are logged in and have a valid JWT token.\n"
        "2. Send a POST request to `/posts/` with your title, content, and optionally an image.\n"
        "3. Your subscription plan determines how many posts and images you can upload.\n"
        "4. Once created, your post will be visible to all users."
    ),
    # ── Editing Posts ────────────────────────────────────────────────
    (
        ["edit", "update", "modify", "change", "post"],
        "To edit an existing post:\n"
        "1. Send a PUT request to `/posts/{post_id}` with the updated title, content, or image.\n"
        "2. Only the author of the post can edit it.\n"
        "3. You can update the title, content, or replace the image."
    ),
    # ── Deleting Posts ───────────────────────────────────────────────
    (
        ["delete", "remove", "post"],
        "To delete a post:\n"
        "1. Send a DELETE request to `/posts/{post_id}`.\n"
        "2. Only the author of the post can delete it.\n"
        "3. Deleting a post also removes all associated comments and likes."
    ),
    # ── Subscriptions ────────────────────────────────────────────────
    (
        ["subscription", "subscribe", "plan", "plans", "tier", "upgrade", "downgrade"],
        "Our platform offers three subscription plans:\n"
        "• **Basic** (Free) — 1 post, 1 image per post, 5 likes & comments.\n"
        "• **Premium** ($9.99/month) — 2 posts, 2 images per post, 20 likes & comments.\n"
        "• **Pro** ($29.99/month) — Unlimited posts, images, likes & comments.\n\n"
        "To subscribe, send a POST request to `/subscriptions/subscribe` with the plan ID.\n"
        "View available plans at GET `/subscriptions/plans`."
    ),
    # ── Billing ──────────────────────────────────────────────────────
    (
        ["billing", "bill", "invoice", "payment", "pay", "charge", "price", "cost", "receipt"],
        "For billing inquiries:\n"
        "• View your billing history at GET `/subscriptions/billing-history`.\n"
        "• Each subscription change generates an invoice with transaction details.\n"
        "• Invoices include plan name, amount, date, and payment status.\n"
        "• The Basic plan is free; Premium is $9.99/month and Pro is $29.99/month."
    ),
    # ── Profile Management ───────────────────────────────────────────
    (
        ["profile", "account", "username", "email", "password", "settings", "user"],
        "To manage your profile:\n"
        "• Your account details are tied to your username and email.\n"
        "• To register, send a POST request to `/auth/register` with username, email, and password.\n"
        "• To log in, send a POST request to `/auth/login` with your credentials to receive a JWT token.\n"
        "• Use the JWT token in the Authorization header for all authenticated requests."
    ),
    # ── Dashboard & Analytics ────────────────────────────────────────
    (
        ["dashboard", "analytics", "stats", "statistics", "chart", "graph", "views", "metrics"],
        "Your dashboard provides personalized analytics:\n"
        "• **Total Posts** — Number of posts you've created.\n"
        "• **Total Comments** — Comments received on your posts.\n"
        "• **Likes Received** — Total likes across all your posts.\n"
        "• **Post Views** — How many times your posts have been viewed.\n"
        "• **Bar Chart** — Likes & comments distribution per post.\n"
        "• **Line Chart** — Post creation activity over time.\n\n"
        "Access your dashboard at GET `/user/dashboard/` (requires JWT token) or view the visual dashboard at `/user/dashboard/view`."
    ),
    # ── Comments ─────────────────────────────────────────────────────
    (
        ["comment", "comments", "reply", "respond"],
        "To interact with comments:\n"
        "• Add a comment: POST `/posts/{post_id}/comments/` with your comment text.\n"
        "• View comments: GET `/posts/{post_id}/comments/`.\n"
        "• Delete your comment: DELETE `/posts/{post_id}/comments/{comment_id}`.\n"
        "• Your subscription plan limits how many comments you can make."
    ),
    # ── Likes ────────────────────────────────────────────────────────
    (
        ["like", "likes", "unlike", "heart", "favorite"],
        "To like or unlike a post:\n"
        "• Toggle a like: POST `/posts/{post_id}/like`.\n"
        "• If you haven't liked the post, it adds a like; if you already liked it, it removes the like.\n"
        "• Your subscription plan limits the total number of likes you can give."
    ),
    # ── Notifications ────────────────────────────────────────────────
    (
        ["notification", "notifications", "alert", "alerts", "bell"],
        "Notifications keep you updated on activity:\n"
        "• View all notifications: GET `/notifications/`.\n"
        "• Check unread count: GET `/notifications/unread-count`.\n"
        "• Mark one as read: PUT `/notifications/{id}/read`.\n"
        "• Mark all as read: PUT `/notifications/read-all`.\n"
        "• You receive notifications when someone likes or comments on your posts."
    ),
    # ── Authentication / Login ───────────────────────────────────────
    (
        ["login", "signin", "sign in", "authenticate", "token", "jwt", "auth"],
        "To authenticate with the platform:\n"
        "1. **Register**: POST `/auth/register` with `username`, `email`, and `password`.\n"
        "2. **Login**: POST `/auth/login` with `username` and `password`.\n"
        "3. You'll receive a JWT access token in the response.\n"
        "4. Include the token in the `Authorization: Bearer <token>` header for protected endpoints."
    ),
    # ── API Documentation ────────────────────────────────────────────
    (
        ["api", "docs", "documentation", "swagger", "endpoints", "routes"],
        "You can explore the full API documentation:\n"
        "• **Swagger UI**: Visit `/docs` in your browser for interactive API docs.\n"
        "• All endpoints are organized by tags: Auth, Posts, Comments, Likes, Subscriptions, Dashboard, and Notifications.\n"
        "• Each endpoint shows required parameters, request bodies, and response schemas."
    ),
    # ── Greeting ─────────────────────────────────────────────────────
    (
        ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"],
        "Hello! Welcome to the Blog Management Platform support chat!\n"
        "I'm here to help you with any questions about:\n"
        "• Creating, editing, or deleting posts\n"
        "• Subscriptions and billing\n"
        "• Profile management\n"
        "• Dashboard analytics\n"
        "• And more!\n\n"
        "Just type your question and I'll do my best to assist you."
    ),
    # ── Help ──────────────────────────────────────────────────────────
    (
        ["help", "support", "assist", "how", "what can"],
        "I can help you with the following topics:\n"
        "• **Posts** — Create, edit, delete blog posts\n"
        "• **Comments** — Add and manage comments\n"
        "• **Likes** — Like and unlike posts\n"
        "• **Dashboard** — View your analytics and stats\n"
        "• **Subscriptions & Billing** — Plans, payments, invoices\n"
        "• **Notifications** — Stay updated on activity\n"
        "• **Profile & Auth** — Registration, login, account management\n"
        "• **API Docs** — Explore available endpoints\n\n"
        "Just ask me about any of these topics!"
    ),
    # ── Thank you ────────────────────────────────────────────────────
    (
        ["thank", "thanks", "thx", "appreciate"],
        "You're welcome! I'm glad I could help.\n"
        "If you have any more questions, feel free to ask anytime!"
    ),
]

# ── Default fallback response ──────────────────────────────────────────────────
DEFAULT_RESPONSE = (
    "I'm sorry, I didn't quite understand your question.\n\n"
    "Here are some topics I can help with:\n"
    "• How to create, edit, or delete posts\n"
    "• Subscription plans and billing\n"
    "• Profile and account management\n"
    "• Dashboard analytics and charts\n"
    "• Comments and likes\n"
    "• Notifications\n"
    "• API documentation\n\n"
    "Try rephrasing your question or type **help** for a full list of topics!"
)


def get_ai_response(user_message: str) -> str:
    """
    Match the user message against FAQ entries using keyword scoring.
    Returns the best-matching FAQ answer, or a fallback response.

    Replace this function body with a real AI API call when ready:
        import openai
        response = openai.ChatCompletion.create(...)
        return response.choices[0].message.content
    """
    message_lower = user_message.lower().strip()

    # Score each FAQ entry by counting keyword matches
    best_score = 0
    best_answer = DEFAULT_RESPONSE

    for keywords, answer in FAQ_ENTRIES:
        score = 0
        for keyword in keywords:
            if keyword in message_lower:
                score += 1
        # Require at least 1 keyword match, prefer higher scores
        if score > best_score:
            best_score = score
            best_answer = answer

    return best_answer
