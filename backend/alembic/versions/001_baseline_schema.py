"""Baseline schema matching init.sql

Revision ID: 001_baseline

This migration represents the existing database schema.
For existing databases, stamp this revision without running it.
For new databases, this creates all tables from scratch.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("document_type", sa.String(50)),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index("idx_documents_uploaded_by", "documents", ["uploaded_by"])
    op.create_index("idx_documents_document_type", "documents", ["document_type"])

    # Extractions
    op.create_table(
        "extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("raw_text", sa.Text),
        sa.Column("structured_data", JSONB, nullable=False),
        sa.Column("confidence_scores", JSONB),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("extraction_metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_extractions_document_id", "extractions", ["document_id"])
    op.execute("CREATE INDEX IF NOT EXISTS idx_extractions_structured_data ON extractions USING GIN(structured_data)")

    # Validation results
    op.create_table(
        "validation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("extraction_id", UUID(as_uuid=True), sa.ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("validation_rules", JSONB, nullable=False),
        sa.Column("validation_status", sa.String(20), nullable=False),
        sa.Column("validation_errors", JSONB),
        sa.Column("validated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_validation_extraction_id", "validation_results", ["extraction_id"])

    # Reviews
    op.create_table(
        "reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("corrections", JSONB, nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("review_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_reviews_document_id", "reviews", ["document_id"])
    op.create_index("idx_reviews_reviewed_by", "reviews", ["reviewed_by"])

    # Audit trails
    op.create_table(
        "audit_trails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("performed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("changes", JSONB),
        sa.Column("audit_metadata", JSONB),
    )
    op.create_index("idx_audit_document_id", "audit_trails", ["document_id"])
    op.create_index("idx_audit_performed_at", "audit_trails", ["performed_at"])

    # Exports
    op.create_table(
        "exports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exported_to", sa.String(255), nullable=False),
        sa.Column("export_payload", JSONB, nullable=False),
        sa.Column("export_status", sa.String(20), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True)),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_exports_document_id", "exports", ["document_id"])
    op.create_index("idx_exports_status", "exports", ["export_status"])

    # Default admin user (password: admin123 - bcrypt)
    op.execute(
        "INSERT INTO users (email, password_hash, role) "
        "VALUES ('admin@sortex.ai', '$2b$12$E2RXvif2fug6G9jVhDevHu78b8OIAB8KXstiPqKcFEprsSdk0.oSO', 'admin') "
        "ON CONFLICT (email) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("exports")
    op.drop_table("audit_trails")
    op.drop_table("reviews")
    op.drop_table("validation_results")
    op.drop_table("extractions")
    op.drop_table("documents")
    op.drop_table("users")
