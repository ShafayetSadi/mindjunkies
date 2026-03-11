# MindJunkies — System Architecture Overview

## 1. Project Structure

```
mindjunkies/
├── config/            # Shared base config (BaseModel, JitsiJWT builder)
├── project/
│   └── settings/      # base.py, development.py, production.py, test.py
├── mindjunkies/       # All Django apps
│   ├── accounts/      # User, Profile, auth
│   ├── courses/       # Course catalog, modules, ratings, enrollments
│   ├── lecture/       # Lecture content (video, PDF), progress tracking
│   ├── payments/      # SSLCommerz integration, teacher balance
│   ├── live_classes/  # Jitsi-based video conferencing
│   ├── forums/        # Course discussion boards (Elasticsearch)
│   ├── dashboard/     # Teacher verification & teacher portal
│   └── home/          # Homepage, global search
├── docs/              # Architecture, SRS, guides
└── pyproject.toml
```

---

## 2. Django Apps & Responsibilities

| App | Responsibility |
|---|---|
| **accounts** | Custom `User` (UUID PK, `is_teacher` flag), `Profile`, Google OAuth via allauth |
| **courses** | `Course`, `Module`, `Enrollment`, `Rating`, `CourseToken` (approval workflow), hierarchical `CourseCategory` |
| **lecture** | `Lecture`, `LectureVideo` (Cloudinary HLS), `LecturePDF`, `LectureCompletion`, progression tracking |
| **payments** | SSLCommerz checkout, `Transaction`, teacher `Balance`, `BalanceHistory` |
| **live_classes** | `LiveClass` model with Jitsi-as-a-Service JWT tokens (8x8.vc) |
| **forums** | `ForumTopic`, `ForumComment`, `Reply`, nested likes, Elasticsearch indexing |
| **dashboard** | `TeacherVerification`, `Certificate`, teacher portal views |
| **home** | Homepage with Redis-cached popular/new courses, title search |

---

## 3. Database Models & Relationships

```
User (accounts.User — UUID PK, is_teacher)
 ├── Profile (1:1)
 ├── TeacherVerification (1:1)
 ├── Balance (1:1)
 ├── Course [teacher FK] ─── Enrollment [student FK] ─── Transaction (1:1 enrollment)
 │       ├── Module ──────── Lecture ──── LectureVideo (Cloudinary)
 │       │                            └── LecturePDF
 │       ├── Rating [student FK]       └── LectureCompletion [user FK]
 │       ├── LiveClass [teacher FK]
 │       └── ForumTopic [course FK]
 │               └── ForumComment
 │                       └── Reply (self-referential)
 └── BalanceHistory [user FK]
```

**Key constraints:**
- `Enrollment`: unique_together `(course, student)`
- `Rating`: unique_together `(student, course)` — one rating per user
- `Module.order`: unique per course; `Lecture.order`: unique per module
- `Transaction`: unique_together `(user, course)`

---

## 4. Request Flow

```
URL → View → (Business Logic) → Models/DB
                   │
                   ├─ Cache (Redis) — popular/new courses
                   ├─ Cloudinary — media uploads
                   ├─ SSLCommerz — payment redirect
                   ├─ Elasticsearch — forum search
                   └─ Signals → DB side-effects
```

**Example — Paid Course Enrollment:**
```
GET /payment/{slug}/checkout/
  → CheckoutView
    → create Enrollment(status=pending)
    → init SSLCommerz session
    → redirect to gateway

POST /payment/{slug}/success/   [SSLCommerz webhook]
  → CheckoutSuccessView (CSRF-exempt)
    → create Transaction
    → update teacher Balance + BalanceHistory
    → set Enrollment(status=active)
```

**Example — Lecture Progress:**
```
POST /courses/{slug}/lecture/{id}/complete/
  → MarkLectureCompleteView
    → create LectureCompletion
    → signal: update_module_progression_on_save
      → recalculate (completed/total)*100
      → save Enrollment.progression
```

---

## 5. Authentication & Permissions

**Backends:** `ModelBackend` + `allauth.AuthenticationBackend` + Google OAuth2

**Access control layers:**

| Mixin | What it enforces |
|---|---|
| `LoginRequiredMixin` | Must be authenticated |
| `VerifiedTeacherRequiredMixin` | `is_teacher=True` AND `TeacherVerification.verified=True` |
| Inline checks in views | Enrollment check for students; `course.teacher == request.user` for teachers |

**Teacher workflow:**  
Apply → `TeacherVerification` created → Admin approves → `User.is_teacher=True` → full dashboard access

**Course publishing workflow:**  
Create course → `CourseToken(status=pending)` → Admin approves → token `status=approved` → can upload content & run live classes

**Email verification:** Mandatory (configured in allauth settings)

---

## 6. Background Jobs / Async Tasks

No Celery. All "background" work is **synchronous via Django signals:**

| Signal | Trigger | Effect |
|---|---|---|
| `post_save(LectureCompletion)` | Lecture marked complete | Recalculates `Enrollment.progression` |
| `post_delete(LectureCompletion)` | Completion removed | Recalculates progression |
| `post_delete(Lecture)` | Lecture deleted | Recalculates progression for all enrolled users |
| `post_save(Rating)` | Rating saved | Updates `Course.total_rating` |
| `course_updated` (custom) | Course created | Clears Redis cache keys `popular_courses`, `new_courses` |
| `post_save(User)` | User created | Auto-creates `Profile` |

---

## 7. External Integrations

| Service | Library | Used For |
|---|---|---|
| **SSLCommerz** | `sslcommerz-lib` | Bangladeshi payment gateway |
| **Cloudinary** | `cloudinary` | User avatars, course images, lecture videos (HLS) |
| **DigitalOcean Spaces** | `boto3` + `django-storages` | Static/media file hosting (S3-compatible, `blr1`) |
| **Redis** | `django-redis` | Caching popular/new courses (5-min TTL) |
| **Elasticsearch** | `django-elasticsearch-dsl` | Forum topic full-text search |
| **Jitsi 8x8.vc** | Custom `JaaSJwtBuilder` (RS256) | Live video conferencing, JWT-gated teacher rooms |
| **Resend** | `resend` | Transactional email (verification, password reset) |
| **Google OAuth2** | `django-allauth` | Social login |

---

## 8. Key Business Logic

**Course economics:**
- Free courses: instant `Enrollment(status=active)`
- Paid courses: SSLCommerz flow; 100% of `course_price` credited to teacher balance

**Content gating:** Lectures are only accessible to enrolled students OR the course teacher. `CourseToken` must be `approved` before teacher can upload content or create live classes.

**Progression:** Purely percentage-based (`completed_lectures / total_lectures * 100`), stored on `Enrollment.progression`.

**Forum search:** Elasticsearch-backed, searches `title` field of `ForumTopic` with `match` query — per-course scoped.

**Live classes:** Jitsi room URL = `8x8.vc/{APP_ID}/{meeting_id}`. Teachers get JWT with moderator rights (from `private.pem`); students join unauthenticated.

---

## 9. Potential Architectural Problems

### Critical
1. **No Celery / async workers.** Signal-based progression recalculation runs synchronously on every lecture completion. At scale (many students, many lectures), `update_all_progressions_on_lecture_delete` runs N queries blocking the request thread.

2. **CSRF-exempt payment webhooks trust POST body blindly.** `CheckoutSuccessView` reads `value_a`/`value_b` from SSLCommerz POST to identify `user_id` and `course_slug` with no additional HMAC validation beyond SSLCommerz's own `verify_sign`. A forged POST could fraudulently activate enrollments.

3. **Private key on disk.** `private.pem` is read from the filesystem inside the `lecture/` directory — risky in containerized/cloud deployments.

### Moderate
4. **No soft-delete.** `BaseModel` has a `deleted_at` field but no `SoftDeleteManager` or queryset filter — it exists but is never used.

5. **Cache invalidation is partial.** Only `CreateCourseView` fires `course_updated`. Course updates, deletions, and enrollment changes don't invalidate the cache, so stale data can persist for up to 5 minutes.

6. **`ForumComment.content` is `CharField(150)`** — very short for a discussion platform. Same for `ForumTopic.content`.

7. **Hardcoded user info in payment requests** — phone, address, city, country are hardcoded strings in `CheckoutView` instead of pulled from `Profile`.

8. **`PaymentGateway` model stores `store_pass` in plaintext** in the database instead of using environment variables.

### Minor
9. **No rate limiting on course rating, forum, or lecture completion views** — susceptible to spam.
10. **Elasticsearch is only used for forum search** — course search falls back to basic `icontains`, which won't scale.
11. **`silk` profiling middleware is always active** — should be disabled or gated behind `DEBUG` in production.

---

**Stack summary:** Django 5.1 · PostgreSQL · Redis · Cloudinary · DigitalOcean Spaces · SSLCommerz · Jitsi 8x8 · Elasticsearch · Resend email · Tailwind CSS · HTMX

---
