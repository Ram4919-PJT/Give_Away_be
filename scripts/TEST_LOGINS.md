# Give Away — test logins (seeded data)

Password for **every** account below: `Test@1234`

Seed with:

```powershell
cd D:\Aja\Give_away\Give_Away_be
python scripts\seed_database.py
```

Databases: `iam_db`, `core_mgmt_db`, `communication_db`

## Accounts

| Purpose | Email | Role | Verification |
|---------|-------|------|--------------|
| Admin | `admin@giveaway.org` | SUPER_ADMIN | n/a |
| Verified donor | `ananya.donor@gmail.com` | DONOR | VERIFIED |
| Pending donor | `pending.donor@gmail.com` | DONOR | SUBMITTED / pending |
| Verified donor (2) | `vikram.donor@yahoo.com` | DONOR | VERIFIED |
| Verified receiver | `ramesh.receiver@gmail.com` | RECEIVER | VERIFIED |
| Pending receiver | `sita.receiver@gmail.com` | RECEIVER | DOCUMENTS_SUBMITTED |
| Under-review receiver | `gita.r@gmail.com` | RECEIVER | UNDER_REVIEW |
| Verified NGO | `contact@hopefoundation.org` | NGO | VERIFIED |
| Pending NGO | `info@careshare.org` | NGO | UNDER_REVIEW |
| Verified NGO (2) | `help@smiletrust.org` | NGO | VERIFIED |

## Mobiles (10-digit)

| Email | Mobile |
|-------|--------|
| admin@giveaway.org | 9876543210 |
| ananya.donor@gmail.com | 9876543211 |
| pending.donor@gmail.com | 9876543212 |
| ramesh.receiver@gmail.com | 9876543213 |
| sita.receiver@gmail.com | 9876543214 |
| contact@hopefoundation.org | 9876543215 |
| info@careshare.org | 9876543216 |
| vikram.donor@yahoo.com | 9876543217 |
| gita.r@gmail.com | 9876543218 |
| help@smiletrust.org | 9876543219 |

## Seed files

| File | Database |
|------|----------|
| `scripts/seed_iam.sql` | `iam_db` |
| `scripts/seed_core.sql` | `core_mgmt_db` |
| `scripts/seed_communication.sql` | `communication_db` |

Document / logo URLs live in `verification_documents.file_url` (paths like `/assets/seed/...`) so the frontend can load them from the API once wired.
