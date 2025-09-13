# Tests for config/supabase_client.test_connection
#
# Strategy:
# - Patch config.supabase_client.supabase_service with a stub object exposing table(...).select(...).limit(1).execute().
# - Simulate success (no exception) and failure (raise Exception) paths.
# - Also simulate supabase_service=None to ensure function returns False with helpful print.
#
# Test cases:
# - supabase_service is None -> returns False; prints advisory message.
# - Successful select -> returns True.
# - select raises -> returns False and prints failure message.
#
# Notes:
# - Avoid importing real supabase client; strictly patch the module attribute.

