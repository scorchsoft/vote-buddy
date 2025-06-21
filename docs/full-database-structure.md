# Full Database Structure

_Last updated: 2025-06-27_

This document summarises all tables and columns created by the Alembic migrations. It should help contributors and AI tools understand the schema without opening each migration file.

## Table overview

### roles
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| name | String(50) | Unique |

### permissions
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| name | String(50) | Unique |

### roles_permissions
| Column | Type | Notes |
|-------|------|-------|
| role_id | Integer | PK, FK `roles.id` |
| permission_id | Integer | PK, FK `permissions.id` |

### users
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| email | String(255) | Unique |
| password_hash | String(255) | |
| role_id | Integer | FK `roles.id` |
| is_active | Boolean | |
| created_at | DateTime | |

### meetings
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| title | String(255) | Not null |
| type | String(10) | |
| notice_date | DateTime | |
| opens_at_stage1 | DateTime | |
| closes_at_stage1 | DateTime | |
| opens_at_stage2 | DateTime | |
| closes_at_stage2 | DateTime | |
| ballot_mode | String(20) | |
| revoting_allowed | Boolean | |
| status | String(50) | |
| chair_notes_md | Text | |
| quorum | Integer | Default `0` |
| stage1_locked | Boolean | Default `False` |
| stage2_locked | Boolean | Default `False` |
| stage1_reminder_sent_at | DateTime | |
| public_results | Boolean | Default `False` |
| extension_reason | Text | Reason for extending a stage |
| stage1_manual_votes | Integer | Manual Stage 1 turnout |
| stage2_manual_for | Integer | Manual Stage 2 'for' count |
| stage2_manual_against | Integer | Manual Stage 2 'against' count |
| stage2_manual_abstain | Integer | Manual Stage 2 'abstain' count |

### members
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| meeting_id | Integer | FK `meetings.id` |
| name | String(255) | |
| email | String(255) | |
| proxy_for | String(255) | |
| email_opt_out | Boolean | Default `false` |

### motions
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| meeting_id | Integer | FK `meetings.id` |
| title | String(255) | |
| text_md | Text | |
| final_text_md | Text | |
| category | String(20) | |
| threshold | String(20) | |
| ordering | Integer | |
| status | String(50) | |
| withdrawn | Boolean | |
| modified_at | DateTime | |
| withdrawal_requested_at | DateTime | |
| chair_approved_at | DateTime | |
| board_approved_at | DateTime | |

### motion_options
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| motion_id | Integer | FK `motions.id` |
| text | String(255) | |

### amendments
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| meeting_id | Integer | FK `meetings.id` |
| motion_id | Integer | FK `motions.id` |
| text_md | Text | |
| order | Integer | |
| status | String(50) | |
| reason | Text | |
| proposer_id | Integer | FK `members.id` |
| seconder_id | Integer | FK `members.id` |
| board_seconded | Boolean | |
| tie_break_method | String(20) | |
| seconded_at | DateTime | |
| seconded_method | String(50) | |

### amendment_conflicts
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| meeting_id | Integer | FK `meetings.id` |
| amendment_a_id | Integer | FK `amendments.id` |
| amendment_b_id | Integer | FK `amendments.id` |
| tie_break_method | String(20) | |

### amendment_merges
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| combined_id | Integer | FK `amendments.id` |
| source_id | Integer | FK `amendments.id` |

### amendment_objections
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| amendment_id | Integer | FK `amendments.id` |
| member_id | Integer | FK `members.id` |
| created_at | DateTime | |

### runoffs
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| meeting_id | Integer | FK `meetings.id` |
| amendment_a_id | Integer | FK `amendments.id` |
| amendment_b_id | Integer | FK `amendments.id` |
| tie_break_method | String(20) | |

### vote_tokens
| Column | Type | Notes |
|-------|------|-------|
| token | String(64) | SHA-256 hash of the emailed token |
| member_id | Integer | FK `members.id` |
| stage | Integer | |
| used_at | DateTime | |

### unsubscribe_tokens
| Column | Type | Notes |
|-------|------|-------|
| token | String(36) | Primary key |
| member_id | Integer | FK `members.id` |
| created_at | DateTime | |

### password_reset_tokens
| Column | Type | Notes |
|-------|------|-------|
| token | String(36) | Primary key |
| user_id | Integer | FK `users.id` |
| created_at | DateTime | |
| used_at | DateTime | |

### votes
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| member_id | Integer | FK `members.id` |
| amendment_id | Integer | FK `amendments.id` (nullable) |
| motion_id | Integer | FK `motions.id` (nullable) |
| choice | String(10) | |
| hash | String(128) | |

### app_settings
| Column | Type | Notes |
|-------|------|-------|
| id | Integer | Primary key |
| key | String(50) | Unique |
| value | String(255) | |
| group | String(50) | |

