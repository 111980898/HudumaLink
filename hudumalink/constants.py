"""
Shared, read-only reference data for HudumaLink.

Keeping these lists in one place means the forms, the validation logic, the
analytics queries and the templates can never disagree about what a valid
"category" or "status" is.
"""

# --- Service categories -----------------------------------------------------
# Each category is routed to a county department and has a service-level
# target (in days) used to flag overdue requests on the admin dashboard.
CATEGORIES = {
    "Streetlight Fault":          {"department": "Energy & Public Lighting",   "sla_days": 5,  "icon": "💡"},
    "Water Supply Problem":       {"department": "Water & Sanitation",         "sla_days": 3,  "icon": "💧"},
    "Garbage Collection":         {"department": "Environment & Waste",        "sla_days": 4,  "icon": "🗑️"},
    "Roads & Drainage":           {"department": "Roads & Public Works",       "sla_days": 10, "icon": "🛣️"},
    "Public Health & Sanitation": {"department": "Health Services",            "sla_days": 4,  "icon": "🏥"},
    "Other Public Service":       {"department": "County Customer Care Desk",  "sla_days": 7,  "icon": "📨"},
}

# --- Geography --------------------------------------------------------------
# The seven sub-counties of Murang'a County.
SUB_COUNTIES = [
    "Kangema", "Mathioya", "Kiharu", "Kigumo", "Maragwa", "Kandara", "Gatanga",
]

# --- Workflow ---------------------------------------------------------------
PRIORITIES = ["Low", "Normal", "High", "Urgent"]

STATUSES = ["Pending", "In Progress", "Resolved", "Rejected"]
OPEN_STATUSES = ("Pending", "In Progress")

# A request may only move along these edges. This prevents nonsense such as
# jumping from "Rejected" straight to "Resolved" and keeps the history honest.
ALLOWED_TRANSITIONS = {
    "Pending":     {"In Progress", "Rejected"},
    "In Progress": {"Resolved", "Rejected", "Pending"},
    "Resolved":    {"In Progress"},          # re-open if the fix did not hold
    "Rejected":    {"Pending"},              # allow an appeal to be reviewed
}

# --- Uploads ----------------------------------------------------------------
# Extension -> the magic bytes that a genuine file of that type begins with.
IMAGE_SIGNATURES = {
    "png":  (b"\x89PNG\r\n\x1a\n",),
    "jpg":  (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif":  (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),
}
