# App Settings Guidance

This project stores global configuration in the `app_settings` table. A value should become a setting when:

* It affects the entire installation rather than a single meeting or user.
* Administrators may need to change it without a code deploy.
* It is not specific to a single record for audit purposes.

Examples: site title, default logo path or the email address used for outgoing mail.

Values that belong to individual meetings, members or other models should remain fields on those tables. Truly constant strings such as permission names can stay hard coded.
