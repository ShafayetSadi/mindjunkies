# MindJunkies — Product Feature Analysis

## Core Features
*Fully implemented, complete user journeys, production-ready*

### Authentication & Identity
| Feature | Details |
|---|---|
| User registration & login | Email/password via django-allauth |
| Email verification | Mandatory, blocks access until verified |
| Password reset / change | Full allauth flow |
| Google OAuth2 login | Social account linking |
| Auto profile creation | Signal-driven on user signup |
| Profile view & edit | Avatar (Cloudinary), bio, phone, address, birthday |

### Course Catalog & Discovery
| Feature | Details |
|---|---|
| Course listing | All published + verified courses |
| Course detail page | Description, price, level, teacher, lecture count |
| New courses feed | Ordered by creation date, excludes enrolled |
| Popular courses feed | Ordered by active enrollment count, cached 5 min |
| Category browsing | Hierarchical categories; parent → children via HTMX |
| Course search | Title `icontains` with highlighted match text in results |
| Course tags | `django-taggit` M2M; courses can be tagged |
| Homepage | Shows new, popular, enrolled courses and categories |

### Course Management (Teacher)
| Feature | Details |
|---|---|
| Create course | Slug auto-generated, CourseToken(pending) created |
| Edit course | Update any field; slug preserved |
| Delete course | Teacher-only; cascades to modules, lectures, enrollments |
| Module creation | Ordered sections within a course |
| Module editing | Title and order update |
| Module deletion | Cascades to lectures |
| Course status workflow | `draft → published → archived` |
| Course publish gating | `verified=True` required for homepage/search visibility |

### Lecture Content (Teacher)
| Feature | Details |
|---|---|
| Create lecture | Ordered within module, auto-slug |
| Edit lecture | Title, description, learning objective |
| Delete lecture | Triggers progression recalculation for all students |
| Upload video | Cloudinary upload; HLS URL stored after processing |
| Upload PDF | `FileField`-based attachment, `lecture_pdfs/` path |
| Content gating | Upload blocked until `CourseToken.status = approved` |

### Learning Experience (Student)
| Feature | Details |
|---|---|
| Enroll in free course | Instant `active` enrollment at checkout |
| Enroll in paid course | SSLCommerz gateway → `pending` → `active` on success |
| Video playback | HLS adaptive stream served from Cloudinary |
| PDF viewing | In-browser PDF display |
| Mark lecture complete | Creates `LectureCompletion` record |
| Course progression | Auto-calculated `(completed/total)*100` via signals |
| Resume last position | `LastVisitedModule` tracks exact lecture per module |

### Payment Processing
| Feature | Details |
|---|---|
| SSLCommerz checkout | BDT payments; redirect-based gateway flow |
| Free course bypass | No gateway redirect; immediate enrollment |
| Payment success handler | Creates `Transaction`, activates `Enrollment` |
| Payment failure handler | Sets `Enrollment.status = withdrawn` |
| Teacher balance | `Balance` incremented on each sale |
| Balance history | Append-only audit log with before/after snapshots |
| Transaction records | Full SSLCommerz response persisted (card, risk, signatures) |

### Teacher Dashboard
| Feature | Details |
|---|---|
| Teacher verification | Application form with certificates (image upload) |
| Verification wait page | Status page post-submission |
| Dashboard home | Shows published and unverified courses |
| Course status views | Separate views for draft, published, archived |
| Balance & transactions | Paginated transaction history (10/page) |
| Student enrollment list | Per-course list of enrolled students |
| Remove student | Unenroll a specific student from a course |

### Live Classes
| Feature | Details |
|---|---|
| Schedule live class | Topic, date/time, duration; conflict check |
| List live classes | Per-course list with status (Upcoming/Ongoing/Completed) |
| Join live class | Jitsi 8x8.vc iframe embed |
| Teacher JWT token | RS256 signed token with moderator rights |
| Student public join | Unauthenticated Jitsi URL (no JWT) |
| Lecture home integration | Today's and this week's live classes shown in course view |

### Discussion Forums
| Feature | Details |
|---|---|
| Forum home | Per-course forum landing |
| Module-scoped threads | Topics scoped to course + module |
| Create topic | Title + short content post |
| Edit topic | Author can update |
| Delete topic | Author can delete |
| Comment on topic | First-level replies to topics |
| Delete comment | Author can delete |
| Nested replies | Reply to a comment or to another reply (self-referential) |
| Delete reply | Author-only, returns HTMX empty response |
| Threaded reply form | HTMX-loaded inline reply form |
| Like topics | Toggle like via M2M through-table |
| Like comments | Same pattern |
| Like replies | Same pattern |
| Forum search | Elasticsearch `match` query on topic title |

---

## Secondary Features
*Implemented and working, but peripheral to the main learning flow*

| Feature | Location | Notes |
|---|---|---|
| Course rating (1–5 stars) | `courses/` | One rating per student per course; updates course average on save |
| Written review text | `courses/` | Stored with rating, displayed on course detail |
| Rating distribution chart | `Course.get_rating_distribution()` | Returns `{1: %, 2: %, ...}` — frontend must render it |
| Instructor stat methods | `accounts/User` | `get_instructor_rating()`, `get_number_of_students()`, `get_number_of_courses()` |
| `CourseInfo` supplemental page | `courses/CourseInfo` | What you'll learn, who it's for, requirements |
| Upcoming course flag | `Course.upcoming` | Boolean field for pre-launch courses |
| Course-level tags | `TaggableManager` | Stored, not yet surfaced in search or filtering |
| Cache invalidation signal | `courses/signals.py` | Clears `popular_courses` / `new_courses` on course creation |
| `LastVisitedCourse` tracking | `courses/` | Tracks per-user last-visited course |
| Request profiling | `django-silk` | Profiling middleware always active |
| Admin dashboard | `django-unfold` | Custom admin UI for all models |
| HTMX subcategory load | `home/views.py` | Dynamic category children without page reload |
| `LectureCompletion` deletion | `lecture/signals.py` | Progression recalculated when completion removed |
| `Lecture` deletion signal | `lecture/signals.py` | Recalculates all students' progression when a lecture is deleted |
| Multiple certificates upload | `dashboard/` | Teacher can attach N certificate images to verification |

---

## Experimental / Incomplete Features
*Code exists but the feature is broken, half-wired, or never surfaced to users*

### Broken
| Feature | File | Problem |
|---|---|---|
| **Teacher balance crediting** | `payments/views.py:156–161` | `CheckoutSuccessView` fetches the student's `Balance` instead of the teacher's. The teacher's revenue is never credited correctly. `BalanceHistory` is also written against the wrong user. |
| **`ContentListView` status filtering** | `dashboard/views.py:42` | The view always queries `status="published"` regardless of the `status` URL parameter. The draft/archive status pages work only because `DraftView` and `ArchiveView` override it separately. |

### Stub / Dead Code
| Feature | File | Problem |
|---|---|---|
| **Soft delete** | `config/models.py` | `BaseModel.deleted_at` field defined on every model. No `SoftDeleteManager`, no queryset filter, no `delete()` override — field is set nowhere and read nowhere. |
| **`LectureVideo.status` processing pipeline** | `lecture/models.py` | `Pending / Processing / Completed` states defined; `is_running` flag defined. Nothing in the codebase transitions these states — no Celery task, no webhook, no signal. Videos are uploaded directly to Cloudinary; the status field stays `Pending` forever. |
| **`LiveClass.status` lifecycle** | `live_classes/models.py` | `Upcoming / Ongoing / Completed` states defined. No scheduled task, no signal, no view updates this field. All classes stay `Upcoming` indefinitely after creation. |
| **`Course.published_on`** | `courses/models.py` | `DateTimeField(null=True)` — never populated in any view or signal. The field exists but no part of the app sets it when a course is published. |
| **`Course.upcoming`** | `courses/models.py` | Boolean flag with no dedicated view, filter, or UI for upcoming/pre-launch courses. |
| **Course tags** | `courses/models.py` | `TaggableManager` is defined and tags can be saved, but no URL, view, or template uses tags for filtering or discovery. |
| **`CourseInfo` model** | `courses/models.py` | Model defined (`what_you_will_learn`, `requirements`, `who_this_course_is_for`). No form, no view, no URL to create or update it. |
| **`Enrollment.status = completed`** | `courses/models.py` | The `completed` status exists in choices but nothing in the codebase sets it — not even when `progression` reaches 100%. |

### Incomplete / Partially Wired
| Feature | File | Problem |
|---|---|---|
| **Elasticsearch course search** | `home/views.py` | Homepage search uses `Course.objects.filter(title__icontains=...)`. The `ForumTopicDocument` in `forums/documents.py` uses Elasticsearch, but no `CourseDocument` exists — course search does not use it. |
| **HLS video playback** | `lecture/models.py` | `LectureVideo.hls` field stores the streaming URL, but no mechanism populates it. Cloudinary video upload saves `video_file` but the HLS transcode URL must be manually set or requires a webhook that is not implemented. |
| **`PaymentGateway` model** | `payments/models.py` | Credentials fetched from DB via `PaymentGateway.objects.first()` in `CheckoutView`. If no row exists, the checkout silently fails. No admin validation, no fallback to env vars. |
| **Reply-to-reply nesting** | `forums/models.py` | `Reply.parent_reply` self-FK supports infinite nesting. The `ReplyFormView` handles one level of nesting. Deeper thread rendering is not confirmed in templates. |
| **Debug `print()` statements** | Multiple files | `home/views.py` (3×), `lecture/views.py` (2×), `dashboard/views.py` (2×) — production log noise. |
| **Hardcoded payment customer data** | `payments/views.py:90–91` | `cus_add1="Goalpara"`, `cus_city="Thakurgaon"` hardcoded instead of reading from `user.profile.address`. |
| **`CourseToken` multiple rows** | `courses/models.py` | No `unique` constraint on `(course,)`. Multiple tokens can exist per course. Views use `.filter(...).exists()` which works, but the data model is ambiguous. |
