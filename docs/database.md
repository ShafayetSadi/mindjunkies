# MindJunkies — Database Schema

## Foundational Layer

### `BaseModel` *(abstract — `config/models.py`)*

Every app model (except a few) inherits from this. It provides:

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Integer PK for DB performance |
| `uuid` | `UUIDField` | Unique, non-editable — safe for external exposure in URLs |
| `created_at` | `DateTimeField` | Auto-set on insert |
| `updated_at` | `DateTimeField` | Auto-updated on every save |
| `deleted_at` | `DateTimeField` | Nullable — **soft-delete stub, never enforced** |

Default ordering: `[-created_at, -updated_at]` — newest first everywhere.

> **Important:** `id` (integer) is used for internal DB joins. `uuid` is the public-safe identifier shown in URLs. The two coexist on every model that extends `BaseModel`.

---

## Accounts Domain

### `User` *(accounts/models.py)*

Extends Django's `AbstractUser`. The central entity everything else references.

| Field | Type | Notes |
|---|---|---|
| `uuid` | `UUIDField` | **Primary key** — replaces the default integer PK |
| `username` | `CharField` | Inherited from `AbstractUser` |
| `email` | `EmailField` | Required (in `REQUIRED_FIELDS`) |
| `first_name` / `last_name` | `CharField` | Required |
| `is_teacher` | `BooleanField` | Default `False` — gates all teacher functionality |
| `password`, `is_active`, etc. | — | Standard Django auth fields |

**Computed methods (no DB columns):**

| Method | Logic |
|---|---|
| `name` | `f"{first_name} {last_name}"` |
| `get_instructor_rating()` | Average of `total_rating` across all courses taught, divided by total review count |
| `get_number_of_students()` | `Enrollment` rows where `course__teacher=self` and `status=active`, distinct by student |
| `get_number_of_courses()` | Count of `courses_taught` relation |
| `get_number_of_reviews()` | Count of `Rating` where `course__teacher=self` |

**Relationships going out from `User`:**

```
User
 ├── profile           → Profile (1:1, reverse)
 ├── balance           → Balance (1:1, reverse)
 ├── courses_taught    → Course[] (1:many, teacher FK)
 ├── enrolled          → Enrollment[] (1:many, student FK)
 ├── ratings           → Rating[] (1:many)
 ├── transactions      → Transaction[] (1:many)
 ├── balance_history   → BalanceHistory[] (1:many)
 ├── live_classes      → LiveClass[] (1:many, teacher FK)
 ├── forum_topics      → ForumTopic[] (1:many)
 ├── forum_comments    → ForumComment[] (1:many)
 └── replies           → Reply[] (1:many)
```

---

### `Profile` *(accounts/models.py — extends BaseModel)*

Stores supplemental user info. Always created automatically via a `post_save` signal on `User`.

| Field | Type | Notes |
|---|---|---|
| `user` | `OneToOneField → User` | `CASCADE` delete — profile dies with user |
| `birthday` | `DateField` | Nullable |
| `bio` | `TextField` | Nullable |
| `avatar` | `CloudinaryField` | Stored in Cloudinary `avatars/` folder |
| `phone_number` | `CharField(15)` | Nullable |
| `address` | `TextField` | Nullable |

> **Business rule:** Every `User` row guaranteed to have a `Profile` row (signal-enforced). Access via `user.profile`.

---

## Courses Domain

### `CourseCategory` *(courses/models.py — extends `CategoryBase`)*

A **hierarchical** category tree powered by `django-categories`.

| Field | Type | Notes |
|---|---|---|
| `name`, `slug`, `parent` | — | Inherited from `CategoryBase` |
| `description` | `TextField` | Nullable |

`CategoryBase` provides self-referential parent/children relations. The `home` app loads parent categories with `.children` to render nav trees.

---

### `Course` *(courses/models.py — extends BaseModel)*

The central content entity. Everything else — lectures, enrollments, payments, forums, live classes — hangs off a `Course`.

| Field | Type | Notes |
|---|---|---|
| `slug` | `SlugField(255)` | Unique. Auto-generated as `{title-slug}-{8-char-uuid}` on first save |
| `title` | `CharField(255)` | — |
| `short_introduction` | `CharField(500)` | Used in course cards |
| `course_description` | `TextField` | Full detail page |
| `level` | `CharField` | `beginner / intermediate / advanced` |
| `category` | `FK → CourseCategory` | `SET_NULL` on delete — course survives category deletion |
| `teacher` | `FK → User` | `CASCADE` — course deleted if teacher deleted. `related_name=courses_taught` |
| `course_image` | `CloudinaryField` | Stored in `course_images/` |
| `status` | `CharField` | `draft / published / archived`, default `draft` |
| `published_on` | `DateTimeField` | Nullable — set manually |
| `paid_course` | `BooleanField` | Auto-set to `True` in `save()` if `course_price > 0` |
| `course_price` | `DecimalField(10,2)` | 0.0 for free courses |
| `upcoming` | `BooleanField` | Marks pre-launch courses |
| `total_rating` | `DecimalField(5,2)` | Cached average — updated by `update_rating()` |
| `number_of_ratings` | `PositiveIntegerField` | Cached count |
| `verified` | `BooleanField` | Admin-set. Controls listing in homepage/search |
| `tags` | `TaggableManager` | `django-taggit` M2M |

**`save()` side-effects:**
1. Generates `slug` on first save only
2. Sets `paid_course = True` when `course_price > 0`
3. Raises `ValueError` if no teacher

**`update_rating()` — called from `Rating.save()`:**
```python
recalculate → number_of_ratings, total_rating → save(update_fields=[...])
```

**Computed methods:**

| Method | Query |
|---|---|
| `get_total_enrollments()` | `enrollments.filter(status=active).count()` |
| `get_rating_distribution()` | Annotated GROUP BY rating, returns `{1: %, 2: %, ...}` |
| `get_individual_ratings()` | `ratings.select_related("student")` |

---

### `CourseInfo` *(courses/models.py — extends BaseModel)*

Optional supplemental metadata for a course. One-to-one — each course has at most one.

| Field | Type | Notes |
|---|---|---|
| `course` | `OneToOneField → Course` | `CASCADE`, `related_name=info` |
| `what_you_will_learn` | `TextField` | Bullet points in practice |
| `who_this_course_is_for` | `TextField` | Target audience |
| `requirements` | `TextField` | Prerequisites |

Access: `course.info` — may raise `RelatedObjectDoesNotExist` if not created yet.

---

### `Rating` *(courses/models.py — extends BaseModel)*

Student review + star rating for a course.

| Field | Type | Notes |
|---|---|---|
| `student` | `FK → User` | `CASCADE`, `related_name=ratings` |
| `course` | `FK → Course` | `CASCADE`, `related_name=ratings` |
| `rating` | `PositiveSmallIntegerField` | Choices `1–5` |
| `review` | `TextField` | Optional text |

**Constraints:**
- `unique_together = (student, course)` — one rating per student per course, enforced at DB level
- `Index on course` — fast lookups when loading course detail

**`save()` side-effect:** Always calls `self.course.update_rating()` — recalculates `total_rating` and `number_of_ratings` on the parent `Course`. This means every rating write triggers a `Course` update.

---

### `Enrollment` *(courses/models.py — extends BaseModel)*

The join record between a student and a course. It is the source of truth for access control.

| Field | Type | Notes |
|---|---|---|
| `course` | `FK → Course` | `CASCADE`, `related_name=enrollments` |
| `student` | `FK → User` | `CASCADE`, `related_name=enrolled` |
| `status` | `CharField` | `active / pending / withdrawn / archived / completed` |
| `progression` | `PositiveIntegerField` | 0–100 (validated), updated via signals |

**Constraints:**
- `unique_together = [course, student]` — a student can only enroll in a course once

**Status lifecycle:**
```
pending → active       (payment success / free course checkout)
pending → withdrawn    (payment failure)
active  → completed    (manual or auto at 100% progression)
active  → archived     (teacher or admin action)
```

**Business dependency:** `Enrollment.status = active` is the gate for lecture access. Views check this before serving any content.

---

### `Module` *(courses/models.py — extends BaseModel)*

An ordered section within a course. Lectures belong to modules.

| Field | Type | Notes |
|---|---|---|
| `title` | `CharField(255)` | — |
| `course` | `FK → Course` | `CASCADE`, `related_name=modules` |
| `order` | `PositiveIntegerField` | Default 0. Unique per course |

**Constraints:**
- `UniqueConstraint(fields=[course, order])` — DB-level enforcement
- `save()` also raises `ValidationError` if order conflicts (application-level guard)
- `ordering = [order]` — always retrieved in order

---

### `CourseToken` *(courses/models.py — plain Model, no BaseModel)*

Approval workflow token. Created when a course is first created; must be set to `approved` by an admin before teachers can upload content or create live classes.

| Field | Type | Notes |
|---|---|---|
| `course` | `FK → Course` | `CASCADE`, `related_name=tokens` |
| `teacher` | `FK → User` | `CASCADE` |
| `status` | `CharField` | `pending / approved`, default `pending` |

> **Architectural note:** There can be multiple token rows per course (no unique constraint on `course`). Views check `CourseToken.objects.filter(course=..., status=approved).exists()`.

---

### `LastVisitedCourse` *(courses/models.py — plain Model)*

Tracks the most recent course a user visited. Used to resume learning.

| Field | Type | Notes |
|---|---|---|
| `user` | `FK → User` | `CASCADE` |
| `course` | `FK → Course` | `CASCADE` |
| `last_visited` | `DateTimeField(auto_now)` | Updated on every visit |

**Constraints:**
- `unique_together = [course, user]` — one row per user-course pair, updated (not duplicated) on revisit
- `ordering = [-last_visited]`

---

## Lecture Domain

### `Lecture` *(lecture/models.py — extends BaseModel)*

A single content unit within a Module. Can have multiple videos and PDFs.

| Field | Type | Notes |
|---|---|---|
| `course` | `FK → Course` | `CASCADE`, `related_name=lectures` — denormalized for direct lookup |
| `module` | `FK → Module` | `CASCADE`, `related_name=lectures` |
| `title` | `CharField(255)` | — |
| `description` | `TextField` | Nullable |
| `learning_objective` | `TextField` | Nullable |
| `order` | `PositiveIntegerField` | Unique per module |
| `slug` | `SlugField(255)` | Unique, auto-generated |

**Constraints:**
- `UniqueConstraint(fields=[module, order])` — DB-level
- `clean()` validates order uniqueness at application level too
- `save()` calls `full_clean()` on every save — unusual, enforces validation strictly

> `course` FK is redundant given `module → course`, but allows direct `Lecture.objects.filter(course=x)` queries without a join through Module.

---

### `LecturePDF` *(lecture/models.py — extends BaseModel)*

A PDF file attachment for a lecture.

| Field | Type | Notes |
|---|---|---|
| `lecture` | `FK → Lecture` | `CASCADE`, `related_name=pdf_files` |
| `pdf_file` | `FileField` | Uploaded to `lecture_pdfs/` on the configured storage backend |
| `pdf_title` | `CharField(255)` | — |

---

### `LectureVideo` *(lecture/models.py — extends BaseModel)*

A video upload for a lecture. Cloudinary processes it to HLS for adaptive streaming.

| Field | Type | Notes |
|---|---|---|
| `lecture` | `FK → Lecture` | `CASCADE`, `related_name=videos` |
| `video_file` | `CloudinaryField(resource_type=video)` | Raw upload |
| `video_title` | `CharField(255)` | — |
| `thumbnail` | `ImageField` | Nullable, local storage |
| `hls` | `CharField(500)` | HLS streaming manifest URL — populated after Cloudinary processing |
| `status` | `CharField` | `Pending / Processing / Completed` |
| `is_running` | `BooleanField` | Transient flag during processing |

**Business rule:** The `lecture_video` view serves the `hls` URL. Videos with `status=Pending` have no `hls` and cannot be played.

---

### `LectureCompletion` *(lecture/models.py — extends BaseModel)*

Records that a specific user completed a specific lecture. Drives the progression calculation.

| Field | Type | Notes |
|---|---|---|
| `user` | `FK → User` | `CASCADE` |
| `lecture` | `FK → Lecture` | `CASCADE` |
| `completed_at` | `DateTimeField(auto_now_add)` | — |

**Constraints:**
- `unique_together = (user, lecture)` — can only complete a lecture once

**Signal chain on save/delete:**
```
LectureCompletion created/deleted
  → signal: update_module_progression_on_save / on_delete
    → count completed lectures for this user in this course
    → (completed / total) * 100
    → write Enrollment.progression
```

---

### `LastVisitedModule` *(lecture/models.py — plain Model)*

Tracks the last lecture a user viewed within a module — used to resume playback position.

| Field | Type | Notes |
|---|---|---|
| `user` | `FK → User` | `CASCADE` |
| `module` | `FK → Module` | `CASCADE` |
| `lecture` | `FK → Lecture` | `CASCADE` — exact lecture, not just module |
| `last_visited` | `DateTimeField(auto_now)` | — |

**Constraints:**
- `unique_together = [module, user, lecture]`
- `ordering = [-last_visited]`

> The triple unique constraint means one row per `(user, module, lecture)` combination. Since a user visits multiple lectures in a module, this creates multiple rows. The view queries `.filter(user=..., module=...).order_by("-last_visited").first()` to find the resume point.

---

## Payments Domain

### `Transaction` *(payments/models.py — extends BaseModel)*

An immutable record of a completed SSLCommerz payment. All fields come directly from the gateway callback.

| Field | Type | Notes |
|---|---|---|
| `user` | `FK → User` | `DO_NOTHING` — preserves financial record if user deleted |
| `course` | `FK → Course` | `DO_NOTHING` — same reason |
| `enrollment` | `OneToOneField → Enrollment` | `DO_NOTHING`, `related_name=transaction` |
| `name` | `CharField(150)` | Buyer name from gateway |
| `amount` | `DecimalField(10,2)` | Amount charged |
| `tran_id` | `CharField(15)` | **Unique** SSLCommerz transaction ID |
| `val_id` | `CharField(75)` | Validation ID from gateway |
| `card_type` | `CharField(150)` | e.g. VISA, BKASH |
| `store_amount` | `DecimalField(10,2)` | Amount after gateway fees |
| `card_no` | `CharField(55)` | Masked card number |
| `bank_tran_id` | `CharField(155)` | Bank-side transaction ref |
| `status` | `CharField(55)` | Gateway status string |
| `tran_date` | `DateTimeField` | Timestamp from gateway |
| `currency` | `CharField(10)` | e.g. BDT |
| `card_issuer` | `CharField(255)` | Bank name |
| `card_brand` | `CharField(15)` | VISA/MC/etc |
| `card_issuer_country` | `CharField(55)` | — |
| `card_issuer_country_code` | `CharField(55)` | — |
| `currency_rate` | `DecimalField(10,2)` | Exchange rate at time of payment |
| `verify_sign` | `CharField(155)` | SSLCommerz signature (MD5) |
| `verify_sign_sha2` | `CharField(255)` | SSLCommerz signature (SHA2) |
| `risk_level` | `CharField(15)` | Fraud risk level |
| `risk_title` | `CharField(25)` | Human-readable risk label |

**Constraints:**
- `unique_together = (user, course)` — one transaction per user-course pair
- `tran_id` unique — idempotency guard

> `DO_NOTHING` on all FKs is intentional — transaction records must not be cascade-deleted when a user or course is removed.

---

### `Balance` *(payments/models.py — extends BaseModel)*

A teacher's running wallet balance. Created on first payment success.

| Field | Type | Notes |
|---|---|---|
| `user` | `OneToOneField → User` | `CASCADE`, `related_name=balance` |
| `amount` | `DecimalField(10,2)` | Current balance, default 0 |
| `last_updated` | `DateTimeField(auto_now)` | — |

**Business rule:** When a student's payment succeeds, `CheckoutSuccessView` increments `balance.amount` by `course.course_price`. No withdrawal mechanism exists yet.

---

### `BalanceHistory` *(payments/models.py — extends BaseModel)*

Append-only audit log of every balance change.

| Field | Type | Notes |
|---|---|---|
| `user` | `FK → User` | `CASCADE`, `related_name=balance_history` |
| `transaction` | `FK → Transaction` | `CASCADE`, nullable (allows manual adjustments) |
| `amount` | `DecimalField(10,2)` | Change amount |
| `previous_balance` | `DecimalField(10,2)` | Snapshot before |
| `new_balance` | `DecimalField(10,2)` | Snapshot after |
| `description` | `CharField(255)` | Human-readable reason |

---

### `PaymentGateway` *(payments/models.py — plain Model)*

Stores SSLCommerz credentials in the database.

| Field | Type | Notes |
|---|---|---|
| `store_id` | `CharField(500)` | SSLCommerz merchant ID |
| `store_pass` | `CharField(500)` | **Plaintext secret** — significant security risk |

> This model exists so admins can rotate credentials through Django Admin without a deployment. But storing credentials in plaintext in the DB is a serious vulnerability. Should be moved to environment variables.

---

## Live Classes Domain

### `LiveClass` *(live_classes/models.py — plain Model, no BaseModel)*

A scheduled Jitsi video session attached to a course.

| Field | Type | Notes |
|---|---|---|
| `course` | `FK → Course` | `CASCADE`, `related_name=live_classes` |
| `teacher` | `FK → User` | `CASCADE`, `related_name=live_classes` |
| `topic` | `CharField(255)` | Session title |
| `meeting_id` | `CharField(50)` | **Unique**, auto-generated as `mindjunkies-{10-char hex uuid}` |
| `scheduled_at` | `DateTimeField` | — |
| `duration` | `IntegerField` | Minutes, default 60 |
| `status` | `CharField` | `Upcoming / Ongoing / Completed` |
| `created_at` | `DateTimeField(auto_now_add)` | — |

**Methods:**

| Method | Logic |
|---|---|
| `generate_jwt_token()` | Reads `private.pem` from disk, builds RS256 JWT via `JaaSJwtBuilder`, returns token with moderator=True |
| `get_meeting_url_teacher()` | `https://8x8.vc/{APP_ID}/{meeting_id}?jwt={token}` |
| `get_meeting_url_student()` | `https://8x8.vc/{APP_ID}/{meeting_id}` (no JWT, public join) |

> No `BaseModel` — no `uuid`, no `created_at` from base (has its own `created_at`). Status is never auto-updated; it must be changed manually.

---

## Forums Domain

### `ForumTopic` *(forums/models.py — plain Model)*

A discussion thread within a course module.

| Field | Type | Notes |
|---|---|---|
| `title` | `CharField(255)` | — |
| `slug` | `SlugField(255)` | Unique, auto-generated |
| `content` | `CharField(150)` | **Very short** — effectively a subtitle/teaser |
| `author` | `FK → User` | `CASCADE`, `related_name=forum_topics` |
| `course` | `FK → Course` | `CASCADE`, `related_name=forum_posts` |
| `module` | `FK → Module` | `CASCADE`, `related_name=forum_posts` |
| `likes` | `M2M → User` | Through `LikedPost`, `related_name=likedTopics` |
| `created_at` / `updated_at` | `DateTimeField` | — |

`ordering = [-created_at]`

---

### `LikedPost` *(forums/models.py — plain Model)*

Through-table for `ForumTopic.likes`.

| Field | Notes |
|---|---|
| `topic → ForumTopic` | `CASCADE` |
| `user → User` | `CASCADE` |
| `created` | `auto_now_add` |

---

### `ForumComment` *(forums/models.py — plain Model)*

A direct reply to a `ForumTopic`.

| Field | Type | Notes |
|---|---|---|
| `topic` | `FK → ForumTopic` | `CASCADE`, `related_name=comments` |
| `content` | `CharField(150)` | Same short limit as topic |
| `author` | `FK → User` | `CASCADE`, `related_name=forum_comments` |
| `likes` | `M2M → User` | Through `LikedComment` |
| `created_at` / `updated_at` | `DateTimeField` | — |

`ordering = [created_at]` (ascending — oldest first)

---

### `Reply` *(forums/models.py — plain Model)*

A nested reply. Can reply to a `ForumComment` **or** to another `Reply` — enabling infinite nesting.

| Field | Type | Notes |
|---|---|---|
| `author` | `FK → User` | `SET_NULL` — reply survives if user is deleted |
| `parent_comment` | `FK → ForumComment` | Nullable, `CASCADE`, `related_name=replies` |
| `parent_reply` | `FK → Reply (self)` | Nullable, `CASCADE`, `related_name=replies` — **self-referential** |
| `body` | `CharField(150)` | — |
| `likes` | `M2M → User` | Through `LikedReply` |
| `created` | `DateTimeField(auto_now_add)` | — |

`ordering = [created]`

> `SET_NULL` on author is the only place across all models where a deletion doesn't cascade — author attribution is preserved as null rather than deleted.

---

### `LikedComment` / `LikedReply` *(forums/models.py)*

Through-tables for the comment and reply like M2M relations. Identical structure to `LikedPost`.

---

## Dashboard Domain

### `TeacherVerification` *(dashboard/models.py — extends BaseModel)*

Application form + approval record for becoming a verified teacher.

| Field | Type | Notes |
|---|---|---|
| `user` | `OneToOneField → User` | `CASCADE` — one verification per user |
| `full_name` | `CharField(255)` | — |
| `email` | `EmailField` | — |
| `phone` | `CharField(20)` | Nullable |
| `address` | `CharField(255)` | Nullable |
| `portfolio_links` | `TextField` | Nullable — free-form URLs |
| `important_links` | `TextField` | Nullable |
| `experience` | `TextField` | Nullable |
| `social_media` | `TextField` | Nullable |
| `certificates` | `M2M → Certificate` | `related_name=teacher_verifications` |
| `verified` | `BooleanField` | Default `False` — toggled by admin |
| `verification_date` | `DateTimeField` | Nullable — set on submission |

**`VerifiedTeacherRequiredMixin` depends on this model:**
```python
if not user.is_teacher:           → redirect to teacher_permission
if not verification.verified:     → redirect to verification_wait
```

---

### `Certificate` *(dashboard/models.py — extends BaseModel)*

A credential image uploaded as part of teacher verification.

| Field | Type | Notes |
|---|---|---|
| `image` | `ImageField` | Uploaded to `certificates/` |
| `description` | `CharField(255)` | Optional label |

Used via M2M on `TeacherVerification`.

---

## Complete Relationship Map

```
                         ┌──────────────┐
                         │     User     │ ← UUID PK
                         └──────┬───────┘
          ┌──────────────┬──────┼──────────┬──────────────┐
          │              │      │           │              │
     Profile(1:1)  Balance(1:1)  │    TeacherVer.(1:1)  LiveClass[]
                                 │
              ┌──────────────────┤ (teacher FK)
              │                  │ (student FK)
           Course[]           Enrollment[]
              │   \               │
              │    \              └── Transaction(1:1)
              │   CourseToken[]             │
              │                        BalanceHistory[]
              │
     ┌────────┴──────────────────────────────────────┐
     │                   │              │             │
  Module[]            Rating[]     LiveClass[]    ForumTopic[]
     │                                                │
  Lecture[]                                      ForumComment[]
  ┌─────┴──────────┐                                  │
  │                │                               Reply[]
LecturePDF[]  LectureVideo[]                    (self-referential)
```

---

## Key Business Logic Dependencies

### 1. Access Control Chain
```
Enrollment.status = "active"
  ↑ set by: CheckoutSuccessView (paid) or CheckoutView (free)
  ↑ cleared by: payment failure (withdrawn) or teacher removal
  → required by: lecture views, forum views, live class join
```

### 2. Rating → Course Denormalization
```
Rating.save()
  → course.update_rating()
    → Course.total_rating (cached average)
    → Course.number_of_ratings (cached count)
```
The `Course` row carries stale-able cached aggregates. If a `Rating` is bulk-deleted bypassing `.save()`, these go out of sync.

### 3. LectureCompletion → Enrollment.progression
```
LectureCompletion created/deleted (post_save / post_delete signal)
  → count user's completed lectures in course
  → (completed / total_in_course) * 100
  → Enrollment.progression = result
```
`Lecture` deletion also triggers recalculation for **all enrolled students** synchronously.

### 4. CourseToken Approval Gate
```
CourseToken.status = "approved"   (set by admin)
  → unlocks: content upload, live class creation
  → Course.verified = True         (separate admin action)
    → unlocks: course listing on homepage/search
```
These are **two separate approvals** — a course can be token-approved (teacher can upload) but not `verified` (not visible to students yet).

### 5. Payment → Balance Flow
```
SSLCommerz POST /success/
  → Transaction created
  → Balance.amount += course.course_price
  → BalanceHistory row appended (previous, new, delta)
  → Enrollment.status = "active"
```

### 6. Teacher Activation
```
TeacherVerification.verified = True (admin sets)
+ User.is_teacher = True            (admin sets separately)
  → VerifiedTeacherRequiredMixin passes
    → dashboard, course CRUD, lecture upload unlocked
```
**These two flags must both be set.** Forgetting either one leaves the teacher locked out.

---

## Schema Problem Areas

| Problem | Location | Risk |
|---|---|---|
| `ForumTopic.content` and `ForumComment.content` are `CharField(150)` | forums/models.py | Unusably short for real discussion |
| `PaymentGateway.store_pass` stored plaintext | payments/models.py | Credential exposure if DB is dumped |
| `Transaction.unique_together(user, course)` — one transaction per course | payments/models.py | Blocks repurchase or course re-enrollment after refund |
| `CourseToken` has no unique constraint on `course` | courses/models.py | Multiple tokens can exist; views check `.exists()` not `.get()` |
| `BaseModel.deleted_at` unused — no manager enforces soft-delete | config/models.py | Field is dead weight; `deleted` rows are always visible |
| `Rating.save()` always calls `course.update_rating()` — O(n) query on every save | courses/models.py | Unnecessary full recalculation; use `F()` incremental update instead |
| `LastVisitedModule` triple `unique_together` creates many rows per user | lecture/models.py | Never cleaned up — grows indefinitely |
| `LiveClass.status` never auto-updated | live_classes/models.py | Stale `Upcoming` rows even after the session ends |

---
