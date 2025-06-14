# Member CSV Import

Coordinators can bulk add members to a meeting by uploading a CSV file.

## CSV format

```
member_id,name,email,vote_weight,proxy_for
1234,Jane Smith,jane@example.com,1,
1235,John Doe,john@example.com,1,1234
```

Column order must match exactly. Duplicate emails are rejected.

## Steps

1. Open the meeting and choose **Import Members**.
2. Select your CSV and click **Upload**.
3. Each row is stored as a `Member` and an initial Stage 1 `VoteToken` is generated.

Tokens can later be emailed using the standard template.
