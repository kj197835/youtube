import React, { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { ChannelStats, VideoData, AIInsight, ChartData, AppTab, DashboardData } from './types';
import { getCreatorInsights } from './services/geminiService';
import StatsCard from './components/StatsCard';
import InsightSection from './components/InsightSection';
import { translations, Language } from './translations';

const NavItem: React.FC<{ label: string; active: boolean; onClick: () => void; icon: React.ReactNode }> = ({ label, active, onClick, icon }) => (
    <button
        onClick={onClick}
        className={`relative flex items-center gap-2 px-2 sm:px-4 py-4 text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${active ? 'text-red-600' : 'text-gray-500 hover:text-gray-900'
            }`}
    >
        {icon}
        {label}
        {active && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-red-600 rounded-t-full shadow-sm" />
        )}
    </button>
);

const App: React.FC = () => {
    const [activeTab, setActiveTab] = useState<AppTab>('Dashboard');
    const [timeRange, setTimeRange] = useState<'Daily' | 'Weekly' | 'Monthly'>('Daily');
    const [chartType, setChartType] = useState<'Daily' | 'Cumulative'>('Daily');
    const [videoLimit, setVideoLimit] = useState<number | 'ALL'>(10);
    const [selectedMetric, setSelectedMetric] = useState<'views' | 'likes' | 'dislikes' | 'watchTime' | 'subscribers' | 'revenue'>('views');
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const [legalModal, setLegalModal] = useState<'privacy' | 'tos' | null>(null);
    const [language, setLanguage] = useState<Language>('en');

    const t = translations[language]; // Convenience accessor

    // Data State
    const [stats, setStats] = useState<ChannelStats | null>(null);
    const [videos, setVideos] = useState<VideoData[]>([]);
    const [chartData, setChartData] = useState<ChartData[]>([]);

    const [insights, setInsights] = useState<AIInsight[]>([]);
    const [loadingData, setLoadingData] = useState(true);
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 640);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    const fetchData = async () => {
        try {
            setLoadingData(true);
            const res = await fetch('./dashboard_data.json');
            if (!res.ok) {
                throw new Error("Failed to load data");
            }
            const data: DashboardData = await res.json();

            // 1. Process Channel Stats (Dynamic based on Time Range)
            const summary = data.summary;
            const profileImage = summary.profile_image;

            // Determine Source Data based on TimeRange
            const dailyTrends = data.trends.daily;
            let source = dailyTrends; // Default
            if (timeRange === 'Weekly') source = data.trends.weekly;
            if (timeRange === 'Monthly') source = data.trends.monthly;

            // Process Chart Data
            // Process Chart Data
            // [FIX] Support both 'dates' (legacy) and 'day' (new DB) keys
            const dates = source.dates || (source as any).day;
            const views = source.views;
            const subs = source.subscribers || (source as any).subscribersGained;
            const revenue = source.revenue || (source as any).estimatedRevenue; // Support different naming
            const likes = (source as any).likes || [];
            const dislikes = (source as any).dislikes || [];
            const watchMinutes = (source as any).estimatedMinutesWatched || [];
            const comments = (source as any).comments || [];

            if (!dates) {
                console.error("No dates found in source data:", source);
                setLoadingData(false);
                return;
            }

            // Calculate Totals for Stats Cards
            const totalViews = views.reduce((a: number, b: number) => a + b, 0);
            const totalSubs = subs.reduce((a: number, b: number) => a + b, 0);
            const totalRevenue = revenue.reduce((a: number, b: number) => a + b, 0);

            // Calculate Watch Time (Hours)
            const totalWatchTimeMinutes = watchMinutes.reduce((a: number, b: number) => a + b, 0);
            const totalWatchTimeHours = totalWatchTimeMinutes / 60;

            // Calculate Engagement Rate
            // (Likes + Comments) / Views * 100
            const totalLikes = likes.reduce((a: number, b: number) => a + b, 0);
            const totalComments = comments.reduce((a: number, b: number) => a + b, 0);
            const engagementRate = totalViews > 0 ? ((totalLikes + totalComments) / totalViews) * 100 : 0;

            const calculatedStats: ChannelStats = {
                subscriberCount: totalSubs,
                viewCount: totalViews,
                videoCount: data.top_videos.length,
                watchTimeHours: Math.round(totalWatchTimeHours),
                avgEngagementRate: parseFloat(engagementRate.toFixed(2)),
                profileImage: profileImage,
                revenue: totalRevenue,
                likes: data.summary.likes_30d || 0,
                lastUpdated: data.summary.last_updated
            };

            setStats(calculatedStats);

            const newChartData: ChartData[] = dates.map((date, i) => ({
                name: date,
                views: views[i] || 0,
                subscribers: subs[i] || 0,
                revenue: revenue[i] || 0,
                likes: likes[i] || 0,
                dislikes: dislikes[i] || 0,
                watchTime: (data.trends[timeRange.toLowerCase() as keyof typeof data.trends].estimatedMinutesWatched?.[i] || 0) / 60
            }));

            if (timeRange === 'Daily') {
                setChartData(newChartData.slice(-30));
            } else {
                setChartData(newChartData);
            }

            // 2. Process Videos
            const processedVideos: VideoData[] = data.top_videos.map((v, i) => ({
                id: v.video || `v-${i}`,
                title: (v as any).title || `Unknown Video (${v.video})`,
                thumbnail: (v as any).thumbnail || '',
                publishedAt: 'Recent',
                views: v.views,
                likes: (v as any).likes || 0,
                dislikes: (v as any).dislikes || 0,
                revenue: (v as any).estimatedRevenue || 0,
                comments: (v as any).comments || 0,
                retentionRate: 50,
                status: 'Public'
            }));
            setVideos(processedVideos);
            setLoadingData(false);

            fetchInsights(calculatedStats, processedVideos);

        } catch (e) {
            console.error(e);
            setLoadingData(false);
        }
    };

    const getDisplayChartData = () => {
        if (chartType === 'Daily') return chartData;

        let runningTotal = 0;
        return chartData.map(d => {
            const val = d[selectedMetric] || 0;
            runningTotal += val;
            return { ...d, [selectedMetric]: runningTotal };
        });
    };

    const fetchInsights = useCallback(async (currentStats: ChannelStats, recentVideos: VideoData[]) => {
        const data = await getCreatorInsights(currentStats, recentVideos);
        setInsights(data);
    }, []);

    useEffect(() => {
        fetchData();
    }, [timeRange]);

    const rangeLabel = timeRange === 'Daily' ? '(30d)' : timeRange === 'Weekly' ? '(30w)' : '(30m)';
    const displayChartData = getDisplayChartData();

    const renderContent = () => {
        if (loadingData) return <div className="p-20 text-center text-gray-400">{t.loading}</div>;

        switch (activeTab) {
            case 'Dashboard':
                return (
                    <div className="space-y-8">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                            <StatsCard label={`${t.stats.views} ${rangeLabel}`} value={stats?.viewCount.toLocaleString() || '-'} change="-" isPositive={true} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>} />
                            <StatsCard label={`${t.stats.subscribers} ${rangeLabel}`} value={stats?.subscriberCount.toLocaleString() || '-'} change="-" isPositive={true} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>} />
                            <StatsCard label={`Likes ${rangeLabel}`} value={stats?.likes.toLocaleString() || '-'} change="-" isPositive={true} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>} />
                            <StatsCard label={t.stats.watchTime} value={stats?.watchTimeHours.toLocaleString() || '-'} change="-" isPositive={false} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
                            <StatsCard label={t.stats.engagement} value={`${stats?.avgEngagementRate}%`} change="-" isPositive={true} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" /></svg>} />
                            <StatsCard label={`${t.stats.revenue} ${rangeLabel}`} value={`$${stats?.revenue.toFixed(2) || '0.00'}`} change="-" isPositive={true} icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} />
                        </div>
                        <div className="bg-white p-4 sm:p-8 rounded-3xl border border-gray-100 shadow-sm min-h-0 sm:min-h-[500px]">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-bold text-gray-900">{t.sections.growth} ({timeRange})</h3>
                                <div className="flex items-center gap-3">
                                    <div className="relative inline-block text-left">
                                        <select
                                            value={selectedMetric}
                                            onChange={(e) => setSelectedMetric(e.target.value as any)}
                                            className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-gray-50 border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer capitalize"
                                        >
                                            <option value="views">{t.metrics.views}</option>
                                            <option value="watchTime">{t.metrics.watchTime}</option>
                                            <option value="subscribers">{t.metrics.subscribers}</option>
                                            <option value="revenue">{t.metrics.revenue}</option>
                                            <option value="likes">{t.metrics.likes}</option>
                                            <option value="dislikes">{t.metrics.dislikes}</option>
                                        </select>
                                    </div>
                                    <div className="relative inline-block text-left">
                                        <select
                                            value={chartType}
                                            onChange={(e) => setChartType(e.target.value as any)}
                                            className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-gray-50 border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer"
                                        >
                                            <option value="Daily">{t.chartType.changes}</option>
                                            <option value="Cumulative">{t.chartType.cumulative}</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div className="h-[65vw] sm:h-[400px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    {chartType === 'Daily' ? (
                                        <BarChart data={displayChartData} margin={{ top: 10, right: 10, left: isMobile ? -35 : -20, bottom: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                            <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                                            <Bar dataKey={selectedMetric} fill="#ef4444" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    ) : (
                                        <AreaChart data={displayChartData} margin={{ top: 10, right: 10, left: isMobile ? -35 : -20, bottom: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                            <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                                            <Area type="monotone" dataKey={selectedMetric} stroke="#ef4444" fill="#fee2e2" strokeWidth={3} />
                                        </AreaChart>
                                    )}
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <InsightSection insights={insights} title={t.sections.aiInsights} />
                    </div>
                );
            case 'Content':
                return (
                    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
                        <div className="p-6 border-b border-gray-50 flex items-center justify-between">
                            <h3 className="font-bold text-lg text-gray-900">{t.sections.topVideos}</h3>
                            <div className="relative inline-block text-left">
                                <select
                                    value={videoLimit}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        setVideoLimit(val === 'ALL' ? 'ALL' : Number(val));
                                    }}
                                    className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-gray-50 border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer"
                                >
                                    <option value={10}>10</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                    <option value="ALL">{t.videoLimit.all}</option>
                                </select>
                            </div>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-wider">
                                    <tr>
                                        <th className="px-4 py-3 text-gray-900 w-[50px]">{t.table.image}</th>
                                        <th className="px-4 py-3 text-gray-900 w-[40%]">{t.table.video}</th>
                                        <th className="px-4 py-3 text-gray-900">{t.table.id}</th>
                                        <th className="px-4 py-3 text-gray-900">{t.table.views}</th>
                                        <th className="px-4 py-3 text-gray-900">{t.table.likes}</th>
                                        <th className="px-4 py-3 text-gray-900">{t.table.dislikes}</th>
                                        <th className="px-4 py-3 text-gray-900">{t.table.revenue}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50 text-[11px]">
                                    {(videoLimit === 'ALL' ? videos : videos.slice(0, videoLimit)).map(v => (
                                        <tr key={v.id} className="hover:bg-gray-50/50 transition-colors">
                                            <td className="px-4 py-2">
                                                <img
                                                    src={v.thumbnail}
                                                    alt={v.title}
                                                    className="w-10 h-6 object-cover rounded cursor-pointer hover:opacity-80 transition-opacity"
                                                    onClick={() => setSelectedImage(v.thumbnail)}
                                                />
                                            </td>
                                            <td className="px-4 py-2 font-medium text-gray-900 truncate max-w-[200px]" title={v.title}>
                                                {v.title}
                                            </td>
                                            <td className="px-4 py-2 text-gray-400 font-mono text-[10px]">{v.id}</td>
                                            <td className="px-4 py-2 text-gray-600">{v.views.toLocaleString()}</td>
                                            <td className="px-4 py-2 text-gray-600">{v.likes.toLocaleString()}</td>
                                            <td className="px-4 py-2 text-gray-600">{v.dislikes.toLocaleString()}</td>
                                            <td className="px-4 py-2 font-bold text-green-600">${v.revenue.toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                );
            case 'Analytics':
                return (
                    <div className="space-y-6">
                        <div className="bg-white p-4 sm:p-8 rounded-3xl border border-gray-100 shadow-sm min-h-0 sm:min-h-[500px]">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-bold text-gray-900">{t.sections.detailedAnalytics} ({timeRange})</h3>
                                <div className="flex items-center gap-3">
                                    <div className="relative inline-block text-left">
                                        <select
                                            value={selectedMetric}
                                            onChange={(e) => setSelectedMetric(e.target.value as any)}
                                            className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-gray-50 border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer capitalize"
                                        >
                                            <option value="views">{t.metrics.views}</option>
                                            <option value="watchTime">{t.metrics.watchTime}</option>
                                            <option value="subscribers">{t.metrics.subscribers}</option>
                                            <option value="revenue">{t.metrics.revenue}</option>
                                            <option value="likes">{t.metrics.likes}</option>
                                            <option value="dislikes">{t.metrics.dislikes}</option>
                                        </select>
                                    </div>
                                    <div className="relative inline-block text-left">
                                        <select
                                            value={chartType}
                                            onChange={(e) => setChartType(e.target.value as any)}
                                            className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-gray-50 border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer"
                                        >
                                            <option value="Daily">{t.chartType.changes}</option>
                                            <option value="Cumulative">{t.chartType.cumulative}</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {chartData.every(d => (d[selectedMetric] || 0) === 0) ? (
                                <div className="h-[400px] flex flex-col items-center justify-center text-gray-400">
                                    <svg className="w-12 h-12 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    <p className="font-semibold">No detailed trend data available for this period.</p>
                                    <p className="text-sm mt-1">Daily stats might be hidden by YouTube for privacy.</p>
                                </div>
                            ) : (
                                <div className="h-[65vw] sm:h-[400px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        {chartType === 'Daily' ? (
                                            <BarChart data={displayChartData} margin={{ top: 10, right: 10, left: isMobile ? -35 : -20, bottom: 0 }}>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} minTickGap={30} />
                                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                                <Tooltip cursor={{ fill: '#f3f4f6' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                                                <Bar dataKey={selectedMetric} fill="#ef4444" radius={[4, 4, 0, 0]} />
                                            </BarChart>
                                        ) : (
                                            <AreaChart data={displayChartData} margin={{ top: 10, right: 10, left: isMobile ? -35 : -20, bottom: 0 }}>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} minTickGap={30} />
                                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9ca3af' }} />
                                                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                                                <Area type="monotone" dataKey={selectedMetric} stroke="#ef4444" fill="#fee2e2" strokeWidth={3} />
                                            </AreaChart>
                                        )}
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </div>
                        <InsightSection insights={insights} title="AI Prediction Insights" />
                    </div>
                );
                return <div className="p-20 text-center text-gray-400">{t.sectionComingSoon}</div>;
        }
    };

    return (
        <div className="min-h-screen bg-[#F8F9FC] flex flex-col">
            <header className="sticky top-0 z-50 bg-white border-b border-gray-100 shadow-sm backdrop-blur-md bg-white/90">
                <div className="max-w-[1600px] mx-auto px-6 lg:px-12 flex items-center justify-between h-20">
                    <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('Dashboard')}>
                        <div className="w-8 h-8 bg-red-600 rounded-xl flex items-center justify-center rotate-3 shadow-md shadow-red-100">
                            <svg className="text-white w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" /></svg>
                        </div>
                        <h1 className="text-xl font-black text-gray-900 tracking-tighter hidden sm:block">{t.title}</h1>
                    </div>

                    <nav className="flex items-center gap-1 sm:gap-2 overflow-x-auto no-scrollbar">
                        <NavItem label={t.nav.dashboard} active={activeTab === 'Dashboard'} onClick={() => setActiveTab('Dashboard')} icon={null} />
                        <NavItem label={t.nav.content} active={activeTab === 'Content'} onClick={() => setActiveTab('Content')} icon={null} />
                        <NavItem label={t.nav.analytics} active={activeTab === 'Analytics'} onClick={() => setActiveTab('Analytics')} icon={null} />
                    </nav>

                    <div className="flex items-center gap-4">
                        {/* Language Selector */}
                        <div className="relative">
                            <select
                                value={language}
                                onChange={(e) => setLanguage(e.target.value as Language)}
                                className="appearance-none bg-gray-100 pl-3 pr-8 py-1.5 rounded-lg text-xs font-bold text-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500 cursor-pointer hover:bg-gray-200 transition-colors"
                            >
                                <option value="en">English</option>
                                <option value="kr">한국어</option>
                            </select>
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                                <svg className="fill-current h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" /></svg>
                            </div>
                        </div>
                    </div>
                </div>
            </header>


            <main className="flex-1 max-w-[1600px] mx-auto w-full p-6 lg:p-12 space-y-10">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <h2 className="text-4xl font-black text-gray-900 tracking-tight">{t.nav[activeTab.toLowerCase() as keyof typeof t.nav] || activeTab}</h2>
                        <p className="text-gray-500 font-medium mt-1">
                            {activeTab === 'Dashboard' ? t.subtitles.dashboard :
                                activeTab === 'Content' ? t.subtitles.contents :
                                    activeTab === 'Analytics' ? t.subtitles.analytics :
                                        t.subtitles.dashboard}
                        </p>
                        {stats?.lastUpdated && (
                            <p className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                {t.lastUpdated} {stats.lastUpdated}
                            </p>
                        )}
                    </div>

                    {activeTab !== 'Earn' && activeTab !== 'Customization' && (
                        <div className="relative inline-block text-left">
                            <select
                                value={timeRange}
                                onChange={(e) => setTimeRange(e.target.value as any)}
                                className="block w-full pl-3 pr-8 py-2 text-sm font-semibold bg-white border border-gray-200 text-gray-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-lg shadow-sm appearance-none cursor-pointer"
                            >
                                <option value="Daily">{t.timeRange.daily}</option>
                                <option value="Weekly">{t.timeRange.weekly}</option>
                                <option value="Monthly">{t.timeRange.monthly}</option>
                            </select>
                        </div>
                    )}
                </div>
                {renderContent()}
            </main>

            <footer className="border-t border-gray-200 bg-white mt-auto">
                <div className="max-w-[1600px] mx-auto px-6 lg:px-12 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-sm text-gray-500">{t.footer.copyright}</p>
                    <div className="flex items-center gap-6 text-sm text-gray-500">
                        <button onClick={() => setLegalModal('privacy')} className="hover:text-gray-900 transition-colors">{t.footer.privacy}</button>
                        <button onClick={() => setLegalModal('tos')} className="hover:text-gray-900 transition-colors">{t.footer.tos}</button>
                    </div>
                </div>
            </footer>

            {/* Legal Modal */}
            {legalModal && (
                <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setLegalModal(null)}>
                    <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}>
                        <div className="p-6 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
                            <h3 className="text-2xl font-bold text-gray-900">
                                {legalModal === 'privacy' ? t.legal.privacyTitle : t.legal.tosTitle}
                            </h3>
                            <button
                                onClick={() => setLegalModal(null)}
                                className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>
                        <div className="p-6 md:p-8 text-gray-600 space-y-4 leading-relaxed overflow-y-auto">
                            {legalModal === 'privacy' ? (
                                <>
                                    <p className="font-semibold text-gray-900">{t.legal.lastUpdated}</p>
                                    <p>{t.legal.privacyIntro}</p>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.privacySection1}</h4>
                                    <ul className="list-disc pl-5 space-y-1">
                                        {t.legal.privacyList1.map((item, i) => <li key={i}>{item}</li>)}
                                    </ul>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.privacySection2}</h4>
                                    <p>{t.legal.privacyIntro2}</p>
                                    <ul className="list-disc pl-5 space-y-1">
                                        {t.legal.privacyList2.map((item, i) => <li key={i}>{item}</li>)}
                                    </ul>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.privacySection3}</h4>
                                    <p>{t.legal.privacyIntro3}</p>
                                    <ul className="list-disc pl-5 space-y-1">
                                        {t.legal.privacyList3.map((item, i) => <li key={i}>{item}</li>)}
                                    </ul>
                                </>
                            ) : (
                                <>
                                    <p className="font-semibold text-gray-900">{t.legal.effectiveDate}</p>
                                    <p>{t.legal.tosIntro}</p>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.tosSection1}</h4>
                                    <p>{t.legal.tosContent1}</p>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.tosSection2}</h4>
                                    <p dangerouslySetInnerHTML={{ __html: t.legal.tosContent2.replace('https://www.youtube.com/t/terms', '<a href="https://www.youtube.com/t/terms" target="_blank" rel="noreferrer" class="text-blue-600 hover:underline">https://www.youtube.com/t/terms</a>') }} />

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.tosSection3}</h4>
                                    <p>{t.legal.tosContent3}</p>

                                    <h4 className="text-lg font-bold text-gray-900 pt-4">{t.legal.tosSection4}</h4>
                                    <p>{t.legal.tosContent4}</p>
                                </>
                            )}
                        </div>
                        <div className="p-6 border-t border-gray-100 bg-gray-50 rounded-b-2xl flex justify-end">
                            <button
                                onClick={() => setLegalModal(null)}
                                className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
                            >
                                {t.footer.close}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Image Modal */}
            {selectedImage && (
                <div
                    className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    onClick={() => setSelectedImage(null)}
                >
                    <div className="relative max-w-4xl w-full max-h-[90vh] flex flex-col items-center">
                        <img
                            src={selectedImage}
                            alt="Full Size"
                            className="max-w-full max-h-[85vh] rounded-lg shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        />
                        <button
                            className="mt-4 px-6 py-2 bg-white/10 text-white rounded-full hover:bg-white/20 transition-colors backdrop-blur-md"
                            onClick={() => setSelectedImage(null)}
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default App;
