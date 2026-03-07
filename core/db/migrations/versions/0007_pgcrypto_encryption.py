"""Enable pgcrypto encryption at rest for sensitive columns.

Adds transparent encrypt/decrypt helper functions backed by pgcrypto's
PGP symmetric encryption. Encrypted BYTEA columns are added alongside
existing plaintext columns (non-destructive) so rollback is safe.

The encryption key must be set before using the helpers:
  - Per-session:  SET app.encryption_key = 'your-key-here';
  - Persistent:   ALTER SYSTEM SET app.encryption_key = 'your-key-here';
                   SELECT pg_reload_conf();

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-08
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable pgcrypto extension (provides pgp_sym_encrypt / pgp_sym_decrypt)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 2. Create helper function: dce_encrypt(plaintext) -> bytea
    #    Reads the symmetric key from the GUC variable app.encryption_key.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION dce_encrypt(plaintext TEXT)
        RETURNS BYTEA
        LANGUAGE sql IMMUTABLE STRICT
        AS $$
            SELECT pgp_sym_encrypt(
                plaintext,
                current_setting('app.encryption_key')
            )
        $$
        """
    )

    # 3. Create helper function: dce_decrypt(ciphertext) -> text
    op.execute(
        """
        CREATE OR REPLACE FUNCTION dce_decrypt(ciphertext BYTEA)
        RETURNS TEXT
        LANGUAGE sql IMMUTABLE STRICT
        AS $$
            SELECT pgp_sym_decrypt(
                ciphertext,
                current_setting('app.encryption_key')
            )
        $$
        """
    )

    # 4. Add encrypted columns alongside existing plaintext columns
    #    (non-destructive — originals kept for rollback safety)
    op.execute(
        "ALTER TABLE messages "
        "ADD COLUMN IF NOT EXISTS content_encrypted BYTEA"
    )
    op.execute(
        "ALTER TABLE query_analytics "
        "ADD COLUMN IF NOT EXISTS query_text_encrypted BYTEA"
    )


def downgrade() -> None:
    # Drop encrypted columns
    op.execute(
        "ALTER TABLE query_analytics "
        "DROP COLUMN IF EXISTS query_text_encrypted"
    )
    op.execute(
        "ALTER TABLE messages "
        "DROP COLUMN IF EXISTS content_encrypted"
    )

    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS dce_decrypt(BYTEA)")
    op.execute("DROP FUNCTION IF EXISTS dce_encrypt(TEXT)")

    # Keep the pgcrypto extension — other things may depend on it
