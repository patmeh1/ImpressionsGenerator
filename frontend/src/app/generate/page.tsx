'use client';

import React, { useState, useEffect } from 'react';
import { getDoctors, generateReport } from '@/lib/api';
import type { Doctor, Report } from '@/lib/types';
import DictationInput from '@/components/DictationInput';
import DoctorSelector from '@/components/DoctorSelector';
import ReportViewer from '@/components/ReportViewer';
import { Sparkles, Loader2 } from 'lucide-react';

const REPORT_TYPES = ['CT', 'MRI', 'X-ray', 'PET', 'Ultrasound'];
const BODY_REGIONS = [
  'Head', 'Neck', 'Chest', 'Abdomen', 'Pelvis',
  'Spine', 'Upper Extremity', 'Lower Extremity', 'Whole Body',
];

export default function GeneratePage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);
  const [inputText, setInputText] = useState('');
  const [reportType, setReportType] = useState('CT');
  const [bodyRegion, setBodyRegion] = useState('Abdomen');
  const [generating, setGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDoctors()
      .then((docs) => {
        setDoctors(docs);
        if (docs.length > 0) setSelectedDoctorId(docs[0].id);
      })
      .catch(console.error);
  }, []);

  const handleGenerate = async () => {
    if (!selectedDoctorId || !inputText.trim()) return;
    setGenerating(true);
    setError(null);
    setGeneratedReport(null);

    try {
      const res = await generateReport({
        doctor_id: selectedDoctorId,
        input_text: inputText,
        report_type: reportType,
        body_region: bodyRegion,
      });

      setGeneratedReport({
        id: res.report_id,
        doctor_id: selectedDoctorId,
        input_text: inputText,
        report_type: reportType,
        body_region: bodyRegion,
        findings: res.findings,
        impressions: res.impressions,
        recommendations: res.recommendations,
        status: 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
        <Sparkles size={24} className="text-teal-500" />
        Generate Report
      </h1>

      <div className="card p-5 space-y-5">
        {/* Doctor + Report Type selectors */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Doctor
            </label>
            <DoctorSelector
              doctors={doctors}
              selectedId={selectedDoctorId}
              onChange={setSelectedDoctorId}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="input-field"
            >
              {REPORT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Body Region
            </label>
            <select
              value={bodyRegion}
              onChange={(e) => setBodyRegion(e.target.value)}
              className="input-field"
            >
              {BODY_REGIONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Dictation Input */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Dictation Text
          </label>
          <DictationInput
            value={inputText}
            onChange={setInputText}
            disabled={generating}
          />
        </div>

        {/* Generate Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating || !inputText.trim() || !selectedDoctorId}
            className="btn-primary flex items-center gap-2"
          >
            {generating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles size={16} />
                Generate Impressions
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Generated Report */}
      {generatedReport && (
        <ReportViewer inputText={inputText} report={generatedReport} />
      )}
    </div>
  );
}
