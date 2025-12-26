import React, { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { X, Download, FileText } from 'lucide-react';

interface DetailedReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    report: string;
    title?: string;
    description?: string;
}

const DetailedReportModal: React.FC<DetailedReportModalProps> = ({
    isOpen,
    onClose,
    report,
    title = "AI Detailed Strategic Report",
    description = "Comprehensive analysis & Action items"
}) => {
    const reportRef = useRef<HTMLDivElement>(null);

    if (!isOpen) return null;

    const handleDownloadPDF = async () => {
        if (!reportRef.current) return;

        try {
            const canvas = await html2canvas(reportRef.current, { scale: 2 });
            const imgData = canvas.toDataURL('image/png');

            const pdf = new jsPDF('p', 'mm', 'a4');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

            pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
            pdf.save('AI_Strategic_Report.pdf');
        } catch (error) {
            console.error('Error generating PDF:', error);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gray-50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <FileText className="w-6 h-6 text-purple-600" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">{title}</h2>
                            <p className="text-sm text-gray-500">{description}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleDownloadPDF}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            Download PDF
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8 bg-white">
                    <div ref={reportRef} className="prose prose-slate max-w-none">
                        <ReactMarkdown>{report}</ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DetailedReportModal;
