import React from 'react';
import { Sparkles, TrendingUp, AlertTriangle, Zap } from 'lucide-react';
import { AIInsights } from '../types';
import DetailedReportModal from './DetailedReportModal';



const InsightSection: React.FC<InsightSectionProps> = ({ data, title = "AI Data Analysis", variant }) => {
    if (!data) {
        return (
            <div className="bg-slate-900 rounded-3xl p-6 sm:p-8 text-white relative overflow-hidden flex flex-col items-center justify-center min-h-[200px]">
                <Sparkles className="w-10 h-10 text-slate-600 mb-4 animate-pulse" />
                <h3 className="text-slate-500 font-medium">Waiting for AI Analysis...</h3>
            </div>
        );
    }

    const [isModalOpen, setIsModalOpen] = React.useState(false);

    // Map data based on variant
    let cards = [];
    if (variant === 'current') {
        cards = [
            { key: 'strengths', icon: TrendingUp, color: 'emerald', label: 'Strengths (성과)' },
            { key: 'improvements', icon: AlertTriangle, color: 'amber', label: 'Improvements (개선점)' },
            { key: 'action_plan', icon: Zap, color: 'blue', label: 'Action Plan (행동 계획)' }
        ];
    } else {
        cards = [
            { key: 'growth_trend', icon: TrendingUp, color: 'emerald', label: 'Growth Trend (성장 추세)' },
            { key: 'risk_factor', icon: AlertTriangle, color: 'amber', label: 'Risk Factor (리스크 탐지)' },
            { key: 'action_strategy', icon: Zap, color: 'blue', label: 'Action Strategy (대응 전략)' }
        ];
    }

    return (
        <div className="bg-slate-900 rounded-3xl p-4 sm:p-8 text-white relative overflow-hidden border border-slate-800 shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-6 sm:mb-8 relative z-10">
                <div className="flex items-center gap-3">
                    <div className="bg-gradient-to-br from-purple-500 to-blue-600 p-2 rounded-xl shadow-lg shadow-purple-900/20">
                        <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                    </div>
                    <div>
                        <h2 className="text-lg sm:text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                            {title}
                        </h2>
                        <p className="text-slate-400 text-xs sm:text-sm">Strategized by Llama 3.1 & {variant === 'future' ? 'XGBoost Prediction' : 'Current Data'}</p>
                    </div>
                </div>
                {data.detailed_report && (
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="text-xs sm:text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-2 px-4 rounded-lg transition-colors border border-slate-700 hover:border-slate-600"
                    >
                        상세 보기 (View Details)
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 relative z-10">
                {cards.map((card) => {
                    const item = data[card.key];
                    if (!item) return null;

                    const Icon = card.icon;
                    const colors: any = {
                        emerald: { text: 'text-emerald-400', border: 'border-emerald-500/20', bgHover: 'hover:bg-emerald-900/10' },
                        amber: { text: 'text-amber-400', border: 'border-amber-500/20', bgHover: 'hover:bg-amber-900/10' },
                        blue: { text: 'text-blue-400', border: 'border-blue-500/20', bgHover: 'hover:bg-blue-900/10' }
                    };
                    const theme = colors[card.color];

                    return (
                        <div key={card.key} className={`bg-slate-800/40 backdrop-blur-sm border ${theme.border} rounded-2xl p-5 hover:bg-slate-800/60 transition-all duration-300 group`}>
                            <div className="flex items-center gap-2 mb-3">
                                <Icon className={`w-5 h-5 ${theme.text} group-hover:scale-110 transition-transform`} />
                                <h3 className={`${theme.text} font-bold text-sm sm:text-base uppercase tracking-wider`}>{card.label}</h3>
                            </div>
                            <div className="space-y-2">
                                <p className="font-semibold text-white/90 text-sm sm:text-base">{item.title}</p>
                                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed border-t border-slate-700/50 pt-2">
                                    {item.content}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>

            <DetailedReportModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                report={data.detailed_report || ""}
            />
        </div>
    );
};

export default InsightSection;
