import React from 'react';

interface StatsCardProps {
    label: string;
    value: string | number;
    change?: string;
    isPositive?: boolean;
    icon: React.ReactNode;
}

const StatsCard: React.FC<StatsCardProps> = ({ label, value, change, isPositive, icon }) => {
    return (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
                <span className="text-gray-500 text-sm font-medium">{label}</span>
                <div className="p-2 bg-gray-50 rounded-lg text-gray-600">
                    {icon}
                </div>
            </div>
            <div>
                <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
                {change && (
                    <p className={`text-sm mt-1 font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                        {isPositive ? '↑' : '↓'} {change}
                    </p>
                )}
            </div>
        </div>
    );
};

export default StatsCard;
