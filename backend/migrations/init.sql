-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL,
    document_type VARCHAR(50),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);

-- Create extractions table
CREATE TABLE IF NOT EXISTS extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    extraction_method VARCHAR(20) NOT NULL,
    raw_text TEXT,
    structured_data JSONB NOT NULL,
    confidence_scores JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    extraction_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id);
CREATE INDEX IF NOT EXISTS idx_extractions_structured_data ON extractions USING GIN(structured_data);

-- Create validation_results table
CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
    validation_rules JSONB NOT NULL,
    validation_status VARCHAR(20) NOT NULL,
    validation_errors JSONB,
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_extraction_id ON validation_results(extraction_id);

-- Create reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reviewed_by UUID NOT NULL REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    corrections JSONB NOT NULL,
    review_status VARCHAR(20) NOT NULL,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_document_id ON reviews(document_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_by ON reviews(reviewed_by);

-- Create audit_trails table
CREATE TABLE IF NOT EXISTS audit_trails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    performed_by UUID NOT NULL REFERENCES users(id),
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changes JSONB,
    audit_metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_document_id ON audit_trails(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_performed_at ON audit_trails(performed_at);

-- Create exports table
CREATE TABLE IF NOT EXISTS exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    exported_to VARCHAR(255) NOT NULL,
    export_payload JSONB NOT NULL,
    export_status VARCHAR(20) NOT NULL,
    exported_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exports_document_id ON exports(document_id);
CREATE INDEX IF NOT EXISTS idx_exports_status ON exports(export_status);

-- Insert default admin user (password: admin123 - to be changed in production!)
-- bcrypt hash of 'admin123'. Regenerate with: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash('admin123'))"
INSERT INTO users (email, password_hash, role)
VALUES ('admin@sortex.ai', '$2b$12$E2RXvif2fug6G9jVhDevHu78b8OIAB8KXstiPqKcFEprsSdk0.oSO', 'admin')
ON CONFLICT (email) DO NOTHING;

