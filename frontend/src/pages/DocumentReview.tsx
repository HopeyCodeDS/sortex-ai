import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  RefreshCw,
  RotateCw,
  Save,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  Play,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { useDocumentReview } from '../hooks/useDocumentReview';
import { getDocument } from '../services/documents';
import client from '../api/client';
import { RAW_TEXT_PREVIEW_LENGTH } from '../constants';
import TopBar from '../components/layout/TopBar';
import { Card } from '../components/ui/Card';
import Button from '../components/ui/Button';
import PipelineSteps from '../components/ui/PipelineSteps';
import ConfidenceBar from '../components/ui/ConfidenceBar';
import { Skeleton } from '../components/ui/Skeleton';

const PIPELINE_STAGES = ['UPLOADED', 'PROCESSING', 'EXTRACTED', 'VALIDATED', 'REVIEWED', 'EXPORTED', 'FAILED'] as const;

/** Format a structured_data value for display in a text input. */
function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return JSON.stringify(value);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

const MetadataGrid: React.FC<{ metadata: Record<string, unknown> }> = ({ metadata }) => {
  const meta = metadata as Record<string, any>;
  const confidence = meta.classification_confidence;
  const confidenceNum = typeof confidence === 'number' ? confidence : (typeof confidence === 'string' ? parseFloat(confidence) : null);

  return (
    <div className="px-4 py-3 text-sm">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <span className="text-slate-500">OCR Provider:</span>{' '}
          <span className="font-medium text-slate-900">{String(meta.ocr_provider || 'Unknown')}</span>
        </div>
        <div>
          <span className="text-slate-500">LLM Provider:</span>{' '}
          <span className="font-medium text-slate-900">{String(meta.llm_provider || 'N/A')}</span>
        </div>
        <div>
          <span className="text-slate-500">LLM Model:</span>{' '}
          <span className="font-medium text-slate-900">{String(meta.llm_model || 'N/A')}</span>
        </div>
        {confidenceNum != null && !isNaN(confidenceNum) && (
          <div>
            <span className="text-slate-500">Confidence:</span>{' '}
            <span className="font-medium text-slate-900">{Math.round(confidenceNum * 100)}%</span>
          </div>
        )}
        {meta.classification_method && (
          <div>
            <span className="text-slate-500">Method:</span>{' '}
            <span className="font-medium text-slate-900">{String(meta.classification_method)}</span>
          </div>
        )}
        {meta.error && (
          <div className="col-span-2">
            <span className="text-red-600 font-medium">Error: {String(meta.error)}</span>
          </div>
        )}
        {meta.fallback && (
          <div className="col-span-2">
            <span className="text-amber-600">Fallback: {String(meta.fallback)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const DocumentReview: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const [documentStatus, setDocumentStatus] = useState<string | null>(null);
  const {
    extraction,
    validation,
    review,
    corrections,
    setCorrection,
    save,
    approve,
    reject,
    retryExtraction,
    fetchData,
    loading,
    saving,
    canSave,
  } = useDocumentReview(documentId, documentStatus);
  const [documentFilename, setDocumentFilename] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [restartingProcessing, setRestartingProcessing] = useState(false);

  const refreshDocumentStatus = useCallback(async () => {
    if (!documentId) return;
    try {
      const d = await getDocument(documentId);
      setDocumentStatus(d.status);
      setDocumentFilename(d.original_filename);
    } catch {
      // ignore
    }
  }, [documentId]);

  const refreshData = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetchData();
      await refreshDocumentStatus();
    } finally {
      setRefreshing(false);
    }
  }, [fetchData, refreshDocumentStatus]);

  useEffect(() => {
    refreshDocumentStatus();
  }, [refreshDocumentStatus]);

  useEffect(() => {
    if (documentStatus !== 'PROCESSING') return;
    const t = setInterval(refreshData, 5000);
    return () => clearInterval(t);
  }, [documentStatus, refreshData]);

  const handleRestartProcessing = useCallback(async () => {
    if (!documentId) return;
    setRestartingProcessing(true);
    try {
      await client.post(`/documents/${documentId}/reprocess`);
      toast.success('Reprocessing started');
      await refreshData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to restart processing');
    } finally {
      setRestartingProcessing(false);
    }
  }, [documentId, refreshData]);

  const handleSave = async () => {
    try {
      await save();
      toast.success('Review saved successfully');
      await refreshDocumentStatus();
    } catch (e) {
      toast.error((e as Error).message || 'Failed to save review');
    }
  };

  const handleApprove = async () => {
    try {
      await approve();
      toast.success('Review approved');
      await refreshDocumentStatus();
    } catch (e) {
      toast.error((e as Error).message || 'Failed to approve review');
    }
  };

  const handleReject = async () => {
    try {
      await reject();
      toast.success('Review rejected — corrections can be resubmitted');
      await refreshDocumentStatus();
    } catch (e) {
      toast.error((e as Error).message || 'Failed to reject review');
    }
  };

  const isProcessing = documentStatus === 'PROCESSING';
  const VALIDATED_OR_BEYOND = new Set(['VALIDATED', 'REVIEWED', 'EXPORTED']);
  const hasReachedValidation = documentStatus ? VALIDATED_OR_BEYOND.has(documentStatus) : false;
  const validationFailed = validation?.validation_status === 'FAILED';
  const isApproved = review?.review_status === 'APPROVED';
  const isRejected = review?.review_status === 'REJECTED';
  const isPending = review?.review_status === 'PENDING';

  if (loading) {
    return (
      <>
        <TopBar title="Review Document" />
        <Card>
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="grid grid-cols-2 gap-4 mt-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-1.5 w-full" />
                </div>
              ))}
            </div>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <TopBar
        title="Review Document"
        subtitle="Review extracted data and make corrections"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon={<RefreshCw className="h-4 w-4" />}
              onClick={refreshData}
              loading={refreshing}
            >
              Refresh
            </Button>
            <Link to="/dashboard">
              <Button variant="ghost" size="sm" icon={<ArrowLeft className="h-4 w-4" />}>
                Back
              </Button>
            </Link>
          </div>
        }
      />

      {/* Pipeline steps */}
      <Card className="mb-4">
        <PipelineSteps stages={PIPELINE_STAGES} currentStatus={documentStatus} />
      </Card>

      {/* Processing banner */}
      {isProcessing && (
        <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-brand-50 border border-brand-200 text-brand-700">
          <div className="h-5 w-5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin flex-shrink-0" />
          <div className="text-sm">
            <span className="font-semibold">Processing in progress.</span>{' '}
            <span className="text-brand-600">The page will auto-refresh every 5 seconds.</span>
          </div>
        </div>
      )}

      {/* Validation status — only show when document has actually reached validation */}
      {validation && hasReachedValidation && (
        <div
          className={`mb-4 flex items-start gap-3 px-4 py-3 rounded-xl border text-sm ${
            validation.validation_status === 'PASSED'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : validation.validation_status === 'FAILED'
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-amber-50 border-amber-200 text-amber-700'
          }`}
        >
          {validation.validation_status === 'PASSED' ? (
            <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
          ) : validation.validation_status === 'FAILED' ? (
            <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className="font-semibold">Validation: {validation.validation_status}</p>
            {validation.validation_errors.length > 0 && (
              <ul className="mt-1.5 space-y-0.5 list-disc list-inside">
                {validation.validation_errors.map((error: any, idx: number) => (
                  <li key={idx}>
                    <span className="font-medium">{error.field}:</span> {error.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Main content */}
      <Card>
        {!extraction ? (
          /* No extraction yet */
          <div className="text-center py-8">
            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto mb-4">
              <Info className="h-7 w-7" />
            </div>
            <h3 className="text-base font-semibold text-slate-900 mb-1">
              No extraction data available
            </h3>
            <p className="text-sm text-slate-500 mb-6">
              The document may still be processing, or extraction hasn't started yet.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Button
                onClick={retryExtraction}
                loading={loading}
                icon={<Play className="h-4 w-4" />}
              >
                Start Extraction
              </Button>
              <Link to="/dashboard">
                <Button variant="secondary">Back to Dashboard</Button>
              </Link>
            </div>
          </div>
        ) : Object.keys(extraction.structured_data || {}).length === 0 ? (
          /* Extraction ran but no structured data */
          <div className="space-y-6">
            <div className="text-center py-6">
              <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center text-amber-500 mx-auto mb-4">
                <AlertTriangle className="h-7 w-7" />
              </div>
              <h3 className="text-base font-semibold text-slate-900 mb-1">
                No structured data extracted
              </h3>
              <p className="text-sm text-slate-500 max-w-md mx-auto">
                The document was processed but no fields were extracted. The format may not be recognized,
                OCR text extraction may have been incomplete, or the LLM extraction failed.
              </p>
            </div>

            {/* Extraction metadata */}
            {extraction.extraction_metadata && (
              <div className="rounded-lg border border-slate-200 overflow-hidden">
                <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                  <h4 className="text-sm font-semibold text-slate-700">Extraction Details</h4>
                </div>
                <MetadataGrid metadata={extraction.extraction_metadata} />
              </div>
            )}

            {/* Raw text preview */}
            {extraction.raw_text && (
              <div className="rounded-lg border border-slate-200">
                <div className="px-4 py-3 bg-slate-50 rounded-t-lg">
                  <h4 className="text-sm font-semibold text-slate-700">Extracted Text Preview</h4>
                </div>
                <pre className="px-4 py-3 text-xs text-slate-600 font-mono whitespace-pre-wrap max-h-48 overflow-auto">
                  {extraction.raw_text.substring(0, RAW_TEXT_PREVIEW_LENGTH)}
                  {extraction.raw_text.length > RAW_TEXT_PREVIEW_LENGTH ? '...' : ''}
                </pre>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                icon={<RotateCw className="h-4 w-4" />}
                onClick={handleRestartProcessing}
                loading={restartingProcessing}
              >
                Restart Processing
              </Button>
            </div>
          </div>
        ) : (
          /* Structured data — editable fields */
          <div className="space-y-6">
            {documentFilename && (
              <h2 className="text-lg font-bold text-slate-900 text-center">{documentFilename}</h2>
            )}

            {/* Review status banners */}
            {isApproved && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
                <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                <span className="font-semibold">Review approved — document complete.</span>
              </div>
            )}
            {isRejected && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                <XCircle className="h-5 w-5 flex-shrink-0" />
                <span className="font-semibold">Review rejected. Please make corrections and resubmit.</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {Object.entries(extraction.structured_data || {}).map(([field, value]) => {
                const rawConf = extraction.confidence_scores[field];
                const confidence = typeof rawConf === 'number' ? rawConf : 0;
                const displayValue = corrections[field] || formatFieldValue(value);
                return (
                  <div key={field} className={`space-y-2 ${Array.isArray(value) ? 'md:col-span-2' : ''}`}>
                    <label className="block text-sm font-medium text-slate-700">
                      {field.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                    </label>
                    {Array.isArray(value) ? (
                      <div className="overflow-x-auto rounded-lg border border-slate-300">
                        <table className="min-w-full text-sm">
                          <thead className="bg-slate-50">
                            <tr>
                              {value.length > 0 && typeof value[0] === 'object' && value[0] !== null
                                ? Object.keys(value[0]).map((col) => (
                                    <th key={col} className="px-3 py-2 text-left font-medium text-slate-600 border-b border-slate-200">
                                      {col.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                                    </th>
                                  ))
                                : <th className="px-3 py-2 text-left font-medium text-slate-600 border-b border-slate-200">Value</th>
                              }
                            </tr>
                          </thead>
                          <tbody>
                            {value.map((row, idx) => (
                              <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                                {typeof row === 'object' && row !== null
                                  ? Object.values(row).map((cell, ci) => (
                                      <td key={ci} className="px-3 py-2 text-slate-900 border-b border-slate-100">
                                        {String(cell ?? '')}
                                      </td>
                                    ))
                                  : <td className="px-3 py-2 text-slate-900 border-b border-slate-100">{String(row)}</td>
                                }
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={displayValue}
                        onChange={(e) => setCorrection(field, e.target.value)}
                        disabled={isApproved}
                        className={`block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 ${
                          isApproved ? 'bg-slate-50 cursor-not-allowed' : 'bg-white'
                        }`}
                      />
                    )}
                    <ConfidenceBar confidence={confidence} />
                  </div>
                );
              })}
            </div>

            {/* Action buttons */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-200">
              <Button
                variant="outline"
                icon={<RotateCw className="h-4 w-4" />}
                onClick={handleRestartProcessing}
                loading={restartingProcessing}
                disabled={isApproved}
              >
                Restart Processing
              </Button>
              <div className="flex items-center gap-3">
                <Link to="/dashboard">
                  <Button variant="secondary">Cancel</Button>
                </Link>
                {/* Save Review — hidden when approved, shown when no review or rejected */}
                {!isApproved && (!review || isRejected) && (
                  <Button
                    icon={<Save className="h-4 w-4" />}
                    onClick={handleSave}
                    loading={saving}
                    disabled={!canSave}
                  >
                    {saving ? 'Saving...' : 'Save Review'}
                  </Button>
                )}
              </div>
            </div>

            {/* Validation failed hint */}
            {validationFailed && !isApproved && (
              <p className="text-sm text-red-600 text-right -mt-2">
                Fix validation errors or reprocess the document before saving.
              </p>
            )}

            {/* Approve / Reject — shown when review is pending */}
            {isPending && (
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
                <Button
                  variant="danger"
                  icon={<ThumbsDown className="h-4 w-4" />}
                  onClick={handleReject}
                >
                  Reject
                </Button>
                <Button
                  icon={<ThumbsUp className="h-4 w-4" />}
                  onClick={handleApprove}
                >
                  Approve
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </>
  );
};

export default DocumentReview;
