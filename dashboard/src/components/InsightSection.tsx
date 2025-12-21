import React from 'react';
import { AIInsight } from '../types';

interface InsightSectionProps {
    insights: AIInsight[];
    title?: string;
}

const InsightSection: React.FC<InsightSectionProps> = ({ insights, title = "AI Strategy Insights" }) => {
    return (
        <div className="bg-slate-900 rounded-3xl p-3 sm:p-8 text-white relative overflow-hidden">
            <div className="flex items-center justify-between mb-2 sm:mb-8 relative z-10">
                <div>
                    <h2 className="text-lg sm:text-2xl font-bold">{title}</h2>
                    <p className="text-slate-400 mt-1 text-xs sm:text-base">Recommendations based on latest data</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-6 relative z-10">
                {insights.map((insight, idx) => (
                    <div key={idx} className="bg-white/5 border border-white/10 rounded-2xl p-3 sm:p-6 flex flex-col justify-between border-l-4 border-l-red-500">
                        <div>
                            <h3 className="font-bold text-base sm:text-lg mb-1 sm:mb-2 text-white">{insight.topic}</h3>
                            <p className="text-slate-300 text-xs sm:text-sm mb-2 sm:mb-4 leading-relaxed">{insight.analysis}</p>
                        </div>
                        <div className="bg-red-500/10 p-2 sm:p-3 rounded-lg border border-red-500/20">
                            <p className="text-[10px] text-red-300 font-bold uppercase mb-1">Recommendation</p>
                            <p className="text-xs sm:text-sm font-medium text-red-50">{insight.recommendation}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default InsightSection;
