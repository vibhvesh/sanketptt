# Sanket IT Intelligence — setup
This module is part of the existing SanketPTT website and is published at:
https://sanketptt.com/it-intelligence/

1. Open the Supabase SQL editor: https://supabase.com/dashboard/project/djpkcubjnbpueyrqtcch/sql/new
2. Run the SQL in schema.sql.
3. Open https://supabase.com/dashboard/project/djpkcubjnbpueyrqtcch/auth/providers and ensure Email authentication is enabled.
4. Open the module URL and use Sign in → Create account.
5. Inventory records are private per authenticated user through owner_id RLS policies.

The Supabase publishable key is public by design. Never place a service-role/secret key in frontend files.
This preview currently provides an inventory register and basic counts, not a full monitoring agent or analytics pipeline.
